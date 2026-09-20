"""Export layer: xlsx / csv / json with origin-page + confidence metadata."""
import io
import json

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


def _grid(table):
    """Return (columns, rows_of_values, rows_of_meta) from a stored table dict."""
    ncols = table["num_columnas"]
    nrows = table["num_filas"]
    values = [["" for _ in range(ncols)] for _ in range(nrows)]
    meta = [[{} for _ in range(ncols)] for _ in range(nrows)]
    for cell in table["cells"]:
        r, c = cell["fila"], cell["columna"]
        if r < nrows and c < ncols:
            values[r][c] = cell.get("valor", "")
            meta[r][c] = {"score": cell.get("score_confianza", 1.0), "page": cell.get("pagina", 1)}
    return table["columnas"], values, meta


def export_json(document, tables):
    payload = {
        "documento": {
            "id": document["id"],
            "nombre_archivo": document["nombre_archivo"],
            "num_paginas": document["num_paginas"],
            "estado": document["estado"],
        },
        "tablas": [],
    }
    for t in tables:
        cols, values, meta = _grid(t)
        rows = []
        for r in range(len(values)):
            row = {}
            for c in range(len(cols)):
                row[cols[c]] = {
                    "valor": values[r][c],
                    "score_confianza": meta[r][c].get("score", 1.0),
                    "pagina_origen": meta[r][c].get("page", 1),
                }
            rows.append(row)
        payload["tablas"].append({
            "id": t["id"],
            "pagina_origen": t["pagina_origen"],
            "source_pages": t.get("source_pages", [t["pagina_origen"]]),
            "extraction_method": t["extraction_method"],
            "columnas": cols,
            "filas": rows,
        })
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def export_csv(document, tables):
    buf = io.StringIO()
    for ti, t in enumerate(tables):
        cols, values, meta = _grid(t)
        buf.write(f"# Tabla {ti + 1} | paginas: {t.get('source_pages', [t['pagina_origen']])} | metodo: {t['extraction_method']}\n")
        header = []
        for c in cols:
            header += [c, f"{c}__score", f"{c}__pagina"]
        buf.write(",".join(_csv_escape(h) for h in header) + "\n")
        for r in range(len(values)):
            line = []
            for c in range(len(cols)):
                line += [values[r][c], str(meta[r][c].get("score", "")), str(meta[r][c].get("page", ""))]
            buf.write(",".join(_csv_escape(x) for x in line) + "\n")
        buf.write("\n")
    return buf.getvalue().encode("utf-8")


def _csv_escape(v):
    v = "" if v is None else str(v)
    if any(ch in v for ch in [",", '"', "\n"]):
        return '"' + v.replace('"', '""') + '"'
    return v


def export_xlsx(document, tables):
    wb = Workbook()
    wb.remove(wb.active)
    green = PatternFill("solid", fgColor="D1FAE5")
    amber = PatternFill("solid", fgColor="FEF3C7")
    red = PatternFill("solid", fgColor="FEE2E2")
    header_fill = PatternFill("solid", fgColor="0EA5E9")
    header_font = Font(bold=True, color="FFFFFF")

    for ti, t in enumerate(tables):
        cols, values, meta = _grid(t)
        ws = wb.create_sheet(title=f"Tabla_{ti + 1}"[:31])
        for c, name in enumerate(cols, start=1):
            cell = ws.cell(row=1, column=c, value=name)
            cell.fill = header_fill
            cell.font = header_font
        pcol = len(cols) + 1
        h = ws.cell(row=1, column=pcol, value="_pagina_origen")
        h.font = header_font
        h.fill = header_fill
        for r in range(len(values)):
            for c in range(len(cols)):
                cell = ws.cell(row=r + 2, column=c + 1, value=values[r][c])
                score = meta[r][c].get("score", 1.0)
                cell.fill = green if score >= 0.9 else amber if score >= 0.6 else red
            page_vals = sorted({meta[r][c].get("page", 1) for c in range(len(cols))})
            ws.cell(row=r + 2, column=pcol, value=", ".join(str(p) for p in page_vals))
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
