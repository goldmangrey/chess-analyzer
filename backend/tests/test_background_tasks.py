import logging

from app.background_tasks import analyze_game_background, analyze_games_background
from app.models import AnalysisStatus
from app.services.analysis_service import AnalysisResult


class FakeSession:
    def __init__(self) -> None:
        self.closed = False
        self.rolled_back = False

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_background_creates_and_closes_own_session() -> None:
    sessions = []
    request_session = FakeSession()

    def session_factory():
        session = FakeSession()
        sessions.append(session)
        return session

    calls = []
    analyze_game_background(
        7,
        lambda: object(),
        session_factory=session_factory,
        analyzer=lambda session, game_id, factory: (
            calls.append((session, game_id, factory))
            or AnalysisResult(game_id, AnalysisStatus.COMPLETED, 2)
        ),
    )
    assert len(sessions) == 1 and sessions[0].closed
    assert calls[0][0] is sessions[0]
    assert calls[0][0] is not request_session


def test_batch_is_sequential_and_error_does_not_stop_next(caplog) -> None:
    order = []

    def task(game_id, factory):
        order.append(game_id)
        if game_id == 1:
            raise RuntimeError("failed")

    # The production single-game helper absorbs errors; emulate that contract.
    def safe_task(game_id, factory):
        try:
            task(game_id, factory)
        except RuntimeError:
            logging.getLogger("test").exception("failure")

    with caplog.at_level(logging.ERROR):
        analyze_games_background([1, 2, 3], lambda: object(), task=safe_task)
    assert order == [1, 2, 3]
    assert "failure" in caplog.text


def test_single_background_failure_rolls_back_closes_and_logs(caplog) -> None:
    session = FakeSession()
    with caplog.at_level(logging.ERROR):
        analyze_game_background(
            1,
            lambda: object(),
            session_factory=lambda: session,
            analyzer=lambda *args: (_ for _ in ()).throw(RuntimeError("boom")),
        )
    assert session.rolled_back and session.closed
    assert "Background analysis failed for game 1" in caplog.text
