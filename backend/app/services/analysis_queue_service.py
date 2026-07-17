from dataclasses import dataclass
import threading

from sqlalchemy.orm import Session

from app.models import AnalysisStatus
from app.queues.errors import PermanentAnalysisTaskError, TransientAnalysisTaskError
from app.repositories.analysis_queue_repository import get_game_for_update, release_execution_lock, try_acquire_execution_lock
from app.repositories.games_repository import get_game_by_id, set_analysis_status
from app.services.analysis_service import AnalysisResult, AnalysisServiceError, analyze_game


_execution_guard = threading.Lock()
_executing_game_ids: set[int] = set()
_reservation_guard = threading.Lock()


@dataclass(frozen=True)
class AnalysisReservation:
    game_id: int
    status: str
    previous_status: AnalysisStatus | None


def reserve_analysis(session: Session, game_id: int, *, force: bool = False) -> AnalysisReservation:
    game = get_game_for_update(session, game_id)
    if game is None:
        raise PermanentAnalysisTaskError(f"Game {game_id} was not found")
    previous = game.analysis_status
    if previous is AnalysisStatus.ANALYZING:
        return AnalysisReservation(game_id, "already_analyzing", previous)
    if previous is AnalysisStatus.COMPLETED and not force:
        return AnalysisReservation(game_id, "already_completed", previous)
    set_analysis_status(session, game, AnalysisStatus.ANALYZING)
    return AnalysisReservation(game_id, "queued", previous)


def reserve_analysis_committed(session: Session, game_id: int, *, force: bool = False) -> AnalysisReservation:
    """Serialize local reservations and commit while PostgreSQL's row lock is held."""
    with _reservation_guard:
        reservation = reserve_analysis(session, game_id, force=force)
        session.commit()
        return reservation


def mark_enqueue_failed(session: Session, game_id: int, previous_status: AnalysisStatus | None) -> None:
    game = get_game_by_id(session, game_id)
    if game is not None and game.analysis_status is AnalysisStatus.ANALYZING:
        set_analysis_status(session, game, previous_status or AnalysisStatus.FAILED)


def execute_game_analysis(session: Session, game_id: int, stockfish_factory, *, analyzer=analyze_game) -> AnalysisResult | None:
    game = get_game_by_id(session, game_id)
    if game is None:
        raise PermanentAnalysisTaskError(f"Game {game_id} was not found")
    if game.analysis_status is AnalysisStatus.COMPLETED:
        return None
    with _execution_guard:
        if game_id in _executing_game_ids:
            raise TransientAnalysisTaskError(f"Game {game_id} is already executing")
        _executing_game_ids.add(game_id)
    acquired = False
    try:
        acquired = try_acquire_execution_lock(session, game_id)
        if not acquired:
            raise TransientAnalysisTaskError(f"Game {game_id} execution lock is busy")
        try:
            return analyzer(session, game_id, stockfish_factory)
        except AnalysisServiceError as error:
            raise TransientAnalysisTaskError(f"Analysis failed for game {game_id}") from error
    finally:
        if acquired:
            release_execution_lock(session, game_id)
        with _execution_guard:
            _executing_game_ids.discard(game_id)
