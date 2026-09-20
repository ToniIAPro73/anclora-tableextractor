import asyncio
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from starlette.middleware.cors import CORSMiddleware

from auth import auth_router, get_current_user
from column_inference import infer_column_names
from db import db
from exporters import (export_batch_xlsx, export_batch_zip, export_csv,
                       export_json, export_xlsx)
from extraction import extract_tables, merge_multipage
from models import (BatchExport, CellStateUpdate, CellUpdate, ColumnTypeUpdate,
                    Documento, User, new_id, now_iso)
from normalization import infer_column_type, normalize_value
from schema_validation import build_cells, combine_confidence, reason_code

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Anclora TableExtract")


# ---------------- Pipeline ----------------
def _process_pdf_sync(path, force_ocr=False):
    num_pages, tables = extract_tables(path, force_ocr=force_ocr)
    tables = merge_multipage(tables)
    return num_pages, tables


async def _tables_from_raw(doc_id, user_id, raw_tables, lang):
    """Build stored-table dicts (with inferred columns, deterministic
    normalization and per-cell confidence) from raw extracted tables."""
    stored_tables = []
    for raw in raw_tables:
        rows = raw["rows"]
        ncols = raw["ncols"]
        if ncols == 0 or not rows:
            continue

        # LLM: infer column names ONLY (never data)
        columnas = await infer_column_names(rows, ncols, lang=lang)

        # decide if first row is a header (drop it from data if so)
        data_rows = rows
        header_like = _looks_like_header(rows[0]) if rows else False
        if header_like and len(rows) > 1:
            data_rows = rows[1:]

        # deterministic column-type inference + normalization
        column_types = []
        for c in range(ncols):
            col_vals = [(r[c]["value"] if c < len(r) else "") for r in data_rows]
            column_types.append(infer_column_type(col_vals))

        rows_meta = []
        for r in data_rows:
            meta_row = []
            for c in range(ncols):
                cell = r[c] if c < len(r) else {"value": "", "original": "", "extraction_conf": 0.5, "page": raw["page"], "bbox": None}
                norm_val, norm_conf = normalize_value(cell["value"], column_types[c])
                meta_row.append({
                    "value": norm_val,
                    "original": cell.get("original", cell["value"]),
                    "extraction_conf": cell.get("extraction_conf", 0.9),
                    "norm_conf": norm_conf,
                    "page": cell.get("page", raw["page"]),
                    "bbox": cell.get("bbox"),
                })
            rows_meta.append(meta_row)

        cells = build_cells(columnas, column_types, rows_meta)
        stored_tables.append({
            "id": new_id("tbl"),
            "documento_id": doc_id,
            "user_id": user_id,
            "pagina_origen": raw["page"],
            "source_pages": raw.get("source_pages", [raw["page"]]),
            "extraction_method": raw["method"],
            "columnas": columnas,
            "column_types": column_types,
            "num_filas": len(rows_meta),
            "num_columnas": ncols,
            "cells": [c.model_dump() for c in cells],
        })
    return stored_tables


async def _process_document(user: User, filename: str, content: bytes, lang: str):
    t0 = time.time()
    doc = Documento(user_id=user.user_id, nombre_archivo=filename)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        try:
            num_pages, raw_tables = await asyncio.to_thread(_process_pdf_sync, tmp.name)
        except Exception as e:
            logger.exception("extraction failed")
            doc.error = str(e)
            await db.documents.insert_one(doc.model_dump())
            return doc

    doc.num_paginas = num_pages
    stored_tables = await _tables_from_raw(doc.id, user.user_id, raw_tables, lang)

    doc.num_tablas = len(stored_tables)
    doc.process_ms = int((time.time() - t0) * 1000)
    await db.documents.insert_one(doc.model_dump())
    if stored_tables:
        await db.tables.insert_many(stored_tables)
    if len(content) <= 15_000_000:
        await db.pdf_files.replace_one(
            {"documento_id": doc.id},
            {"documento_id": doc.id, "user_id": user.user_id, "data": content},
            upsert=True,
        )
    return doc


def _looks_like_header(row):
    from normalization import looks_like_number
    non_empty = [c["value"] for c in row if c.get("value", "").strip()]
    if not non_empty:
        return False
    numeric = sum(1 for v in non_empty if looks_like_number(v))
    return numeric / len(non_empty) < 0.3


# ---------------- Routes ----------------
@app.get("/api/")
async def root():
    return {"message": "Anclora TableExtract API"}


