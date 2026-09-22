"""Safe importer for an explicit JSON export from the legacy database.

The script never connects to or mutates the legacy database. Export data must be
provided explicitly, and execution still requires the production migration guard.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import get_settings
from db.models import DocumentRow, ExtractedTableRow, UserRow
from db.session import close_engine, get_session_factory


async def main(source: Path, execute: bool):
    settings = get_settings()
    payload = json.loads(source.read_text())
    collections = {
        key: value if isinstance(value, list) else [] for key, value in payload.items()
    }
    counts = {key: len(value) for key, value in collections.items()}
    for key, count in counts.items():
        print(f"{key}: {count}")
    if not execute:
        print("dry-run: no source or destination data changed")
        return
    if (
        settings.database_target == "production"
        and not settings.allow_production_migrations
    ):
        raise RuntimeError(
            "Refusing production import: set ALLOW_PRODUCTION_MIGRATIONS=true explicitly"
        )
    async with get_session_factory()() as session:
        for item in collections.get("users", []):
            if await session.get(UserRow, item["user_id"]):
                continue
            session.add(
                UserRow(
                    user_id=item["user_id"],
                    email=item["email"],
                    name=item.get("name", ""),
                    picture=item.get("picture"),
                    is_test_user=bool(item.get("is_test_user", False)),
                )
            )
        for item in collections.get("documents", []):
            if not await session.get(DocumentRow, item["id"]):
                session.add(
                    DocumentRow(
                        id=item["id"],
                        user_id=item["user_id"],
                        nombre_archivo=item["nombre_archivo"],
                        estado=item.get("estado", "pendiente"),
                        num_paginas=item.get("num_paginas", 0),
                        num_tablas=item.get("num_tablas", 0),
                        process_ms=item.get("process_ms", 0),
                        thumb_path=item.get("thumb_path"),
                        error=item.get("error"),
                    )
                )
        for item in collections.get("extracted_tables", []):
            if not await session.get(ExtractedTableRow, item["id"]):
                session.add(
                    ExtractedTableRow(
                        id=item["id"],
                        documento_id=item["documento_id"],
                        user_id=item["user_id"],
                        pagina_origen=item.get("pagina_origen", 1),
                        source_pages=item.get("source_pages", []),
                        extraction_method=item.get("extraction_method", "native"),
                        columnas=item.get("columnas", []),
                        column_types=item.get("column_types", []),
                        num_filas=item.get("num_filas", 0),
                        num_columnas=item.get("num_columnas", 0),
                        cells=item.get("cells", []),
                        column_rules=item.get("column_rules", {}),
                    )
                )
        await session.commit()
    print("import applied")
    await close_engine()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source",
        type=Path,
        help="Explicit JSON export; never a live database connection",
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.source, args.execute))
