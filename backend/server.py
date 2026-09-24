from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.cors import CORSMiddleware

from auth import SESSION_DAYS, auth_router, get_current_user
from column_inference import infer_column_names
from config import get_settings
from db.models import (
    DocumentRow,
    ExtractedTableRow,
    GoogleTokenRow,
    OAuthStateRow,
    PdfFileRow,
)
from db.repositories import (
    documents,
    extracted_tables,
    pdf_files,
    oauth_states,
    google_tokens,
    sessions,
    users,
)
from db.session import check_database, close_engine, get_db
from exporters import (
    export_batch_xlsx,
    export_batch_zip,
    export_csv,
    export_json,
    export_xlsx,
)
from extraction import extract_tables, merge_multipage, render_first_page_thumb
from models import (
    BatchExport,
    CellStateUpdate,
    CellUpdate,
    ColumnRulesUpdate,
    ColumnTypeUpdate,
    DateAutofill,
    Documento,
    User,
    new_id,
)
from normalization import (
    detect_date_format,
    infer_column_type,
    normalize_value,
    parse_date_with,
)
from schema_validation import build_cells, combine_confidence, reason_code
from storage import StorageUnavailable, delete_object, get_object, is_configured, put_object
from sheets import (
    build_auth_url,
    exchange_code,
    export_document_to_sheets,
    is_configured,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
app = FastAPI(title="Anclora TableExtract")
settings = get_settings()


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _doc_dict(row: DocumentRow) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "nombre_archivo": row.nombre_archivo,
        "fecha_carga": _iso(row.fecha_carga),
        "estado": row.estado,
        "num_paginas": row.num_paginas,
        "num_tablas": row.num_tablas,
        "process_ms": row.process_ms,
        "thumb_path": row.thumb_path,
        "error": row.error,
    }


def _table_dict(row: ExtractedTableRow) -> dict:
    return {
        "id": row.id,
        "documento_id": row.documento_id,
        "user_id": row.user_id,
        "pagina_origen": row.pagina_origen,
        "source_pages": row.source_pages or [],
        "extraction_method": row.extraction_method,
        "columnas": row.columnas or [],
        "column_types": row.column_types or [],
        "num_filas": row.num_filas,
        "num_columnas": row.num_columnas,
        "cells": row.cells or [],
        "column_rules": row.column_rules or {},
    }


def _token_dict(row: GoogleTokenRow) -> dict:
    result = {}
    for key in (
        "access_token",
        "refresh_token",
        "token_uri",
        "client_id",
        "client_secret",
        "scopes",
        "expires_at",
    ):
        value = getattr(row, key)
        if value is not None:
            result[key] = value.isoformat() if isinstance(value, datetime) else value
    return result


def _process_pdf_sync(path, force_ocr=False, lang="es"):
    num_pages, tables = extract_tables(path, force_ocr=force_ocr, lang=lang)
    return num_pages, merge_multipage(tables)


async def _tables_from_raw(doc_id, user_id, raw_tables, lang):
    stored = []
    for raw in raw_tables:
        rows, ncols = raw["rows"], raw["ncols"]
        if ncols == 0 or not rows:
            continue
        columnas = await infer_column_names(rows, ncols, lang=lang)
        data_rows = rows[1:] if _looks_like_header(rows[0]) and len(rows) > 1 else rows
        column_types = []
        for c in range(ncols):
            column_types.append(
                infer_column_type(
                    [(r[c]["value"] if c < len(r) else "") for r in data_rows]
                )
            )
        rows_meta = []
        for row in data_rows:
            meta_row = []
            for c in range(ncols):
                cell = (
                    row[c]
                    if c < len(row)
                    else {
                        "value": "",
                        "original": "",
                        "extraction_conf": 0.5,
                        "page": raw["page"],
                        "bbox": None,
                    }
                )
                value, norm_conf = normalize_value(cell["value"], column_types[c])
                meta_row.append(
                    {
                        "value": value,
                        "original": cell.get("original", cell["value"]),
                        "extraction_conf": cell.get("extraction_conf", 0.9),
                        "norm_conf": norm_conf,
                        "page": cell.get("page", raw["page"]),
                        "bbox": cell.get("bbox"),
                    }
                )
            rows_meta.append(meta_row)
        cells = build_cells(columnas, column_types, rows_meta)
        stored.append(
            ExtractedTableRow(
                id=new_id("tbl"),
                documento_id=doc_id,
                user_id=user_id,
                pagina_origen=raw["page"],
                source_pages=raw.get("source_pages", [raw["page"]]),
                extraction_method=raw["method"],
                columnas=columnas,
                column_types=column_types,
                num_filas=len(rows_meta),
                num_columnas=ncols,
                cells=[c.model_dump() for c in cells],
                column_rules={},
            )
        )
    return stored


