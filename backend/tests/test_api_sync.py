from collections.abc import Iterator

from app.api import sync as sync_api
from app.dependencies import get_chesscom_client, get_settings_dependency
from app.dependencies import get_analysis_queue
from app.queues.base import AnalysisEnqueueResult
from app.services.chesscom_client import ChessComGameRecord, ChessComNetworkError


def pgn(identifier: str, date: str = "2026.07.17") -> str:
    return f'''[Event "{identifier}"]
[Date "{date}"]
[White "Player"]
[Black "Opponent"]
[Result "1-0"]

1. e4 e5 1-0
'''


class FakeArchiveClient:
    def __init__(self, archives=None, games=None, error=None):
        self.archives = archives or ["archive/2026/07", "archive/2026/06", "archive/2026/05"]
        self.games = games or {}
        self.error = error
        self.requested_archives = []

    def get_archives(self, _username):
        if self.error:
            raise self.error
        return self.archives

    def get_archive_games(self, archive):
        self.requested_archives.append(archive)
        return self.games.get(archive, [])


def record(identifier: str, end_time: int) -> ChessComGameRecord:
    return ChessComGameRecord(identifier, identifier, pgn(identifier), end_time)


def configure(api_app, client):
    api_app.dependency_overrides[get_chesscom_client] = lambda: client


def test_initial_sync_bounds_history_and_does_not_analyze_all(api_app, api_client, monkeypatch) -> None:
    client = FakeArchiveClient(games={
        "archive/2026/07": [record("newest", 30), record("middle", 20)],
        "archive/2026/06": [record("old", 10)],
        "archive/2026/05": [record("too-old", 1)],
    })
    configure(api_app, client)
    queued = []
    class Queue:
        def enqueue_game_analysis(self, *, game_id, force=False):
            queued.append(game_id)
            return AnalysisEnqueueResult(game_id, "queued")
    api_app.dependency_overrides[get_analysis_queue] = lambda: Queue()
    response = api_client.post("/api/sync/chess-com", json={"username": "Player", "mode": "initial", "initial_months": 2, "auto_analyze_latest": True})
    assert response.status_code == 200
    body = response.json()
    assert body["imported"] == 3 and body["latest_game_id"] is not None
    assert body["analysis_queued_game_id"] == body["latest_game_id"]
    assert queued == [body["latest_game_id"]]
    assert client.requested_archives == client.archives[:2]
    settings = api_client.get("/api/settings").json()
    assert settings["initial_sync_completed"] is True


def test_initial_sync_respects_max_games(api_app, api_client) -> None:
    client = FakeArchiveClient(games={"archive/2026/07": [record("a", 3), record("b", 2), record("c", 1)]})
    configure(api_app, client)
    current = api_app.dependency_overrides[get_settings_dependency]()
    api_app.dependency_overrides[get_settings_dependency] = lambda: current.model_copy(update={"initial_sync_max_games": 2})
    response = api_client.post("/api/sync/chess-com", json={"username": "Player", "mode": "initial", "auto_analyze_latest": False})
    assert response.status_code == 200
    assert response.json()["examined"] == response.json()["imported"] == 2


def test_incremental_saved_username_duplicates_and_auto_analyze_off(api_app, api_client) -> None:
    client = FakeArchiveClient(games={"archive/2026/07": [record("one", 2)], "archive/2026/06": []})
    configure(api_app, client)
    api_client.patch("/api/settings", json={"chesscom_username": "Player", "auto_analyze_latest": False})
    first = api_client.post("/api/sync/chess-com", json={})
    assert first.status_code == 200 and first.json()["imported"] == 1
    assert first.json()["analysis_queued_game_id"] is None
    second = api_client.post("/api/sync/chess-com", json={})
    assert second.json()["imported"] == 0 and second.json()["duplicates"] == 1
    assert client.requested_archives == [*client.archives[:2], *client.archives[:2]]


def test_sync_requires_username_and_rejects_concurrency(api_client) -> None:
    assert api_client.post("/api/sync/chess-com", json={}).status_code == 422
    sync_api._sync_lock.acquire()
    try:
        response = api_client.post("/api/sync/chess-com", json={"username": "Player"})
        assert response.status_code == 409
        assert response.json()["error"] == "sync_already_running"
    finally:
        sync_api._sync_lock.release()


def test_failure_records_status_and_releases_lock(api_app, api_client) -> None:
    configure(api_app, FakeArchiveClient(error=ChessComNetworkError("offline")))
    failed = api_client.post("/api/sync/chess-com", json={"username": "Player"})
    assert failed.status_code == 503
    assert api_client.get("/api/settings").json()["last_sync_status"] == "failed"
    configure(api_app, FakeArchiveClient())
    assert api_client.post("/api/sync/chess-com", json={"username": "Player"}).status_code == 200
