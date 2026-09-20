"""Schema validation layer (Pydantic / JSON-schema style), kept separate from
extraction. Validates the shape of an extracted table and computes per-cell
final confidence combining extraction + normalization signals."""
from typing import List
from pydantic import BaseModel


class ValidatedCell(BaseModel):
    fila: int
    columna: int
    valor: str
    valor_original: str
    score_confianza: float
    pagina: int


class ValidatedTable(BaseModel):
    columnas: List[str]
    column_types: List[str]
    num_filas: int
    num_columnas: int
    cells: List[ValidatedCell]


def combine_confidence(extraction_conf: float, norm_conf: float, has_value: bool) -> float:
    score = extraction_conf * norm_conf
    if not has_value:
        score = min(score, 0.5)
    return round(max(0.0, min(1.0, score)), 3)


def validate_table(columnas, column_types, rows_meta) -> ValidatedTable:
    """rows_meta: list of rows, each a list of dicts:
    {value, original, extraction_conf, norm_conf, page}"""
    cells: List[ValidatedCell] = []
    num_cols = len(columnas)
    for r, row in enumerate(rows_meta):
        for c in range(num_cols):
            cell = row[c] if c < len(row) else {
                "value": "", "original": "", "extraction_conf": 0.5,
                "norm_conf": 0.5, "page": rows_meta and row and row[0].get("page", 1) or 1,
            }
            has_value = bool((cell.get("value") or "").strip())
            score = combine_confidence(
                cell.get("extraction_conf", 0.9),
                cell.get("norm_conf", 1.0),
                has_value,
            )
            cells.append(ValidatedCell(
                fila=r,
                columna=c,
                valor=cell.get("value", ""),
                valor_original=cell.get("original", ""),
                score_confianza=score,
                pagina=cell.get("page", 1),
            ))
    return ValidatedTable(
        columnas=columnas,
        column_types=column_types,
        num_filas=len(rows_meta),
        num_columnas=num_cols,
        cells=cells,
    )
