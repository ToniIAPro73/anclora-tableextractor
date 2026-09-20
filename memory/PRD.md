# PRD — Anclora TableExtract

## Original Problem Statement
Web app to extract tables from PDFs (including scanned) into validated Excel/CSV/JSON with per-cell confidence. Mandatory flow (no chat UI): drag file → system detects tables & builds preview → user reviews only doubtful cells → downloads final file.

## Architecture
- **Backend**: FastAPI (Python). Extraction layer (`extraction.py`) is separated from the schema-validation layer (`schema_validation.py`). Deterministic normalization (`normalization.py`, NO LLM). Small LLM (GPT-5.4-mini via Emergent Universal Key) used ONLY to infer column header names (`column_inference.py`), never to produce final data. Exporters (`exporters.py`).
- **Frontend**: React + Tailwind + shadcn/ui, lucide icons, framer-friendly CSS animations. Editable spreadsheet grid (`ConfidenceGrid.jsx`).
- **DB**: MongoDB (`documents`, `tables` [embedded cells], `users`, `user_sessions`).
- **Auth**: Emergent-managed Google Auth (session_token cookie + Bearer).

## User Personas
- Analyst/accountant digitizing invoices/statements from PDFs into spreadsheets.
- Ops user validating extracted tabular data before downstream use.

## Core Requirements (static)
- Drag & drop multi-PDF upload (native extraction + OCR fallback for scanned).
- Automatic column-name inference; deterministic normalization (dates→ISO, es decimals, currency/units).
- Per-cell confidence score with green/amber/red coding.
- Editable review grid; user corrects only amber/red cells; "Solo celdas dudosas" filter.
- Export xlsx/csv/json with origin-page + confidence metadata.
- Per-user history with status pendiente/validado/exportado.
- Dark-default theme (light/system), ES/EN i18n, premium navy/cyan design with glowing header toggles.

## Data Model
- Documento(id, user_id, nombre_archivo, fecha_carga, estado, num_paginas, num_tablas, process_ms)
- Tabla_extraida(id, documento_id, pagina_origen, source_pages, extraction_method, columnas, column_types, num_filas, num_columnas, cells[])
- Celda(fila, columna, valor, valor_original, score_confianza, pagina, edited)

## Implemented (2026-09-20) — MVP complete & tested (backend 100%, frontend 100%)
- Full pipeline: upload → pdfplumber/OCR extraction → LLM column names → deterministic normalization → schema validation + confidence → store.
- Multipage merge (consecutive same-column-count tables) preserving per-row origin page.
- Editable confidence grid with inline edit (Enter/Esc), edited indicator, doubtful filter.
- xlsx/csv/json export with page + score metadata; validate & status transitions.
- Google Auth, history, i18n (ES/EN), theme system (dark/light/system) with FOUC prevention.

## Backlog / Remaining
- **P2**: Batch export across multiple documents — DONE (2026-09-20).
- **P2**: Column-type override per column in the grid — DONE (2026-09-20).
- **P1**: PDF page thumbnails in upload — DONE (2026-09-20).
- **P1**: Confidence breakdown popover (page/bbox crop/scores) — DONE (2026-09-20).
- **P2**: Robustness of OCR table reconstruction for complex scanned layouts.
- **P2**: Undo/redo and keyboard Tab-to-next-cell navigation in the grid.

## Iteration 2 (2026-09-20) — 4 features added, tested (backend 29/29, frontend 100%)
- Real pdf.js page thumbnails in the upload dropzone (client-side).
- Per-cell confidence-detail popover: page, extraction/normalization confidence, reason, and a live PDF crop of the source region (original PDF stored in db.pdf_files, served via GET /api/documents/{id}/file).
- Batch export from History: combined .xlsx (multi-sheet) or ZIP of CSV/JSON (POST /api/documents/export-batch).
- Editable column type (date/number/text) that instantly renormalizes non-edited cells (PUT /api/documents/{id}/column-type). Cells now carry bbox, extraction_conf, norm_conf, reason_code.

## Notes
- OCR (Tesseract) fallback is best-effort for scanned PDFs; native (text) path fully covered.
- Test session: Authorization: Bearer test_session_fixed (user_id=test-user-fixed) in DB test_database.
