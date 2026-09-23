import asyncio
from types import SimpleNamespace

import pytest

import auth
import column_inference
import storage


def settings(**overrides):
    values = {
        "app_env": "development",
        "frontend_url": "http://localhost:3000",
        "google_auth_client_id": "client-id",
        "google_auth_client_secret": "client-secret",
        "google_auth_redirect_uri": "http://localhost:8000/api/auth/google/callback",
        "local_qa_login_token": "qa-secret",
        "llm_provider": "disabled",
        "llm_api_key": "",
        "llm_base_url": "",
        "llm_model": "gpt-4o-mini",
        "object_storage_backend": "database",
        "object_storage_bucket": "",
        "object_storage_access_key_id": "",
        "object_storage_secret_access_key": "",
        "object_storage_region": "",
        "object_storage_endpoint_url": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_google_start_creates_signed_state_and_minimal_scope(monkeypatch):
    monkeypatch.setattr(auth, "get_settings", lambda: settings())
    response = __import__("asyncio").run(auth.google_start("/upload"))
    assert response.status_code == 307
    assert "accounts.google.com/o/oauth2/v2/auth" in response.headers["location"]
    assert "scope=openid+email+profile" in response.headers["location"]
    assert "google_oauth_state=" in response.headers["set-cookie"]


def test_google_state_rejects_mismatch_and_open_redirect(monkeypatch):
    monkeypatch.setattr(auth, "get_settings", lambda: settings())
    state = auth._create_state("https://attacker.example")
    assert auth._validate_state(state, state) == "/upload"
    with pytest.raises(auth.HTTPException):
        auth._validate_state(state, state + "x")


def test_google_identity_validates_issuer_audience_and_email(monkeypatch):
    monkeypatch.setattr(auth, "get_settings", lambda: settings())
    monkeypatch.setattr(
        auth.id_token,
        "verify_oauth2_token",
        lambda *args: {
            "iss": "https://accounts.google.com",
            "aud": "client-id",
            "sub": "google-sub",
            "email": "qa@example.test",
            "email_verified": True,
            "nonce": "nonce",
        },
    )
    assert auth._google_identity("fake", expected_nonce="nonce")['sub'] == "google-sub"


def test_google_callback_creates_database_session_and_cookie(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"id_token": "signed-google-token"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return FakeResponse()

    class FakeDB:
        async def commit(self):
            self.committed = True

    row = SimpleNamespace(
        user_id="google_sub",
        email="qa@example.test",
        name="QA",
        picture=None,
        is_test_user=False,
        created_at=__import__("datetime").datetime.now(),
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings())
    monkeypatch.setattr(auth.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(auth, "_google_identity", lambda token, expected_nonce: {
        "sub": "google-sub",
        "email": "qa@example.test",
        "email_verified": True,
    })
    monkeypatch.setattr(auth.users, "get_by_email", lambda db, email: _completed(None))
    monkeypatch.setattr(auth.users, "upsert", lambda db, **kwargs: _completed(row))
    saved = {}

    async def save_session(db, **kwargs):
        saved.update(kwargs)

    monkeypatch.setattr(auth.sessions, "upsert", save_session)
    state = auth._create_state("/upload")
    response = __import__("asyncio").run(
        auth.google_callback(code="code", state=state, google_oauth_state=state, db=FakeDB())
    )
    assert response.status_code == 307
    assert response.headers["location"].endswith("/upload")
    assert "session_token=" in response.headers["set-cookie"]
    assert saved["user_id"] == "google_sub"


def _completed(value):
    async def result():
        return value

    return result()


def test_column_inference_disabled_is_deterministic(monkeypatch):
    monkeypatch.setattr(column_inference, "get_settings", lambda: settings())
    rows = [[{"value": "Nombre"}, {"value": "Total"}], [{"value": "Ana"}, {"value": "12"}]]
    assert asyncio.run(column_inference.infer_column_names(rows, 2)) == ["Nombre", "Total"]


def test_column_inference_provider_success_and_invalid_response_fallback(monkeypatch):
    class FakeCompletions:
        async def create(self, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='["Cliente", "Importe"]'))]
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

        async def close(self):
            return None

    monkeypatch.setattr(column_inference, "get_settings", lambda: settings(llm_provider="openai", llm_api_key="key"))
    monkeypatch.setattr("openai.AsyncOpenAI", FakeClient)
    rows = [[{"value": "Nombre"}, {"value": "Total"}]]
    assert asyncio.run(column_inference.infer_column_names(rows, 2)) == ["Cliente", "Importe"]

    class InvalidCompletions:
        async def create(self, **kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="not-json"))])

    class InvalidClient(FakeClient):
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=InvalidCompletions())

    monkeypatch.setattr("openai.AsyncOpenAI", InvalidClient)
    assert asyncio.run(column_inference.infer_column_names(rows, 2)) == ["Nombre", "Total"]


def test_database_storage_backend_never_requires_external_credentials(monkeypatch):
    monkeypatch.setattr(storage, "get_settings", lambda: settings())
    assert storage.is_configured() is False
    with pytest.raises(storage.StorageUnavailable):
        storage.get_object("missing.pdf")


def test_s3_storage_adapter_is_provider_neutral_when_mocked(monkeypatch):
    class Body:
        def read(self):
            return b"pdf-bytes"

    class FakeClient:
        def put_object(self, **kwargs):
            self.put = kwargs

        def get_object(self, **kwargs):
            return {"Body": Body(), "ContentType": "application/pdf"}

        def delete_object(self, **kwargs):
            self.deleted = kwargs

    client = FakeClient()
    monkeypatch.setattr(
        storage,
        "get_settings",
        lambda: settings(
            object_storage_backend="s3",
            object_storage_bucket="bucket",
            object_storage_access_key_id="access",
            object_storage_secret_access_key="secret",
        ),
    )
    import boto3

    monkeypatch.setattr(boto3, "client", lambda **kwargs: client)
    assert storage.put_object("a.pdf", b"pdf-bytes", "application/pdf")["size"] == 9
    assert storage.get_object("a.pdf") == (b"pdf-bytes", "application/pdf")
    storage.delete_object("a.pdf")
