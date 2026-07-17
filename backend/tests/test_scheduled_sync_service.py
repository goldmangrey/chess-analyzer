from app.models import AnalysisStatus, Color, Game, GameResult
from app.queues.base import AnalysisEnqueueResult
from app.queues.errors import QueueEnqueueError
from sqlalchemy import select
from app.repositories import app_settings_repository
from app.schemas import SyncMode
from app.services.chesscom_client import ChessComGameRecord
from app.services.sync_execution_lock import SyncExecutionLock
from app.services.sync_execution_service import execute_chesscom_sync

PGN = '''[Event "Sync"]\n[Date "2026.07.17"]\n[White "Player"]\n[Black "Opponent"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n'''


class Client:
    def get_archives(self, _username): return ["archive"]
    def get_archive_games(self, _archive):
        return [ChessComGameRecord("new-game", None, PGN, 10)]


class Queue:
    def __init__(self): self.ids=[]
    def enqueue_game_analysis(self, *, game_id, force=False):
        self.ids.append(game_id); return AnalysisEnqueueResult(game_id, "queued")


def test_scheduler_imports_once_and_queues_only_latest(db_session, test_engine):
    settings = app_settings_repository.get_or_create_settings(db_session)
    app_settings_repository.update_settings(db_session, settings, chesscom_username="Player", auto_sync_enabled=True, auto_analyze_latest=True)
    db_session.commit(); queue=Queue()
    first = execute_chesscom_sync(session=db_session, client=Client(), queue=queue, config=__import__("app.config", fromlist=["Settings"]).Settings(_env_file=None), execution_lock=SyncExecutionLock(test_engine), mode=SyncMode.INCREMENTAL, source="scheduler")
    second = execute_chesscom_sync(session=db_session, client=Client(), queue=queue, config=__import__("app.config", fromlist=["Settings"]).Settings(_env_file=None), execution_lock=SyncExecutionLock(test_engine), mode=SyncMode.INCREMENTAL, source="scheduler")
    assert first.imported == 1 and first.analysis_queued_game_id is not None
    assert second.imported == 0 and second.analysis_queued_game_id is None
    assert queue.ids == [first.latest_game_id]
    stored = app_settings_repository.get_settings(db_session)
    assert stored.last_sync_status.value == "completed" and stored.last_sync_completed_at is not None


def test_queue_failure_keeps_imported_game(db_session, test_engine):
    settings = app_settings_repository.get_or_create_settings(db_session)
    app_settings_repository.update_settings(db_session, settings, chesscom_username="Player", auto_sync_enabled=True, auto_analyze_latest=True)
    db_session.commit()
    class FailingQueue:
        def enqueue_game_analysis(self, **_kwargs): raise QueueEnqueueError("temporary")
    result = execute_chesscom_sync(session=db_session, client=Client(), queue=FailingQueue(), config=__import__("app.config", fromlist=["Settings"]).Settings(_env_file=None), execution_lock=SyncExecutionLock(test_engine), mode=SyncMode.INCREMENTAL, source="scheduler")
    assert result.imported == 1 and result.analysis_queued_game_id is None
    assert db_session.scalar(select(Game).where(Game.external_id == "new-game")) is not None
