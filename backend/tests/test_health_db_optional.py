"""/api/health: DB check is opt-in (?deep=1) so Neon can scale to zero. No real DB is used."""
import server
from fastapi.testclient import TestClient


async def _fail_if_called():
    raise AssertionError("database must not be queried in light mode")


def _client():
    # Plain TestClient (no context manager) does not run the startup DB check.
    return TestClient(server.app)


def test_light_mode_does_not_touch_database(monkeypatch):
    monkeypatch.setattr(server, "check_database", _fail_if_called)
    r = _client().get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "skipped"}


def test_deep_mode_checks_database(monkeypatch):
    calls = []

    async def ok():
        calls.append(1)

    monkeypatch.setattr(server, "check_database", ok)
    r = _client().get("/api/health?deep=1")
    assert r.status_code == 200 and r.json()["database"] == "ok"
    assert calls == [1]


def test_deep_mode_returns_503_when_database_fails(monkeypatch):
    async def boom():
        raise RuntimeError("down")

    monkeypatch.setattr(server, "check_database", boom)
    assert _client().get("/api/health?deep=1").status_code == 503
    assert _client().get("/api/health").status_code == 200
