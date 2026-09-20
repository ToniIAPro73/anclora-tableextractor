"""Extraction layer: native (pdfplumber) with OCR fallback (Tesseract).

Kept fully separate from schema validation. Produces raw rows with per-cell
extraction confidence + origin page. Does NOT normalize (that is a later,
deterministic layer) and never calls an LLM.
"""
import logging

import pdfplumber

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from pdf2image import convert_from_path
    _OCR_AVAILABLE = True
except Exception:  # pragma: no cover
    _OCR_AVAILABLE = False


def _clean(v):
    return (v or "").strip()


def _build_native_table(raw_rows, page_num):
    """raw_rows: list[list[str|None]] from pdfplumber.extract_tables()"""
    ncols = max((len(r) for r in raw_rows), default=0)
    rows = []
    for r in raw_rows:
        row = []
        for c in range(ncols):
            val = _clean(r[c]) if c < len(r) else ""
            has = bool(val)
            row.append({
                "value": val,
                "original": val,
                "extraction_conf": 0.98 if has else 0.5,
                "page": page_num,
            })
        rows.append(row)
    return {"rows": rows, "ncols": ncols, "page": page_num, "method": "native"}


def _ocr_page(path, page_num, dpi=200):
    """Best-effort OCR table reconstruction for a scanned page."""
    if not _OCR_AVAILABLE:
        return None
    images = convert_from_path(path, first_page=page_num, last_page=page_num, dpi=dpi)
    if not images:
        return None
    data = pytesseract.image_to_data(images[0], output_type=pytesseract.Output.DICT)

    # group words into text lines
    lines = {}
    all_words = []
    for i in range(len(data["text"])):
        txt = (data["text"][i] or "").strip()
        if not txt:
            continue
        conf = int(data["conf"][i]) if str(data["conf"][i]).lstrip("-").isdigit() else -1
        if conf < 0:
            conf = 60
        word = {
            "text": txt,
            "left": data["left"][i],
            "right": data["left"][i] + data["width"][i],
            "top": data["top"][i],
            "conf": conf,
        }
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(word)
        all_words.append(word)

    if len(all_words) < 4:
        return None

    # cluster column boundaries from word left positions
    lefts = sorted(w["left"] for w in all_words)
    widths = sorted(w["right"] - w["left"] for w in all_words)
    med_w = widths[len(widths) // 2] if widths else 40
    gap = max(30, int(med_w * 1.4))
    boundaries = []
    for l in lefts:
        if boundaries and l - boundaries[-1] <= gap:
            continue
        boundaries.append(l)
    if len(boundaries) < 2:
        return None

    def col_of(left):
        best, bi = 10 ** 9, 0
        for idx, b in enumerate(boundaries):
            if abs(left - b) < best:
                best, bi = abs(left - b), idx
        return bi

    ncols = len(boundaries)
    ordered = sorted(lines.values(), key=lambda ws: min(w["top"] for w in ws))
    rows = []
    for ws in ordered:
        cells = [None] * ncols
        confs = [None] * ncols
        for w in sorted(ws, key=lambda x: x["left"]):
            ci = col_of(w["left"])
            if cells[ci] is None:
                cells[ci], confs[ci] = w["text"], w["conf"]
            else:
                cells[ci] += " " + w["text"]
                confs[ci] = min(confs[ci], w["conf"])
        row = []
        for c in range(ncols):
            val = cells[c] or ""
            row.append({
                "value": val,
                "original": val,
                "extraction_conf": round((confs[c] or 55) / 100.0, 3) if val else 0.4,
                "page": page_num,
            })
        rows.append(row)
    return {"rows": rows, "ncols": ncols, "page": page_num, "method": "ocr"}


def extract_tables(path):
    """Returns (num_pages, [table_dict,...]) with raw (un-normalized) cells."""
    tables = []
    with pdfplumber.open(path) as pdf:
        num_pages = len(pdf.pages)
        for pidx, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            found = page.extract_tables()
            if found:
                for raw in found:
                    if raw and len(raw) >= 1:
                        tables.append(_build_native_table(raw, pidx))
            elif len(page_text.strip()) < 15:
                ocr = _ocr_page(path, pidx)
                if ocr and ocr["rows"]:
                    tables.append(ocr)
    return num_pages, tables


def merge_multipage(tables):
    """Merge consecutive-page tables with identical column count into one,
    preserving per-row origin page (handles multipage tables without dup rows)."""
    if not tables:
        return tables
    merged = [tables[0]]
    for t in tables[1:]:
        prev = merged[-1]
        if t["ncols"] == prev["ncols"] and t["page"] == prev["page"] + 1 and t["method"] == prev["method"]:
            prev["rows"].extend(t["rows"])
            prev.setdefault("source_pages", [prev["page"]])
            prev["source_pages"].append(t["page"])
        else:
            merged.append(t)
    for m in merged:
        m.setdefault("source_pages", [m["page"]])
    return merged
