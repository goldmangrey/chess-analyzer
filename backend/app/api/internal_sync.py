import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.dependencies import (
    get_analysis_queue, get_chesscom_client, get_database_engine,
    get_database_session, get_settings_dependency,
)
from app.schemas import ScheduledSyncRequest, ScheduledSyncResponse, SyncMode
from app.security.scheduled_sync_auth import require_scheduled_sync_authentication
from app.services.chesscom_client import ChessComClient
from app.services.sync_execution_lock import SyncExecutionLock
from app.services.sync_execution_service import SyncUsernameNotConfiguredError, execute_chesscom_sync

router = APIRouter(prefix="/internal/sync", tags=["internal-sync"])
logger = logging.getLogger(__name__)


@router.post("/chess-com", response_model=ScheduledSyncResponse)
def scheduled_chesscom_sync(
    _request: ScheduledSyncRequest,
    _authenticated: None = Depends(require_scheduled_sync_authentication),
    session: Session = Depends(get_database_session),
    client: ChessComClient = Depends(get_chesscom_client),
    config: Settings = Depends(get_settings_dependency),
    engine: Engine = Depends(get_database_engine),
    queue=Depends(get_analysis_queue),
) -> ScheduledSyncResponse:
    if not config.scheduled_sync_enabled:
        logger.info("Scheduled sync skipped: infrastructure disabled")
        return ScheduledSyncResponse(status="disabled")
    logger.info("Scheduled sync request accepted")
    try:
        result = execute_chesscom_sync(
            session=session, client=client, queue=queue, config=config,
            execution_lock=SyncExecutionLock(engine), mode=SyncMode.INCREMENTAL,
            source="scheduler",
        )
    except SyncUsernameNotConfiguredError as error:
        raise HTTPException(400, detail=str(error)) from error
    return ScheduledSyncResponse(
        status=result.status, username=result.username, examined=result.examined,
        imported=result.imported, duplicates=result.duplicates, invalid=result.invalid,
        latest_game_id=result.latest_game_id,
        analysis_queued_game_id=result.analysis_queued_game_id,
        started_at=result.started_at, completed_at=result.completed_at,
    )
