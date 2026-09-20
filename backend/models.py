import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any
from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


# ---------- Auth ----------
class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    created_at: str = Field(default_factory=now_iso)


# ---------- Domain models ----------
class Cell(BaseModel):
    """Celda(id, tabla_id, fila, columna, valor, score_confianza, valor_original)"""
    fila: int
    columna: int
    valor: str = ""
    valor_original: str = ""
    score_confianza: float = 1.0
    pagina: int = 1
    edited: bool = False


class TablaExtraida(BaseModel):
    """Tabla_extraida(id, documento_id, pagina_origen, filas, columnas)"""
    id: str = Field(default_factory=lambda: new_id("tbl"))
    documento_id: str
    pagina_origen: int
    source_pages: List[int] = []
    extraction_method: str = "native"  # native | ocr
    columnas: List[str] = []
    column_types: List[str] = []
    num_filas: int = 0
    num_columnas: int = 0
    cells: List[Cell] = []


class Documento(BaseModel):
    """Documento(id, nombre_archivo, fecha_carga, estado, num_paginas)"""
    id: str = Field(default_factory=lambda: new_id("doc"))
    user_id: str
    nombre_archivo: str
    fecha_carga: str = Field(default_factory=now_iso)
    estado: str = "pendiente"  # pendiente | validado | exportado
    num_paginas: int = 0
    num_tablas: int = 0
    process_ms: int = 0
    error: Optional[str] = None


class CellUpdate(BaseModel):
    table_id: str
    fila: int
    columna: int
    valor: str
