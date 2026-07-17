from app.dependencies import get_analysis_queue, get_chesscom_client, get_settings_dependency
from app.queues.base import AnalysisEnqueueResult
from app.services.chesscom_client import ChessComNetworkError


class EmptyClient:
    def get_archives(self, _username): return []


class NeverQueue:
    def enqueue_game_analysis(self, **_kwargs):
        raise AssertionError("No game should be queued")


def configure(api_app, *, enabled=True, secret="scheduled-secret"):
    current = api_app.dependency_overrides[get_settings_dependency]()
    configured = current.model_copy(update={
        "scheduled_sync_enabled": enabled,
        "scheduled_sync_shared_secret": secret,
    })
    api_app.dependency_overrides[get_settings_dependency] = lambda: configured
    api_app.dependency_overrides[get_chesscom_client] = lambda: EmptyClient()
    api_app.dependency_overrides[get_analysis_queue] = lambda: NeverQueue()


def test_scheduled_sync_no_new_games(api_app, api_client):
    configure(api_app)
    api_client.patch("/api/settings", json={"chesscom_username": "Player", "auto_sync_enabled": True})
    response = api_client.post(
        "/internal/sync/chess-com", json={"schema_version": 1},
        headers={"X-Scheduled-Sync-Secret": "scheduled-secret"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["imported"] == 0
    assert response.json()["latest_game_id"] is None


def test_scheduled_sync_disabled_setting_does_not_call_chesscom(api_app, api_client):
    configure(api_app)
    api_client.patch("/api/settings", json={"chesscom_username": "Player", "auto_sync_enabled": False})
    response = api_client.post(
        "/internal/sync/chess-com", json={"schema_version": 1},
        headers={"X-Scheduled-Sync-Secret": "scheduled-secret"},
    )
    assert response.status_code == 200 and response.json()["status"] == "disabled"


def test_scheduled_sync_configuration_disabled_and_payload_validation(api_app, api_client):
    configure(api_app, enabled=False, secret="")
    assert api_client.post("/internal/sync/chess-com", json={"schema_version": 1}).json()["status"] == "disabled"
    assert api_client.post("/internal/sync/chess-com", json={"schema_version": 2}).status_code == 422
    assert api_client.post("/internal/sync/chess-com", json={"schema_version": 1, "extra": True}).status_code == 422


def test_scheduled_sync_missing_username_is_permanent(api_app, api_client):
    configure(api_app)
    response = api_client.post(
        "/internal/sync/chess-com", json={"schema_version": 1},
        headers={"X-Scheduled-Sync-Secret": "scheduled-secret"},
    )
    assert response.status_code == 400


def test_scheduled_timeout_is_transient(api_app, api_client):
    configure(api_app)
    api_client.patch("/api/settings", json={"chesscom_username": "Player", "auto_sync_enabled": True})
    class TimeoutClient:
        def get_archives(self, _username): raise ChessComNetworkError("timeout")
    api_app.dependency_overrides[get_chesscom_client] = lambda: TimeoutClient()
    response = api_client.post(
        "/internal/sync/chess-com", json={"schema_version": 1},
        headers={"X-Scheduled-Sync-Secret": "scheduled-secret"},
    )
    assert response.status_code == 503 and "traceback" not in response.text.lower()


def test_scheduled_busy_is_success(api_app, api_client, monkeypatch):
    configure(api_app)
    from contextlib import contextmanager
    from app.api import internal_sync
    class Busy:
        def __init__(self, _engine): pass
        @contextmanager
        def acquire(self): yield False
    monkeypatch.setattr(internal_sync, "SyncExecutionLock", Busy)
    response = api_client.post(
        "/internal/sync/chess-com", json={"schema_version": 1},
        headers={"X-Scheduled-Sync-Secret": "scheduled-secret"},
    )
    assert response.status_code == 200 and response.json()["status"] == "already_running"
