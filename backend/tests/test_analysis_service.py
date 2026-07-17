import threading

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import AnalysisStatus, Color, Game, MoveAnalysis
from app.repositories.games_repository import create_game, get_game_by_id
from app.repositories.move_analysis_repository import create_move_analysis
from app.schemas import GameCreate, MoveAnalysisCreate
from app.services.analysis_service import (
    AnalysisServiceError,
    GameNotFoundError,
    analyze_game,
)
from app.services.game_analyzer import GameAnalysisError
from app.services.stockfish_service import StockfishStartError


PGN = '''[White "Yeskendir"]
[Black "Opponent"]
[Result "1-0"]

1. e4 e5 1-0
'''


class FakeStockfish:
    def __init__(self, start_error: Exception | None = None) -> None:
        self.start_error = start_error
        self.closed = False

    def __enter__(self):
        if self.start_error:
            raise self.start_error
        return self

    def __exit__(self, *args) -> None:
        self.closed = True


def create_test_game(session: Session, external_id: str, status=AnalysisStatus.PENDING) -> Game:
    game = create_game(session, GameCreate(
        external_id=external_id,
        white_username="Yeskendir",
        black_username="Opponent",
        user_color=Color.WHITE,
        result="win",
        pgn=PGN,
        analysis_status=status,
    ))
    session.commit()
    return game


def analysis_rows(game_id: int, count: int = 2) -> tuple[MoveAnalysisCreate, ...]:
    return tuple(
        MoveAnalysisCreate(
            game_id=game_id,
            ply=ply,
            move_number=1,
            player_color=Color.WHITE if ply == 1 else Color.BLACK,
            is_user_move=ply == 1,
            fen_before=f"fen-{ply}",
            played_move_uci="e2e4" if ply == 1 else "e7e5",
            centipawn_loss=ply,
            classification="normal",
        )
        for ply in range(1, count + 1)
    )


def test_missing_game_is_domain_error_and_session_remains_usable(db_session: Session) -> None:
    with pytest.raises(GameNotFoundError):
        analyze_game(db_session, 999, lambda: FakeStockfish())  # type: ignore[arg-type]
    assert db_session.scalar(select(func.count(Game.id))) == 0


@pytest.mark.parametrize("initial_status", list(AnalysisStatus))
def test_status_flow_success_and_reanalysis(
    db_session: Session,
    initial_status: AnalysisStatus,
) -> None:
    game = create_test_game(db_session, f"status-{initial_status.value}", initial_status)
    observed_statuses = []

    def analyzer(active_game, stockfish):
        observed_statuses.append(active_game.analysis_status)
        return analysis_rows(active_game.id)

    result = analyze_game(db_session, game.id, lambda: FakeStockfish(), analyzer=analyzer)  # type: ignore[arg-type]
    db_session.refresh(game)
    rows = db_session.scalars(select(MoveAnalysis).where(MoveAnalysis.game_id == game.id)).all()

    assert observed_statuses == [AnalysisStatus.ANALYZING]
    assert result.moves_analyzed == 2
    assert game.analysis_status is AnalysisStatus.COMPLETED
    assert game.analyzed_at is not None
    assert len(rows) == 2
    assert [row.is_user_move for row in rows] == [True, False]


def test_success_atomically_replaces_old_analysis(db_session: Session) -> None:
    game = create_test_game(db_session, "replace", AnalysisStatus.COMPLETED)
    create_move_analysis(db_session, analysis_rows(game.id, 1)[0])
    db_session.commit()

    analyze_game(
        db_session,
        game.id,
        lambda: FakeStockfish(),
        analyzer=lambda game, stockfish: analysis_rows(game.id, 2),
    )  # type: ignore[arg-type]
    assert [row.ply for row in db_session.scalars(select(MoveAnalysis)).all()] == [1, 2]


@pytest.mark.parametrize(
    "failure_factory",
    [
        lambda: FakeStockfish(StockfishStartError("cannot start")),
        lambda: FakeStockfish(),
    ],
)
def test_failure_sets_failed_preserves_old_analysis_and_session(
    db_session: Session,
    failure_factory,
) -> None:
    game = create_test_game(db_session, "failure", AnalysisStatus.COMPLETED)
    old = create_move_analysis(db_session, analysis_rows(game.id, 1)[0])
    db_session.commit()

    def failing_analyzer(game, stockfish):
        raise GameAnalysisError("bad analysis")

    analyzer = failing_analyzer if failure_factory().start_error is None else lambda game, stockfish: ()
    with pytest.raises(AnalysisServiceError):
        analyze_game(db_session, game.id, failure_factory, analyzer=analyzer)  # type: ignore[arg-type]

    db_session.refresh(game)
    assert game.analysis_status is AnalysisStatus.FAILED
    assert game.analyzed_at is None
    assert db_session.scalars(select(MoveAnalysis)).all() == [old]
    assert get_game_by_id(db_session, game.id) is game


def test_process_lock_serializes_engine_use_and_releases_afterward(test_engine) -> None:
    maker = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    setup = maker()
    first = create_test_game(setup, "thread-1")
    second = create_test_game(setup, "thread-2")
    setup.close()

    first_entered = threading.Event()
    second_entered = threading.Event()
    release_first = threading.Event()
    errors: list[Exception] = []

    def analyzer(game, stockfish):
        if game.id == first.id:
            first_entered.set()
            assert release_first.wait(2)
        else:
            second_entered.set()
        return analysis_rows(game.id)

    def worker(game_id: int) -> None:
        session = maker()
        try:
            analyze_game(session, game_id, lambda: FakeStockfish(), analyzer=analyzer)  # type: ignore[arg-type]
        except Exception as error:
            errors.append(error)
        finally:
            session.close()

    first_thread = threading.Thread(target=worker, args=(first.id,))
    second_thread = threading.Thread(target=worker, args=(second.id,))
    first_thread.start()
    assert first_entered.wait(2)
    second_thread.start()
    assert not second_entered.wait(0.1)
    release_first.set()
    first_thread.join(2)
    second_thread.join(2)

    assert second_entered.is_set()
    assert not errors