async def _process_document(
    db: AsyncSession, user: User, filename: str, content: bytes, lang: str
):
    t0 = time.time()
    doc = Documento(user_id=user.user_id, nombre_archivo=filename)
    row = DocumentRow(
        id=doc.id,
        user_id=user.user_id,
        nombre_archivo=doc.nombre_archivo,
        estado=doc.estado,
        num_paginas=0,
        num_tablas=0,
        process_ms=0,
        error=None,
    )
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        try:
            num_pages, raw_tables = await asyncio.to_thread(
                _process_pdf_sync, tmp.name, False, lang
            )
        except Exception as exc:
            logger.exception("extraction failed")
            row.error = str(exc)
            db.add(row)
            await db.flush()
            return row
    stored_tables = await _tables_from_raw(doc.id, user.user_id, raw_tables, lang)
    # Thumbnails are rendered on demand from the database-backed PDF. This keeps
    # the default runtime independent of any external object-storage service.
    row.num_paginas, row.num_tablas = num_pages, len(stored_tables)
    row.process_ms = int((time.time() - t0) * 1000)
    db.add(row)
    db.add_all(stored_tables)
    if len(content) <= settings.database_pdf_max_bytes:
        pdf = PdfFileRow(
            documento_id=doc.id,
            user_id=user.user_id,
            original_filename=filename,
            content_type="application/pdf",
            size=len(content),
            is_deleted=False,
        )
        if is_configured():
            storage_path = f"anclora-tableextract/uploads/{user.user_id}/{doc.id}.pdf"
            try:
                result = await asyncio.to_thread(
                    put_object, storage_path, content, "application/pdf"
                )
                pdf.storage_path = result["path"]
                pdf.size = result["size"]
            except Exception as exc:
                logger.warning("S3-compatible upload failed, falling back to PostgreSQL: %s", exc)
                pdf.data = content
        else:
            pdf.data = content
        db.add(pdf)
    await db.flush()
    return row


async def _load_pdf_bytes(db: AsyncSession, doc_id: str, user_id: str):
    rec = await pdf_files.get_owned(db, doc_id, user_id)
    if not rec:
        return None, None
    if rec.storage_path:
        try:
            data, _ = await asyncio.to_thread(get_object, rec.storage_path)
            return data, rec
        except StorageUnavailable:
            logger.warning("Configured PDF object storage is unavailable")
            return None, rec
    return rec.data, rec


def _looks_like_header(row):
    from normalization import looks_like_number

    non_empty = [c["value"] for c in row if c.get("value", "").strip()]
    if not non_empty:
        return False
    return sum(looks_like_number(v) for v in non_empty) / len(non_empty) < 0.3


@app.get("/api/")
async def root():
    return {"message": "Anclora TableExtract API"}


