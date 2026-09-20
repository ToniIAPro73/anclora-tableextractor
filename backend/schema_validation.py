"""Schema validation layer (Pydantic / JSON-schema style), kept separate from
extraction. Combines extraction + normalization signals into a final per-cell
confidence and a deterministic reason code explaining doubtful cells."""
from typing import List, Optional
from pydantic import BaseModel


class ValidatedCell(BaseModel):
    fila: int
    columna: int
    valor: str
    valor_original: str
    score_confianza: float
    pagina: int
    extraction_conf: float = 0.9
    norm_conf: float = 1.0
    bbox: Optional[List[float]] = None
    reason_code: str = "high"
    edited: bool = False


def combine_confidence(extraction_conf: float, norm_conf: float, has_value: bool) -> float:
    score = extraction_conf * norm_conf
    if not has_value:
        score = min(score, 0.5)
    return round(max(0.0, min(1.0, score)), 3)


def reason_code(col_type: str, extraction_conf: float, norm_conf: float, has_value: bool) -> str:
    if not has_value:
        return "empty"
    if extraction_conf < 0.9:
        return "ocr_low"
    if norm_conf < 1.0:
        if col_type == "date":
            return "date_ambiguous"
        if col_type == "number":
            return "number_ambiguous"
        return "norm_ambiguous"
    return "high"


def build_cells(columnas, column_types, rows_meta) -> List[ValidatedCell]:
    """rows_meta: list of rows, each a list of dicts with keys:
    value, original, extraction_conf, norm_conf, page, bbox."""
    cells: List[ValidatedCell] = []
    num_cols = len(columnas)
    for r, row in enumerate(rows_meta):
        for c in range(num_cols):
            cell = row[c] if c < len(row) else {}
            has_value = bool((cell.get("value") or "").strip())
            ext = cell.get("extraction_conf", 0.9)
            nrm = cell.get("norm_conf", 1.0)
            score = combine_confidence(ext, nrm, has_value)
            cells.append(ValidatedCell(
                fila=r,
                columna=c,
                valor=cell.get("value", ""),
                valor_original=cell.get("original", ""),
                score_confianza=score,
                pagina=cell.get("page", 1),
                extraction_conf=ext,
                norm_conf=nrm,
                bbox=cell.get("bbox"),
                reason_code=reason_code(column_types[c] if c < len(column_types) else "text", ext, nrm, has_value),
            ))
    return cells
