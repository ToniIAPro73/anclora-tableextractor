"""Backend API tests for Anclora TableExtract."""
import os
import json
import subprocess
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pdf-to-excel-178.preview.emergentagent.com").rstrip("/")
TOKEN = "test_session_fixed"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
SAMPLE_PDF = "/tmp/sample_invoice.pdf"
MULTI_PDF = "/tmp/multi.pdf"


@pytest.fixture(scope="module")
def doc_id():
    with open(SAMPLE_PDF, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/api/documents/upload?lang=es",
            headers=HEADERS,
            files={"files": ("sample_invoice.pdf", f, "application/pdf")},
            timeout=120,
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "documents" in data and len(data["documents"]) >= 1
    d = data["documents"][0]
    for k in ("id", "num_paginas", "num_tablas", "estado", "process_ms"):
        assert k in d
    assert d["estado"] == "pendiente"
    assert d["error"] is None
    return d["id"]


# --- Auth ---
class TestAuth:
    def test_me_bearer(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=HEADERS, timeout=30)
        assert r.status_code == 200
        assert r.json()["user_id"] == "test-user-fixed"

    def test_me_no_token(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert r.status_code == 401

    def test_me_invalid_token(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": "Bearer bad_xyz"}, timeout=30)
        assert r.status_code == 401

    def test_docs_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/documents", timeout=30)
        assert r.status_code == 401


# --- Extraction + normalization ---
class TestExtraction:
    def test_doc_detail(self, doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{doc_id}", headers=HEADERS, timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["documento"]["id"] == doc_id
        assert len(d["tablas"]) >= 1
        t = d["tablas"][0]
        assert len(t["columnas"]) > 0
        assert len(t["column_types"]) == len(t["columnas"])
        assert len(t["cells"]) > 0
        for c in t["cells"]:
            assert "valor" in c and "valor_original" in c
            assert "score_confianza" in c and 0 <= c["score_confianza"] <= 1
            assert "pagina" in c

    def test_deterministic_normalization(self, doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{doc_id}", headers=HEADERS, timeout=30)
        t = r.json()["tablas"][0]
        cols = t["columnas"]
        types = t["column_types"]
        # find any date cell -> ISO
        date_idx = [i for i, x in enumerate(types) if x == "date"]
        num_idx = [i for i, x in enumerate(types) if x == "number"]
        for c in t["cells"]:
            if c["columna"] in date_idx and c["valor"]:
                assert len(c["valor"]) == 10 and c["valor"][4] == "-" and c["valor"][7] == "-", f"date not ISO: {c['valor']}"
            if c["columna"] in num_idx and c["valor"]:
                # should not contain comma decimal or € sign
                assert "€" not in c["valor"] and "," not in c["valor"], f"number not normalized: {c['valor']}"


# --- Cell edit ---
class TestCellEdit:
    def test_edit(self, doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{doc_id}", headers=HEADERS, timeout=30)
        t = r.json()["tablas"][0]
        table_id = t["id"]
        payload = {"table_id": table_id, "fila": 0, "columna": 1, "valor": "EDITED_ABC"}
        r2 = requests.put(f"{BASE_URL}/api/documents/{doc_id}/cell", headers=HEADERS, json=payload, timeout=30)
        assert r2.status_code == 200, r2.text
        r3 = requests.get(f"{BASE_URL}/api/documents/{doc_id}", headers=HEADERS, timeout=30)
        t3 = next(x for x in r3.json()["tablas"] if x["id"] == table_id)
        cell = next(c for c in t3["cells"] if c["fila"] == 0 and c["columna"] == 1)
        assert cell["valor"] == "EDITED_ABC"
        assert cell["score_confianza"] == 1.0
        assert cell.get("edited") is True


# --- Validate ---
class TestValidate:
    def test_validate(self, doc_id):
        r = requests.post(f"{BASE_URL}/api/documents/{doc_id}/validate", headers=HEADERS, timeout=30)
        assert r.status_code == 200
        r2 = requests.get(f"{BASE_URL}/api/documents/{doc_id}", headers=HEADERS, timeout=30)
        assert r2.json()["documento"]["estado"] == "validado"


# --- Export (run after validate; will flip status to exportado) ---
class TestExport:
    @pytest.mark.parametrize("fmt,ctype_hint", [("xlsx", "sheet"), ("csv", "csv"), ("json", "json")])
    def test_export_download(self, doc_id, fmt, ctype_hint):
        r = requests.get(f"{BASE_URL}/api/documents/{doc_id}/export?format={fmt}", headers=HEADERS, timeout=60)
        assert r.status_code == 200
        assert len(r.content) > 100, f"empty {fmt}"
        if fmt == "json":
            data = json.loads(r.content)
            payload = json.dumps(data)
            assert ("pagina" in payload or "page" in payload)
            assert ("score_confianza" in payload or "confidence" in payload or "score" in payload)
        if fmt == "csv":
            txt = r.content.decode("utf-8", errors="ignore").lower()
            assert ("pagina" in txt or "page" in txt or "confianza" in txt or "confidence" in txt)

    def test_estado_exportado(self, doc_id):
        requests.get(f"{BASE_URL}/api/documents/{doc_id}/export?format=csv", headers=HEADERS, timeout=60)
        r = requests.get(f"{BASE_URL}/api/documents/{doc_id}", headers=HEADERS, timeout=30)
        assert r.json()["documento"]["estado"] == "exportado"


# --- History + isolation + delete ---
class TestHistory:
    def test_list(self, doc_id):
        r = requests.get(f"{BASE_URL}/api/documents", headers=HEADERS, timeout=30)
        assert r.status_code == 200
        ids = [d["id"] for d in r.json()["documents"]]
        assert doc_id in ids

    def test_user_isolation(self, doc_id):
        subprocess.run([
            "mongosh", "--quiet", "--eval",
            "use('test_database'); db.users.updateOne({user_id:'other-user'},{$set:{user_id:'other-user',email:'o@x.com',name:'Other',picture:'',created_at:new Date().toISOString()}},{upsert:true}); db.user_sessions.updateOne({session_token:'other_session'},{$set:{user_id:'other-user',session_token:'other_session',expires_at:new Date(Date.now()+86400000).toISOString(),created_at:new Date().toISOString()}},{upsert:true});"
        ], check=False, capture_output=True)
        r = requests.get(f"{BASE_URL}/api/documents", headers={"Authorization": "Bearer other_session"}, timeout=30)
        assert r.status_code == 200
        assert doc_id not in [d["id"] for d in r.json()["documents"]]
        r2 = requests.get(f"{BASE_URL}/api/documents/{doc_id}", headers={"Authorization": "Bearer other_session"}, timeout=30)
        assert r2.status_code in (403, 404)

    def test_delete(self, doc_id):
        r = requests.delete(f"{BASE_URL}/api/documents/{doc_id}", headers=HEADERS, timeout=30)
        assert r.status_code in (200, 204)
        r2 = requests.get(f"{BASE_URL}/api/documents/{doc_id}", headers=HEADERS, timeout=30)
        assert r2.status_code == 404


# --- New: dedicated fixture that uploads an isolated doc for new-feature tests
@pytest.fixture(scope="module")
def fresh_doc_id():
    with open(SAMPLE_PDF, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/api/documents/upload?lang=es",
            headers=HEADERS,
            files={"files": ("sample_invoice.pdf", f, "application/pdf")},
            timeout=120,
        )
    assert r.status_code == 200, r.text
    did = r.json()["documents"][0]["id"]
    yield did
    requests.delete(f"{BASE_URL}/api/documents/{did}", headers=HEADERS, timeout=30)


# --- New: PDF file storage + serving ---
class TestPdfFile:
    def test_get_pdf_file(self, fresh_doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}/file", headers=HEADERS, timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 500
        assert r.content[:4] == b"%PDF"

    def test_pdf_file_requires_auth(self, fresh_doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}/file", timeout=30)
        assert r.status_code == 401

    def test_pdf_file_deleted_with_doc(self):
        # upload, delete, then /file should be 404
        with open(SAMPLE_PDF, "rb") as f:
            up = requests.post(
                f"{BASE_URL}/api/documents/upload?lang=es",
                headers=HEADERS,
                files={"files": ("s.pdf", f, "application/pdf")},
                timeout=120,
            )
        did = up.json()["documents"][0]["id"]
        # confirm exists
        assert requests.get(f"{BASE_URL}/api/documents/{did}/file", headers=HEADERS, timeout=30).status_code == 200
        assert requests.delete(f"{BASE_URL}/api/documents/{did}", headers=HEADERS, timeout=30).status_code in (200, 204)
        r = requests.get(f"{BASE_URL}/api/documents/{did}/file", headers=HEADERS, timeout=30)
        assert r.status_code == 404


# --- New: enriched cell metadata (bbox, extraction_conf, norm_conf, reason_code) ---
class TestCellMetadata:
    def test_cell_shape(self, fresh_doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t = r.json()["tablas"][0]
        allowed = {"", "ocr_low", "date_ambiguous", "number_ambiguous", "norm_ambiguous", "high"}
        for c in t["cells"]:
            assert "bbox" in c
            if c["bbox"] is not None:
                assert isinstance(c["bbox"], list) and len(c["bbox"]) == 4
                for v in c["bbox"]:
                    assert isinstance(v, (int, float))
            assert "extraction_conf" in c and 0 <= c["extraction_conf"] <= 1
            assert "norm_conf" in c and 0 <= c["norm_conf"] <= 1
            assert "reason_code" in c and c["reason_code"] in allowed


# --- New: column-type re-normalization ---
class TestColumnType:
    def test_invalid_type_400(self, fresh_doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t = r.json()["tablas"][0]
        payload = {"table_id": t["id"], "columna": 0, "tipo": "banana"}
        r2 = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/column-type", headers=HEADERS, json=payload, timeout=30)
        assert r2.status_code == 400

    def test_text_to_date_lowers_confidence(self, fresh_doc_id):
        # find a text column that has non-empty values (e.g. 'Producto')
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t = r.json()["tablas"][0]
        target_col = None
        for i, typ in enumerate(t["column_types"]):
            if typ == "text":
                # check has some non-empty valor
                vals = [c for c in t["cells"] if c["columna"] == i and c.get("valor_original", "").strip()]
                if vals:
                    target_col = i
                    break
        assert target_col is not None, "No text column with values found"

        payload = {"table_id": t["id"], "columna": target_col, "tipo": "date"}
        r2 = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/column-type", headers=HEADERS, json=payload, timeout=30)
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body["column_types"][target_col] == "date"

        # re-fetch and validate cells in that column now have low score + reason_code=date_ambiguous
        r3 = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t3 = next(x for x in r3.json()["tablas"] if x["id"] == t["id"])
        assert t3["column_types"][target_col] == "date"
        col_cells = [c for c in t3["cells"] if c["columna"] == target_col and c.get("valor_original", "").strip()]
        assert col_cells
        for c in col_cells:
            if c.get("edited"):
                continue
            assert c["score_confianza"] < 0.6, f"expected red, got {c['score_confianza']}"
            assert c["reason_code"] == "date_ambiguous", c["reason_code"]

    def test_edited_cells_preserved_on_type_change(self, fresh_doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t = r.json()["tablas"][0]
        # pick any column (previous test may have flipped the text column to date)
        target_col = 0
        # ensure it's set to text first so edit is meaningful
        requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/column-type", headers=HEADERS,
                     json={"table_id": t["id"], "columna": target_col, "tipo": "text"}, timeout=30)
        # edit one cell in that column
        edit_payload = {"table_id": t["id"], "fila": 0, "columna": target_col, "valor": "KEEP_ME_EDITED"}
        r_edit = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/cell", headers=HEADERS, json=edit_payload, timeout=30)
        assert r_edit.status_code == 200
        # change column type -> number
        r2 = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/column-type", headers=HEADERS,
                          json={"table_id": t["id"], "columna": target_col, "tipo": "number"}, timeout=30)
        assert r2.status_code == 200
        r3 = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t3 = next(x for x in r3.json()["tablas"] if x["id"] == t["id"])
        edited_cell = next(c for c in t3["cells"] if c["fila"] == 0 and c["columna"] == target_col)
        assert edited_cell["valor"] == "KEEP_ME_EDITED"
        assert edited_cell.get("edited") is True
        assert edited_cell["score_confianza"] == 1.0


# --- New: batch export ---
class TestBatchExport:
    @pytest.fixture(scope="class")
    def two_doc_ids(self):
        ids = []
        for name in ("batch_a.pdf", "batch_b.pdf"):
            with open(SAMPLE_PDF, "rb") as f:
                r = requests.post(
                    f"{BASE_URL}/api/documents/upload?lang=es",
                    headers=HEADERS,
                    files={"files": (name, f, "application/pdf")},
                    timeout=120,
                )
            assert r.status_code == 200
            ids.append(r.json()["documents"][0]["id"])
        yield ids
        for did in ids:
            requests.delete(f"{BASE_URL}/api/documents/{did}", headers=HEADERS, timeout=30)

    def test_empty_ids_400(self):
        r = requests.post(f"{BASE_URL}/api/documents/export-batch", headers=HEADERS,
                          json={"doc_ids": [], "format": "xlsx"}, timeout=30)
        assert r.status_code == 400

    def test_batch_xlsx(self, two_doc_ids):
        r = requests.post(f"{BASE_URL}/api/documents/export-batch", headers=HEADERS,
                          json={"doc_ids": two_doc_ids, "format": "xlsx"}, timeout=60)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "sheet" in ct or "spreadsheet" in ct
        # xlsx = zip magic
        assert r.content[:2] == b"PK"
        assert len(r.content) > 500

    def test_batch_csv_zip(self, two_doc_ids):
        r = requests.post(f"{BASE_URL}/api/documents/export-batch", headers=HEADERS,
                          json={"doc_ids": two_doc_ids, "format": "csv"}, timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/zip")
        assert r.content[:2] == b"PK"
        # verify zip has entries
        import io, zipfile
        z = zipfile.ZipFile(io.BytesIO(r.content))
        names = z.namelist()
        assert len(names) >= 2
        assert any(n.endswith(".csv") for n in names)

    def test_batch_json_zip(self, two_doc_ids):
        r = requests.post(f"{BASE_URL}/api/documents/export-batch", headers=HEADERS,
                          json={"doc_ids": two_doc_ids, "format": "json"}, timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/zip")
        import io, zipfile
        z = zipfile.ZipFile(io.BytesIO(r.content))
        assert any(n.endswith(".json") for n in z.namelist())

    def test_batch_marks_exportado(self, two_doc_ids):
        # after previous exports, both should be exportado
        for did in two_doc_ids:
            d = requests.get(f"{BASE_URL}/api/documents/{did}", headers=HEADERS, timeout=30).json()
            assert d["documento"]["estado"] == "exportado"

    def test_batch_invalid_format(self, two_doc_ids):
        r = requests.post(f"{BASE_URL}/api/documents/export-batch", headers=HEADERS,
                          json={"doc_ids": two_doc_ids, "format": "pdf"}, timeout=30)
        assert r.status_code == 400


# --- New (iteration 3): PUT /cell-state (undo/redo backend) ---
class TestCellState:
    def test_set_cell_state_roundtrip(self, fresh_doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t = r.json()["tablas"][0]
        table_id = t["id"]
        # pick fila=0, columna=1
        orig = next(c for c in t["cells"] if c["fila"] == 0 and c["columna"] == 1)
        # set an explicit cell-state (simulating redo of an edit)
        payload = {
            "table_id": table_id, "fila": 0, "columna": 1,
            "valor": "CELLSTATE_X", "score_confianza": 1.0, "edited": True,
            "norm_conf": 1.0, "reason_code": "high",
        }
        r2 = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/cell-state", headers=HEADERS, json=payload, timeout=30)
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body["ok"] is True
        assert body["cell"]["valor"] == "CELLSTATE_X"
        assert body["cell"]["edited"] is True
        assert body["cell"]["score_confianza"] == 1.0
        # confirm persistence
        r3 = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t3 = next(x for x in r3.json()["tablas"] if x["id"] == table_id)
        cell = next(c for c in t3["cells"] if c["fila"] == 0 and c["columna"] == 1)
        assert cell["valor"] == "CELLSTATE_X"
        assert cell["edited"] is True
        assert cell["score_confianza"] == 1.0
        assert cell.get("reason_code") == "high"
        # now restore original (simulating undo)
        restore = {
            "table_id": table_id, "fila": 0, "columna": 1,
            "valor": orig["valor"], "score_confianza": orig["score_confianza"],
            "edited": bool(orig.get("edited", False)),
            "norm_conf": orig.get("norm_conf", orig["score_confianza"]),
            "reason_code": orig.get("reason_code", ""),
        }
        r4 = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/cell-state", headers=HEADERS, json=restore, timeout=30)
        assert r4.status_code == 200
        r5 = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t5 = next(x for x in r5.json()["tablas"] if x["id"] == table_id)
        cell5 = next(c for c in t5["cells"] if c["fila"] == 0 and c["columna"] == 1)
        assert cell5["valor"] == orig["valor"]
        assert bool(cell5.get("edited", False)) == bool(orig.get("edited", False))

    def test_cell_state_requires_auth(self, fresh_doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        table_id = r.json()["tablas"][0]["id"]
        payload = {"table_id": table_id, "fila": 0, "columna": 0, "valor": "x",
                   "score_confianza": 1.0, "edited": True}
        r2 = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/cell-state", json=payload, timeout=30)
        assert r2.status_code == 401

    def test_cell_state_unknown_table_404(self, fresh_doc_id):
        payload = {"table_id": "does-not-exist", "fila": 0, "columna": 0, "valor": "x",
                   "score_confianza": 1.0, "edited": True}
        r = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/cell-state", headers=HEADERS, json=payload, timeout=30)
        assert r.status_code == 404

    def test_cell_state_unknown_cell_404(self, fresh_doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        table_id = r.json()["tablas"][0]["id"]
        payload = {"table_id": table_id, "fila": 999, "columna": 999, "valor": "x",
                   "score_confianza": 1.0, "edited": True}
        r2 = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/cell-state", headers=HEADERS, json=payload, timeout=30)
        assert r2.status_code == 404


# --- New (iteration 3): POST /reprocess?mode=ocr ---
class TestReprocessOcr:
    def test_reprocess_forces_ocr_method(self):
        # upload a fresh native-invoice, then reprocess w/ mode=ocr
        with open(SAMPLE_PDF, "rb") as f:
            up = requests.post(
                f"{BASE_URL}/api/documents/upload?lang=es",
                headers=HEADERS,
                files={"files": ("reproc.pdf", f, "application/pdf")},
                timeout=120,
            )
        assert up.status_code == 200
        did = up.json()["documents"][0]["id"]
        try:
            # validate to flip estado away from pendiente so we can check it resets
            requests.post(f"{BASE_URL}/api/documents/{did}/validate", headers=HEADERS, timeout=30)
            r = requests.post(f"{BASE_URL}/api/documents/{did}/reprocess?mode=ocr&lang=es",
                              headers=HEADERS, timeout=180)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["ok"] is True
            assert body["mode"] == "ocr"
            assert body["num_tablas"] >= 1
            # verify estado reset + method='ocr'
            d = requests.get(f"{BASE_URL}/api/documents/{did}", headers=HEADERS, timeout=30).json()
            assert d["documento"]["estado"] == "pendiente"
            methods = [t.get("extraction_method") for t in d["tablas"]]
            assert methods, "no tables after reprocess"
            assert all(m == "ocr" for m in methods), f"expected all 'ocr', got {methods}"
        finally:
            requests.delete(f"{BASE_URL}/api/documents/{did}", headers=HEADERS, timeout=30)

    def test_reprocess_requires_auth(self, fresh_doc_id):
        r = requests.post(f"{BASE_URL}/api/documents/{fresh_doc_id}/reprocess?mode=ocr", timeout=30)
        assert r.status_code == 401

    def test_reprocess_unknown_doc_404(self):
        r = requests.post(f"{BASE_URL}/api/documents/no-such-doc/reprocess?mode=ocr", headers=HEADERS, timeout=30)
        assert r.status_code == 404


# --- New: multi-page PDF still processes ---
class TestMultiPage:
    def test_multi_upload(self):
        with open(MULTI_PDF, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/api/documents/upload?lang=es",
                headers=HEADERS,
                files={"files": ("multi.pdf", f, "application/pdf")},
                timeout=120,
            )
        assert r.status_code == 200, r.text
        d = r.json()["documents"][0]
        assert d["num_paginas"] >= 2
        # /file should return the pdf
        rf = requests.get(f"{BASE_URL}/api/documents/{d['id']}/file", headers=HEADERS, timeout=30)
        assert rf.status_code == 200
        assert rf.content[:4] == b"%PDF"
        # cleanup
        requests.delete(f"{BASE_URL}/api/documents/{d['id']}", headers=HEADERS, timeout=30)


@pytest.fixture(scope="module")
def autofill_doc_id():
    """Isolated doc for iteration-4 autofill/rules tests (unaffected by prior column-type flips)."""
    with open(SAMPLE_PDF, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/api/documents/upload?lang=es",
            headers=HEADERS,
            files={"files": ("autofill.pdf", f, "application/pdf")},
            timeout=120,
        )
    assert r.status_code == 200, r.text
    did = r.json()["documents"][0]["id"]
    yield did
    requests.delete(f"{BASE_URL}/api/documents/{did}", headers=HEADERS, timeout=30)


# --- New (iteration 4): POST /date-autofill ---
class TestDateAutofill:
    def test_autofill_detects_and_reparses(self, autofill_doc_id):
        fresh_doc_id = autofill_doc_id
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t = r.json()["tablas"][0]
        table_id = t["id"]
        # find a date column
        date_cols = [i for i, x in enumerate(t["column_types"]) if x == "date"]
        # Sample invoice has Fecha as column 0 with dd/mm/yyyy format
        assert date_cols, f"No date column found; types={t['column_types']}"
        col = date_cols[0]
        payload = {"table_id": table_id, "columna": col}
        r2 = requests.post(f"{BASE_URL}/api/documents/{fresh_doc_id}/date-autofill",
                           headers=HEADERS, json=payload, timeout=30)
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body["ok"] is True
        assert body["fmt"], "no fmt returned"
        # Sample uses dd/mm/yyyy so we expect %d/%m/%Y or similar
        assert "%d" in body["fmt"] and "%m" in body["fmt"] and "%Y" in body["fmt"]
        assert body["column_types"][col] == "date"
        # Every non-edited, non-empty cell in column should be ISO YYYY-MM-DD w/ score high
        r3 = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t3 = next(x for x in r3.json()["tablas"] if x["id"] == table_id)
        col_cells = [c for c in t3["cells"] if c["columna"] == col and (c.get("valor_original") or "").strip()]
        assert col_cells
        for c in col_cells:
            if c.get("edited"):
                continue
            v = c.get("valor") or ""
            assert len(v) == 10 and v[4] == "-" and v[7] == "-", f"not ISO: {v}"
            assert c["norm_conf"] == 1.0
            assert c["score_confianza"] >= 0.8

    def test_autofill_preserves_edited(self, autofill_doc_id):
        fresh_doc_id = autofill_doc_id
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t = r.json()["tablas"][0]
        table_id = t["id"]
        date_cols = [i for i, x in enumerate(t["column_types"]) if x == "date"]
        assert date_cols
        col = date_cols[0]
        # edit the first cell of the column
        edit = {"table_id": table_id, "fila": 0, "columna": col, "valor": "EDITED_DATE_VAL"}
        re = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/cell", headers=HEADERS, json=edit, timeout=30)
        assert re.status_code == 200
        r2 = requests.post(f"{BASE_URL}/api/documents/{fresh_doc_id}/date-autofill",
                           headers=HEADERS, json={"table_id": table_id, "columna": col}, timeout=30)
        assert r2.status_code == 200
        r3 = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t3 = next(x for x in r3.json()["tablas"] if x["id"] == table_id)
        edited = next(c for c in t3["cells"] if c["fila"] == 0 and c["columna"] == col)
        assert edited["valor"] == "EDITED_DATE_VAL"
        assert edited.get("edited") is True

    def test_autofill_requires_auth(self, fresh_doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        table_id = r.json()["tablas"][0]["id"]
        r2 = requests.post(f"{BASE_URL}/api/documents/{fresh_doc_id}/date-autofill",
                           json={"table_id": table_id, "columna": 0}, timeout=30)
        assert r2.status_code == 401

    def test_autofill_unknown_table_404(self, fresh_doc_id):
        r = requests.post(f"{BASE_URL}/api/documents/{fresh_doc_id}/date-autofill",
                          headers=HEADERS, json={"table_id": "nope", "columna": 0}, timeout=30)
        assert r.status_code == 404


# --- New (iteration 4): PUT /column-rules ---
class TestColumnRules:
    def test_set_and_persist_rules(self, fresh_doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t = r.json()["tablas"][0]
        table_id = t["id"]
        payload = {"table_id": table_id, "columna": 2, "rules": {"required": True, "min": 2, "max": 5}}
        r2 = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/column-rules",
                          headers=HEADERS, json=payload, timeout=30)
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body["ok"] is True
        assert body["column_rules"]["2"]["required"] is True
        assert body["column_rules"]["2"]["min"] == 2
        assert body["column_rules"]["2"]["max"] == 5
        # persistence via GET document
        r3 = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        t3 = next(x for x in r3.json()["tablas"] if x["id"] == table_id)
        assert t3.get("column_rules", {}).get("2", {}).get("min") == 2
        assert t3["column_rules"]["2"]["max"] == 5
        assert t3["column_rules"]["2"]["required"] is True

    def test_empty_rule_removes(self, fresh_doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        table_id = r.json()["tablas"][0]["id"]
        # first set a rule
        requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/column-rules",
                     headers=HEADERS,
                     json={"table_id": table_id, "columna": 3, "rules": {"required": True, "min": 1, "max": 9}},
                     timeout=30)
        # now clear it
        r2 = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/column-rules",
                          headers=HEADERS,
                          json={"table_id": table_id, "columna": 3, "rules": {"required": False, "min": None, "max": None}},
                          timeout=30)
        assert r2.status_code == 200
        assert "3" not in r2.json()["column_rules"]

    def test_rules_requires_auth(self, fresh_doc_id):
        r = requests.get(f"{BASE_URL}/api/documents/{fresh_doc_id}", headers=HEADERS, timeout=30)
        table_id = r.json()["tablas"][0]["id"]
        r2 = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/column-rules",
                         json={"table_id": table_id, "columna": 0, "rules": {"required": True}}, timeout=30)
        assert r2.status_code == 401

    def test_rules_unknown_table_404(self, fresh_doc_id):
        r = requests.put(f"{BASE_URL}/api/documents/{fresh_doc_id}/column-rules",
                         headers=HEADERS,
                         json={"table_id": "nope", "columna": 0, "rules": {"required": True}}, timeout=30)
        assert r.status_code == 404