@app.get("/api/health")
async def health():
    try:
        await check_database()
        return {"status": "ok", "database": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.post("/api/documents/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    lang: str = "es",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    results = []
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            results.append(
                {"nombre_archivo": f.filename, "error": "Solo se admiten archivos PDF"}
            )
            continue
        row = await _process_document(db, user, f.filename, await f.read(), lang)
        results.append(
            {
                "id": row.id,
                "nombre_archivo": row.nombre_archivo,
                "num_paginas": row.num_paginas,
                "num_tablas": row.num_tablas,
                "estado": row.estado,
                "process_ms": row.process_ms,
                "error": row.error,
            }
        )
    await db.commit()
    return {"documents": results}


@app.get("/api/documents")
async def list_documents(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return {
        "documents": [
            _doc_dict(row) for row in await documents.list_for_user(db, user.user_id)
        ]
    }


async def _owned_document(db, doc_id, user_id):
    row = await documents.get(db, doc_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return row


@app.get("/api/documents/{doc_id}")
async def get_document(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_document(db, doc_id, user.user_id)
    return {
        "documento": _doc_dict(await documents.get(db, doc_id, user.user_id)),
        "tablas": [
            _table_dict(row)
            for row in await documents.tables_for_user(db, doc_id, user.user_id)
        ],
    }


async def _owned_table(db, table_id, doc_id, user_id):
    row = await extracted_tables.get_owned(db, table_id, doc_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Tabla no encontrada")
    return row


@app.put("/api/documents/{doc_id}/cell")
async def update_cell(
    doc_id: str,
    update_payload: CellUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    table = await _owned_table(db, update_payload.table_id, doc_id, user.user_id)
    for cell in table.cells:
        if (
            cell["fila"] == update_payload.fila
            and cell["columna"] == update_payload.columna
        ):
            cell["valor"], cell["score_confianza"], cell["edited"] = (
                update_payload.valor,
                1.0,
                True,
            )
            break
    else:
        raise HTTPException(status_code=404, detail="Celda no encontrada")
    await db.commit()
    return {
        "ok": True,
        "fila": update_payload.fila,
        "columna": update_payload.columna,
        "valor": update_payload.valor,
    }


@app.put("/api/documents/{doc_id}/cell-state")
async def set_cell_state(
    doc_id: str,
    upd: CellStateUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    table = await _owned_table(db, upd.table_id, doc_id, user.user_id)
    updated = next(
        (
            cell
            for cell in table.cells
            if cell["fila"] == upd.fila and cell["columna"] == upd.columna
        ),
        None,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Celda no encontrada")
    updated.update(
        {
            "valor": upd.valor,
            "score_confianza": upd.score_confianza,
            "edited": upd.edited,
        }
    )
    if upd.norm_conf is not None:
        updated["norm_conf"] = upd.norm_conf
    if upd.reason_code is not None:
        updated["reason_code"] = upd.reason_code
    await db.commit()
    return {"ok": True, "cell": updated}


@app.post("/api/documents/{doc_id}/reprocess")
async def reprocess_document(
    doc_id: str,
    mode: str = "ocr",
    lang: str = "es",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _owned_document(db, doc_id, user.user_id)
    data, _ = await _load_pdf_bytes(db, doc_id, user.user_id)
    if data is None:
        raise HTTPException(
            status_code=404, detail="PDF original no disponible para reprocesar"
        )
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(data)
        tmp.flush()
        num_pages, raw_tables = await asyncio.to_thread(
            _process_pdf_sync, tmp.name, mode == "ocr", lang
        )
    stored = await _tables_from_raw(doc_id, user.user_id, raw_tables, lang)
    await db.execute(
        delete(ExtractedTableRow).where(
            ExtractedTableRow.documento_id == doc_id,
            ExtractedTableRow.user_id == user.user_id,
        )
    )
    db.add_all(stored)
    doc.num_tablas, doc.num_paginas, doc.estado = len(stored), num_pages, "pendiente"
    await db.commit()
    return {"ok": True, "num_tablas": len(stored), "mode": mode}


@app.post("/api/documents/{doc_id}/validate")
async def validate_document(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _owned_document(db, doc_id, user.user_id)
    doc.estado = "validado"
    await db.commit()
    return {"ok": True, "estado": "validado"}


@app.delete("/api/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pdf = await pdf_files.get_owned(db, doc_id, user.user_id)
    if not await documents.delete_owned(db, doc_id, user.user_id):
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if pdf and pdf.storage_path and is_configured():
        try:
            await asyncio.to_thread(delete_object, pdf.storage_path)
        except Exception as exc:
            logger.warning("S3-compatible delete failed for %s: %s", pdf.storage_path, exc)
    await db.commit()
    return {"ok": True}


@app.get("/api/documents/{doc_id}/file")
async def get_document_file(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data, _ = await _load_pdf_bytes(db, doc_id, user.user_id)
    if data is None:
        raise HTTPException(status_code=404, detail="PDF no disponible")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@app.get("/api/documents/{doc_id}/thumbnail")
async def get_document_thumbnail(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _owned_document(db, doc_id, user.user_id)
    data, _ = await _load_pdf_bytes(db, doc_id, user.user_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Miniatura no disponible")
    data = await asyncio.to_thread(render_first_page_thumb, data)
    if not data:
        raise HTTPException(status_code=404, detail="Miniatura no disponible")
    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=86400"},
    )


@app.put("/api/documents/{doc_id}/column-type")
async def update_column_type(
    doc_id: str,
    upd: ColumnTypeUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if upd.tipo not in ("date", "number", "text"):
        raise HTTPException(status_code=400, detail="Tipo no válido")
    table = await _owned_table(db, upd.table_id, doc_id, user.user_id)
    types = list(table.column_types or [])
    while len(types) <= upd.columna:
        types.append("text")
    types[upd.columna] = upd.tipo
    updated_cells = []
    for cell in table.cells:
        if cell["columna"] != upd.columna:
            continue
        if not cell.get("edited"):
            value, conf = normalize_value(cell.get("valor_original", ""), upd.tipo)
            cell.update(
                {
                    "valor": value,
                    "norm_conf": conf,
                    "score_confianza": combine_confidence(
                        cell.get("extraction_conf", 0.9), conf, bool(value.strip())
                    ),
                    "reason_code": reason_code(
                        upd.tipo,
                        cell.get("extraction_conf", 0.9),
                        conf,
                        bool(value.strip()),
                    ),
                }
            )
        updated_cells.append(cell)
    table.column_types = types
    await db.commit()
    return {"ok": True, "column_types": types, "cells": updated_cells}


@app.post("/api/documents/{doc_id}/date-autofill")
async def date_autofill(
    doc_id: str,
    upd: DateAutofill,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    table = await _owned_table(db, upd.table_id, doc_id, user.user_id)
    originals = [
        c.get("valor_original", "")
        for c in table.cells
        if c["columna"] == upd.columna and not c.get("edited")
    ]
    fmt = upd.fmt or detect_date_format(originals)[0]
    if not fmt:
        raise HTTPException(
            status_code=400, detail="No se pudo detectar un formato de fecha"
        )
    types = list(table.column_types or [])
    types.extend(["text"] * (upd.columna + 1 - len(types)))
    types[upd.columna] = "date"
    for cell in table.cells:
        if cell["columna"] == upd.columna and not cell.get("edited"):
            iso, ok = parse_date_with(cell.get("valor_original", ""), fmt)
            if ok:
                cell.update(
                    {
                        "valor": iso,
                        "norm_conf": 1.0,
                        "score_confianza": combine_confidence(
                            cell.get("extraction_conf", 0.9), 1.0, True
                        ),
                        "reason_code": "high",
                    }
                )
    table.column_types = types
    await db.commit()
    return {
        "ok": True,
        "fmt": fmt,
        "column_types": types,
        "cells": [c for c in table.cells if c["columna"] == upd.columna],
    }


@app.put("/api/documents/{doc_id}/column-rules")
async def set_column_rules(
    doc_id: str,
    upd: ColumnRulesUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    table = await _owned_table(db, upd.table_id, doc_id, user.user_id)
    rules = dict(table.column_rules or {})
    value = upd.rules.model_dump()
    if (
        not value.get("required")
        and value.get("min") is None
        and value.get("max") is None
    ):
        rules.pop(str(upd.columna), None)
    else:
        rules[str(upd.columna)] = value
    table.column_rules = rules
    await db.commit()
    return {"ok": True, "column_rules": rules}


async def _export_items(db, user_id, doc_ids):
    items = []
    for doc_id in doc_ids:
        doc = await documents.get(db, doc_id, user_id)
        if doc:
            items.append(
                (
                    _doc_dict(doc),
                    [
                        _table_dict(t)
                        for t in await documents.tables_for_user(db, doc_id, user_id)
                    ],
                )
            )
    return items


@app.post("/api/documents/export-batch")
async def export_batch(
    payload: BatchExport,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not payload.doc_ids:
        raise HTTPException(status_code=400, detail="Selecciona al menos un documento")
    items = await _export_items(db, user.user_id, payload.doc_ids)
    if not items:
        raise HTTPException(status_code=404, detail="No se encontraron documentos")
    if payload.format == "xlsx":
        data, media, ext = (
            export_batch_xlsx(items),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xlsx",
        )
    elif payload.format in ("csv", "json"):
        data, media, ext = (
            export_batch_zip(items, payload.format),
            "application/zip",
            "zip",
        )
    else:
        raise HTTPException(status_code=400, detail="Formato no soportado")
    for doc, _ in items:
        (await documents.get(db, doc["id"], user.user_id)).estado = "exportado"
    await db.commit()
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="anclora_export.{ext}"'},
    )


@app.get("/api/documents/{doc_id}/export")
async def export_document(
    doc_id: str,
    format: str = "xlsx",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _owned_document(db, doc_id, user.user_id)
    payload_doc = _doc_dict(doc)
    tables = [
        _table_dict(t)
        for t in await documents.tables_for_user(db, doc_id, user.user_id)
    ]
    base = os.path.splitext(doc.nombre_archivo)[0]
    if format == "json":
        data, media, ext = export_json(payload_doc, tables), "application/json", "json"
    elif format == "csv":
        data, media, ext = export_csv(payload_doc, tables), "text/csv", "csv"
    elif format == "xlsx":
        data, media, ext = (
            export_xlsx(payload_doc, tables),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xlsx",
        )
    else:
        raise HTTPException(status_code=400, detail="Formato no soportado")
    doc.estado = "exportado"
    await db.commit()
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{base}.{ext}"'},
    )


@app.post("/api/documents/{doc_id}/export-sheets")
async def export_sheets(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not is_configured():
        raise HTTPException(status_code=400, detail="Google Sheets no está configurado")
    doc = await _owned_document(db, doc_id, user.user_id)
    token_row = await google_tokens.get(db, user.user_id)
    if not token_row:
        state = uuid.uuid4().hex
        db.add(OAuthStateRow(state=state, user_id=user.user_id, doc_id=doc_id))
        await db.commit()
        return {"auth_required": True, "auth_url": build_auth_url(state)}
    try:
        url, updated = await asyncio.to_thread(
            export_document_to_sheets,
            _token_dict(token_row),
            _doc_dict(doc),
            [
                _table_dict(t)
                for t in await documents.tables_for_user(db, doc_id, user.user_id)
            ],
        )
    except Exception:
        await db.delete(token_row)
        state = uuid.uuid4().hex
        db.add(OAuthStateRow(state=state, user_id=user.user_id, doc_id=doc_id))
        await db.commit()
        return {"auth_required": True, "auth_url": build_auth_url(state)}
    if updated:
        for key, value in updated.items():
            if key in {
                "access_token",
                "refresh_token",
                "token_uri",
                "client_id",
                "client_secret",
                "scopes",
                "expires_at",
            }:
                setattr(
                    token_row,
                    key,
                    (
                        datetime.fromisoformat(value)
                        if key == "expires_at" and isinstance(value, str)
                        else value
                    ),
                )
    doc.estado = "exportado"
    await db.commit()
    return {"ok": True, "url": url}


@app.get("/api/oauth/sheets/callback")
async def sheets_callback(
    code: str = None,
    state: str = None,
    error: str = None,
    db: AsyncSession = Depends(get_db),
):
    front = settings.frontend_url.rstrip("/")
    if error or not code or not state:
        return RedirectResponse(f"{front}/history?sheets=error")
    state_row = await oauth_states.get(db, state)
    if not state_row:
        return RedirectResponse(f"{front}/history?sheets=error")
    doc_id, user_id = state_row.doc_id, state_row.user_id
    await db.delete(state_row)
    try:
        token = await asyncio.to_thread(exchange_code, code)
    except Exception:
        await db.commit()
        return RedirectResponse(f"{front}/review/{doc_id}?sheets=error")
    token_fields = {
        k: v
        for k, v in token.items()
        if k
        in {
            "access_token",
            "refresh_token",
            "token_uri",
            "client_id",
            "client_secret",
            "scopes",
            "expires_at",
        }
    }
    if isinstance(token_fields.get("expires_at"), str):
        token_fields["expires_at"] = datetime.fromisoformat(token_fields["expires_at"])
    db.add(GoogleTokenRow(user_id=user_id, **token_fields))
    await db.commit()
    return RedirectResponse(f"{front}/review/{doc_id}?sheets=connected")


@app.post("/api/dev/login")
async def local_qa_login(
    request: Request,
    response: Response,
    x_local_qa_token: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    if settings.app_env != "development" or not settings.local_qa_login_enabled:
        raise HTTPException(status_code=404, detail="Not found")
    if request.client is None or request.client.host not in {
        "127.0.0.1",
        "::1",
        "localhost",
    }:
        raise HTTPException(status_code=403, detail="Localhost only")
    if not x_local_qa_token or x_local_qa_token != settings.local_qa_login_token:
        raise HTTPException(status_code=401, detail="Invalid QA token")
    row = await users.get_by_email(db, settings.qa_user_email)
    if row is None:
        row = await users.upsert(
            db,
            user_id=f"user_{uuid.uuid4().hex[:12]}",
            email=settings.qa_user_email,
            name="TableExtract QA",
            is_test_user=True,
        )
    elif not row.is_test_user:
        raise HTTPException(
            status_code=500, detail="Configured QA user is not marked as test user"
        )
    token = f"qa_{uuid.uuid4().hex}"
    await sessions.upsert(
        db,
        token=token,
        user_id=row.user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
    )
    await db.commit()
    response.set_cookie(
        "session_token",
        token,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
        max_age=SESSION_DAYS * 86400,
    )
    return {"user": {"user_id": row.user_id, "email": row.email, "name": row.name}}


app.include_router(auth_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await check_database()


@app.on_event("shutdown")
async def shutdown():
    await close_engine()
