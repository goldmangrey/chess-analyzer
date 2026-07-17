from collections.abc import Iterator

import pytest
from sqlalchemy import func, select

from app.api import import_games as import_api
from app.dependencies import get_chesscom_client
from app.models import AnalysisStatus, Game
from app.services.chesscom_client import (
    ChessComGameRecord,
    ChessComNetworkError,
    ChessComResponseError,
    ChessComUserNotFoundError,
)


def pgn(identifier: str, username: str = "Yeskendir") -> str:
    return f'''[Event "{identifier}"]
[White "{username}"]
[Black "Opponent"]
[Result "1-0"]

1. e4 e5 1-0
'''


class FakeClient:
    def __init__(self, records=(), error: Exception | None = None) -> None:
        self.records = records
        self.error = error

    def iter_recent_games(self, username: str) -> Iterator[ChessComGameRecord]:
        if self.error:
            raise self.error
        yield from self.records


def record(identifier: str, raw_pgn: str | None = None) -> ChessComGameRecord:
    return ChessComGameRecord(identifier, identifier, raw_pgn if raw_pgn is not None else pgn(identifier), 1)


def test_import_defaults_commit_fields_pending_and_analyze_false(api_app, api_client) -> None:
    api_app.dependency_overrides[get_chesscom_client] = lambda: FakeClient([record("default")])
    response = api_client.post("/api/import/chess-com", json={"analyze": False})
    assert response.status_code == 200
    assert response.json() == {
        "requested": 10,
        "imported": 1,
        "skipped_duplicates": 0,
        "skipped_invalid": 0,
        "examined": 1,
        "imported_game_ids": [1],
        "analysis_queued": 0,
    }
    session = api_app.state.testing_session_factory()
    try:
        game = session.scalar(select(Game))
        assert game is not None and game.analysis_status is AnalysisStatus.PENDING
    finally:
        session.close()


def test_import_explicit_duplicate_invalid_and_background_queue(
    api_app,
    api_client,
    monkeypatch,
) -> None:
    queued = []
    monkeypatch.setattr(
        import_api,
        "analyze_games_background",
        lambda ids, factory: queued.append(tuple(ids)),
    )
    api_app.dependency_overrides[get_chesscom_client] = lambda: FakeClient([
        record("new", pgn("new", "Player")),
        record("invalid", "broken"),
    ])
    first = api_client.post(
        "/api/import/chess-com",
        json={"username": "Player", "limit": 2, "analyze": True},
    )
    assert first.status_code == 200
    assert first.json()["imported"] == 1
    assert first.json()["skipped_invalid"] == 1
    assert first.json()["analysis_queued"] == 1
    assert queued == [(1,)]

    api_app.dependency_overrides[get_chesscom_client] = lambda: FakeClient([
        record("new", pgn("new", "Player")),
    ])
    duplicate = api_client.post(
        "/api/import/chess-com",
        json={"username": "Player", "limit": 1, "analyze": False},
    )
    assert duplicate.json()["skipped_duplicates"] == 1
    assert duplicate.json()["imported"] == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"username": ""},
        {"username": "   "},
        {"limit": 0},
        {"limit": 51},
        {"unknown": True},
    ],
)
def test_import_request_validation(api_client, payload) -> None:
    assert api_client.post("/api/import/chess-com", json=payload).status_code == 422


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (ChessComUserNotFoundError("missing"), 404),
        (ChessComNetworkError("offline"), 503),
        (ChessComResponseError("bad upstream"), 502),
    ],
)
def test_import_upstream_error_mapping_and_rollback(api_app, api_client, error, status_code) -> None:
    api_app.dependency_overrides[get_chesscom_client] = lambda: FakeClient(error=error)
    response = api_client.post("/api/import/chess-com", json={"analyze": False})
    assert response.status_code == status_code
    session = api_app.state.testing_session_factory()
    try:
        assert session.scalar(select(func.count(Game.id))) == 0
    finally:
        session.close()