@app.post("/api/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...), lang: str = "es", user: User = Depends(get_current_user)):
    results = []
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            results.append({"nombre_archivo": f.filename, "error": "Solo se admiten archivos PDF"})
            continue
        content = await f.read()
        doc = await _process_document(user, f.filename, content, lang)
        results.append({
            "id": doc.id,
            "nombre_archivo": doc.nombre_archivo,
            "num_paginas": doc.num_paginas,
            "num_tablas": doc.num_tablas,
            "estado": doc.estado,
            "process_ms": doc.process_ms,
            "error": doc.error,
        })
    return {"documents": results}


@app.get("/api/documents")
async def list_documents(user: User = Depends(get_current_user)):
    docs = await db.documents.find({"user_id": user.user_id}, {"_id": 0}).sort("fecha_carga", -1).to_list(500)
    return {"documents": docs}


@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: str, user: User = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": doc_id, "user_id": user.user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    tables = await db.tables.find({"documento_id": doc_id, "user_id": user.user_id}, {"_id": 0}).to_list(200)
    return {"documento": doc, "tablas": tables}


@app.put("/api/documents/{doc_id}/cell")
async def update_cell(doc_id: str, update: CellUpdate, user: User = Depends(get_current_user)):
    table = await db.tables.find_one({"id": update.table_id, "documento_id": doc_id, "user_id": user.user_id}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Tabla no encontrada")
    updated = False
    for cell in table["cells"]:
        if cell["fila"] == update.fila and cell["columna"] == update.columna:
            cell["valor"] = update.valor
            cell["score_confianza"] = 1.0  # user-corrected = validated
            cell["edited"] = True
            updated = True
            break
    if not updated:
        raise HTTPException(status_code=404, detail="Celda no encontrada")
    await db.tables.update_one({"id": update.table_id}, {"$set": {"cells": table["cells"]}})
    return {"ok": True, "fila": update.fila, "columna": update.columna, "valor": update.valor}


@app.put("/api/documents/{doc_id}/cell-state")
async def set_cell_state(doc_id: str, upd: CellStateUpdate, user: User = Depends(get_current_user)):
    """Set an exact cell state — used by client undo/redo to restore prior values."""
    table = await db.tables.find_one({"id": upd.table_id, "documento_id": doc_id, "user_id": user.user_id}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Tabla no encontrada")
    updated = None
    for cell in table["cells"]:
        if cell["fila"] == upd.fila and cell["columna"] == upd.columna:
            cell["valor"] = upd.valor
            cell["score_confianza"] = upd.score_confianza
            cell["edited"] = upd.edited
            if upd.norm_conf is not None:
                cell["norm_conf"] = upd.norm_conf
            if upd.reason_code is not None:
                cell["reason_code"] = upd.reason_code
            updated = cell
            break
    if updated is None:
        raise HTTPException(status_code=404, detail="Celda no encontrada")
    await db.tables.update_one({"id": upd.table_id}, {"$set": {"cells": table["cells"]}})
    return {"ok": True, "cell": updated}


@app.post("/api/documents/{doc_id}/reprocess")
async def reprocess_document(doc_id: str, mode: str = "ocr", lang: str = "es", user: User = Depends(get_current_user)):
    """Re-run extraction on the stored PDF. mode='ocr' forces Tesseract OCR on
    every page (useful when native detection missed a scanned table)."""
    doc = await db.documents.find_one({"id": doc_id, "user_id": user.user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    rec = await db.pdf_files.find_one({"documento_id": doc_id, "user_id": user.user_id}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="PDF original no disponible para reprocesar")

    data = rec["data"]
    if not isinstance(data, (bytes, bytearray)):
        data = bytes(data)
    force_ocr = mode == "ocr"
    t0 = time.time()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(data)
        tmp.flush()
        try:
            num_pages, raw_tables = await asyncio.to_thread(_process_pdf_sync, tmp.name, force_ocr)
        except Exception as e:
            logger.exception("reprocess failed")
            raise HTTPException(status_code=500, detail=f"Error al reprocesar: {e}")

    stored_tables = await _tables_from_raw(doc_id, user.user_id, raw_tables, lang)
    await db.tables.delete_many({"documento_id": doc_id})
    if stored_tables:
        await db.tables.insert_many(stored_tables)
    await db.documents.update_one(
        {"id": doc_id},
        {"$set": {"estado": "pendiente", "num_tablas": len(stored_tables), "num_paginas": num_pages, "process_ms": int((time.time() - t0) * 1000)}},
    )
    return {"ok": True, "num_tablas": len(stored_tables), "mode": mode}


@app.post("/api/documents/{doc_id}/validate")
async def validate_document(doc_id: str, user: User = Depends(get_current_user)):
    res = await db.documents.update_one(
        {"id": doc_id, "user_id": user.user_id}, {"$set": {"estado": "validado"}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return {"ok": True, "estado": "validado"}


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str, user: User = Depends(get_current_user)):
    res = await db.documents.delete_one({"id": doc_id, "user_id": user.user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    await db.tables.delete_many({"documento_id": doc_id})
    await db.pdf_files.delete_many({"documento_id": doc_id})
    return {"ok": True}


@app.get("/api/documents/{doc_id}/file")
async def get_document_file(doc_id: str, user: User = Depends(get_current_user)):
    rec = await db.pdf_files.find_one({"documento_id": doc_id, "user_id": user.user_id}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="PDF no disponible")
    data = rec["data"]
    if not isinstance(data, (bytes, bytearray)):
        data = bytes(data)
    return Response(content=data, media_type="application/pdf", headers={"Cache-Control": "private, max-age=3600"})


@app.put("/api/documents/{doc_id}/column-type")
async def update_column_type(doc_id: str, upd: ColumnTypeUpdate, user: User = Depends(get_current_user)):
    if upd.tipo not in ("date", "number", "text"):
        raise HTTPException(status_code=400, detail="Tipo no válido")
    table = await db.tables.find_one({"id": upd.table_id, "documento_id": doc_id, "user_id": user.user_id}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Tabla no encontrada")

    types = table.get("column_types", [])
    while len(types) <= upd.columna:
        types.append("text")
    types[upd.columna] = upd.tipo

    updated_cells = []
    for cell in table["cells"]:
        if cell["columna"] != upd.columna:
            continue
        if cell.get("edited"):
            updated_cells.append(cell)
            continue
        norm_val, norm_conf = normalize_value(cell.get("valor_original", ""), upd.tipo)
        has_value = bool(norm_val.strip())
        ext = cell.get("extraction_conf", 0.9)
        cell["valor"] = norm_val
        cell["norm_conf"] = norm_conf
        cell["score_confianza"] = combine_confidence(ext, norm_conf, has_value)
        cell["reason_code"] = reason_code(upd.tipo, ext, norm_conf, has_value)
        updated_cells.append(cell)

    await db.tables.update_one({"id": upd.table_id}, {"$set": {"cells": table["cells"], "column_types": types}})
    return {"ok": True, "column_types": types, "cells": updated_cells}


@app.post("/api/documents/export-batch")
async def export_batch(payload: BatchExport, user: User = Depends(get_current_user)):
    if not payload.doc_ids:
        raise HTTPException(status_code=400, detail="Selecciona al menos un documento")
    items = []
    for did in payload.doc_ids:
        doc = await db.documents.find_one({"id": did, "user_id": user.user_id}, {"_id": 0})
        if not doc:
            continue
        tables = await db.tables.find({"documento_id": did, "user_id": user.user_id}, {"_id": 0}).to_list(200)
        items.append((doc, tables))
    if not items:
        raise HTTPException(status_code=404, detail="No se encontraron documentos")

    if payload.format == "xlsx":
        data = export_batch_xlsx(items)
        media, ext = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    elif payload.format in ("csv", "json"):
        data = export_batch_zip(items, payload.format)
        media, ext = "application/zip", "zip"
    else:
        raise HTTPException(status_code=400, detail="Formato no soportado")

    ids = [d["id"] for d, _ in items]
    await db.documents.update_many({"id": {"$in": ids}, "user_id": user.user_id}, {"$set": {"estado": "exportado"}})
    return Response(content=data, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="anclora_export.{ext}"'
    })


@app.get("/api/documents/{doc_id}/export")
async def export_document(doc_id: str, format: str = "xlsx", user: User = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": doc_id, "user_id": user.user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    tables = await db.tables.find({"documento_id": doc_id, "user_id": user.user_id}, {"_id": 0}).to_list(200)

    base = os.path.splitext(doc["nombre_archivo"])[0]
    if format == "json":
        data, media, ext = export_json(doc, tables), "application/json", "json"
    elif format == "csv":
        data, media, ext = export_csv(doc, tables), "text/csv", "csv"
    elif format == "xlsx":
        data = export_xlsx(doc, tables)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    else:
        raise HTTPException(status_code=400, detail="Formato no soportado")

    await db.documents.update_one({"id": doc_id}, {"$set": {"estado": "exportado"}})
    return Response(content=data, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="{base}.{ext}"'
    })


app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown():
    pass
