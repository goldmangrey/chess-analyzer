from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.dependencies import (
    get_analysis_queue, get_chesscom_client, get_database_engine,
    get_database_session, get_settings_dependency,
)
from app.exceptions import SyncAlreadyRunningError
from app.schemas import ChessComSyncRequest, ChessComSyncResponse
from app.services.chesscom_client import ChessComClient
from app.services.sync_execution_lock import SyncExecutionLock
from app.services.sync_execution_service import SyncUsernameNotConfiguredError, execute_chesscom_sync

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/chess-com", response_model=ChessComSyncResponse)
def sync_chesscom(
    request: ChessComSyncRequest,
    session: Session = Depends(get_database_session),
    client: ChessComClient = Depends(get_chesscom_client),
    config: Settings = Depends(get_settings_dependency),
    engine: Engine = Depends(get_database_engine),
    analysis_queue=Depends(get_analysis_queue),
) -> ChessComSyncResponse:
    try:
        result = execute_chesscom_sync(
            session=session, client=client, queue=analysis_queue, config=config,
            execution_lock=SyncExecutionLock(engine), mode=request.mode,
            username_override=request.username,
            auto_analyze_latest=request.auto_analyze_latest,
            initial_months=request.initial_months, source="manual",
        )
    except SyncUsernameNotConfiguredError as error:
        raise HTTPException(422, detail=str(error)) from error
    if result.status == "already_running":
        raise SyncAlreadyRunningError
    return ChessComSyncResponse(
        mode=result.mode, username=result.username or "", examined=result.examined,
        imported=result.imported, duplicates=result.duplicates, invalid=result.invalid,
        imported_game_ids=result.imported_game_ids, latest_game_id=result.latest_game_id,
        analysis_queued_game_id=result.analysis_queued_game_id,
        started_at=result.started_at, completed_at=result.completed_at,
    )
