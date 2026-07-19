import logging
from collections.abc import Callable

from fastapi import BackgroundTasks

from app.database import get_session_factory
from app.queues.base import AnalysisEnqueueResult
from app.queues.errors import QueueEnqueueError
from app.services.analysis_queue_service import execute_game_analysis, mark_enqueue_failed, reserve_analysis_committed

logger = logging.getLogger(__name__)


def run_local_analysis(game_id: int, stockfish_factory, *, session_factory=None) -> None:
    active_session_factory = session_factory or get_session_factory()
    session = active_session_factory()
    try:
        logger.info("Local analysis task started for game %s", game_id)
        execute_game_analysis(session, game_id, stockfish_factory)
        logger.info("Local analysis task completed for game %s", game_id)
    except Exception:
        session.rollback()
        logger.exception("Local analysis task failed for game %s", game_id)
    finally:
        session.close()


class LocalAnalysisQueue:
    def __init__(self, background_tasks: BackgroundTasks, stockfish_factory, *, session_factory=None):
        self.background_tasks = background_tasks
        self.stockfish_factory = stockfish_factory
        self.session_factory = session_factory or get_session_factory()

    def enqueue_game_analysis(self, *, game_id: int, force: bool = False) -> AnalysisEnqueueResult:
        session = self.session_factory()
        previous = None
        try:
            reservation = reserve_analysis_committed(session, game_id, force=force)
            previous = reservation.previous_status
            if reservation.status != "queued":
                return AnalysisEnqueueResult(game_id, reservation.status)
        finally:
            session.close()
        try:
            self.background_tasks.add_task(
                run_local_analysis, game_id, self.stockfish_factory, session_factory=self.session_factory
            )
        except Exception as error:
            recovery = self.session_factory()
            try:
                mark_enqueue_failed(recovery, game_id, previous)
                recovery.commit()
            finally:
                recovery.close()
            raise QueueEnqueueError(f"Could not enqueue game {game_id}") from error
        return AnalysisEnqueueResult(game_id, "queued", f"local-game-{game_id}")
