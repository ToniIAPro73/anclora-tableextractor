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
