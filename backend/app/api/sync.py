from datetime import datetime, timezone
import logging
import threading

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings
from app.dependencies import get_analysis_queue, get_chesscom_client, get_database_session, get_settings_dependency
from app.exceptions import SyncAlreadyRunningError
from app.repositories import app_settings_repository
from app.queues.errors import QueueEnqueueError
from app.schemas import ChessComSyncRequest, ChessComSyncResponse, SyncMode
from app.services.app_settings_service import normalize_username
from app.services.chesscom_client import ChessComClient
from app.services.chesscom_sync import synchronize_chesscom


router = APIRouter(prefix="/api/sync", tags=["sync"])
_sync_lock = threading.Lock()


@router.post("/chess-com", response_model=ChessComSyncResponse)
def sync_chesscom(
    request: ChessComSyncRequest,
    session: Session = Depends(get_database_session),
    client: ChessComClient = Depends(get_chesscom_client),
    config: Settings = Depends(get_settings_dependency),
    analysis_queue=Depends(get_analysis_queue),
) -> ChessComSyncResponse:
    if not _sync_lock.acquire(blocking=False):
        raise SyncAlreadyRunningError
    started_at = datetime.now(timezone.utc)
    try:
        app_settings = app_settings_repository.get_or_create_settings(session)
        try:
            username = normalize_username(request.username or app_settings.chesscom_username or "")
        except ValueError as error:
            raise HTTPException(422, detail=str(error)) from error
        if request.username:
            app_settings_repository.update_settings(session, app_settings, chesscom_username=username)
        if request.auto_analyze_latest is not None:
            app_settings_repository.update_settings(session, app_settings, auto_analyze_latest=request.auto_analyze_latest)
        app_settings_repository.mark_sync_started(session, app_settings, at=started_at)
        session.commit()
        try:
            synchronized = synchronize_chesscom(session, client, username, request.mode, config, initial_months=request.initial_months)
            app_settings = app_settings_repository.get_or_create_settings(session)
            app_settings_repository.mark_sync_completed(session, app_settings, initial=request.mode is SyncMode.INITIAL)
            session.commit()
        except Exception:
            session.rollback()
            failed_settings = app_settings_repository.get_or_create_settings(session)
            app_settings_repository.mark_sync_failed(session, failed_settings, "Chess.com synchronization failed")
            session.commit()
            raise

        queued_id = None
        latest_id = synchronized.latest_game_id
        if latest_id is not None and app_settings.auto_analyze_latest:
            try:
                enqueue_result = analysis_queue.enqueue_game_analysis(game_id=latest_id)
                if enqueue_result.status == "queued":
                    queued_id = latest_id
            except QueueEnqueueError:
                logging.getLogger(__name__).exception("Could not queue latest synced game %s", latest_id)
        completed_at = datetime.now(timezone.utc)
        result = synchronized.result
        return ChessComSyncResponse(
            mode=request.mode, username=username, examined=result.examined,
            imported=result.imported, duplicates=result.skipped_duplicates,
            invalid=result.skipped_invalid, imported_game_ids=result.imported_game_ids,
            latest_game_id=latest_id, analysis_queued_game_id=queued_id,
            started_at=started_at, completed_at=completed_at,
        )
    finally:
        _sync_lock.release()
