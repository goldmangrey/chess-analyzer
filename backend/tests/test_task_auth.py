from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_settings_dependency
from app.security.task_auth import require_task_authentication


def test_task_secret_required_and_headers_not_identity():
    app=FastAPI(); app.dependency_overrides[get_settings_dependency]=lambda: Settings(_env_file=None, ANALYSIS_WORKER_SHARED_SECRET="secret")
    @app.get("/")
    def protected(_=Depends(require_task_authentication)): return {"ok": True}
    client=TestClient(app)
    assert client.get("/", headers={"X-CloudTasks-TaskName":"fake"}).status_code == 401
    assert client.get("/", headers={"X-Analysis-Worker-Secret":"wrong"}).status_code == 401
    assert client.get("/", headers={"X-Analysis-Worker-Secret":"secret"}).status_code == 200
