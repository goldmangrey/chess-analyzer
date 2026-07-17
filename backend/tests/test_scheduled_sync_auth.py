from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_settings_dependency
from app.security.scheduled_sync_auth import require_scheduled_sync_authentication


def test_scheduled_secret_and_untrusted_headers():
    app = FastAPI()
    app.dependency_overrides[get_settings_dependency] = lambda: Settings(
        _env_file=None, SCHEDULED_SYNC_SHARED_SECRET="correct"
    )
    @app.post("/")
    def route(_=Depends(require_scheduled_sync_authentication)): return {"ok": True}
    client = TestClient(app)
    assert client.post("/", headers={"X-CloudScheduler": "true"}).status_code == 401
    assert client.post("/", headers={"X-Scheduled-Sync-Secret": "wrong"}).status_code == 401
    assert client.post("/", headers={"X-Scheduled-Sync-Secret": "correct"}).status_code == 200
    assert "correct" not in client.post("/").text


def test_local_mode_allows_missing_optional_secret():
    app = FastAPI()
    app.dependency_overrides[get_settings_dependency] = lambda: Settings(_env_file=None)
    @app.post("/")
    def route(_=Depends(require_scheduled_sync_authentication)): return {"ok": True}
    assert TestClient(app).post("/").status_code == 200
