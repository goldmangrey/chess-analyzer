import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings
from app.dependencies import (
    get_analysis_queue,
    get_chesscom_client,
    get_database_session,
    get_settings_dependency,
)
from app.schemas import ChessComImportRequest, ChessComImportResponse
from app.services.chesscom_client import ChessComClient
from app.services.game_importer import import_recent_games
from app.queues.errors import QueueEnqueueError


router = APIRouter(prefix="/api/import", tags=["import"])
logger = logging.getLogger(__name__)


@router.post("/chess-com", response_model=ChessComImportResponse)
def import_chesscom_games(
    request: ChessComImportRequest,
    session: Session = Depends(get_database_session),
    client: ChessComClient = Depends(get_chesscom_client),
    settings: Settings = Depends(get_settings_dependency),
    analysis_queue=Depends(get_analysis_queue),
) -> ChessComImportResponse:
    username = request.username or settings.chess_username
    limit = request.limit if request.limit is not None else settings.import_games_limit
    try:
        result = import_recent_games(session, client, username, limit)
        session.commit()
    except Exception:
        session.rollback()
        raise

    analysis_queued = 0
    if request.analyze and result.imported_game_ids:
        latest_id = result.imported_game_ids[-1]
        try:
            enqueue_result = analysis_queue.enqueue_game_analysis(game_id=latest_id)
            analysis_queued = int(enqueue_result.status == "queued")
            logger.info("Legacy import queued latest game ID %s", latest_id)
        except QueueEnqueueError:
            logger.exception("Legacy import saved, but latest game %s could not be queued", latest_id)
    logger.info(
        "Chess.com import: requested=%s imported=%s duplicates=%s invalid=%s examined=%s",
        result.requested,
        result.imported,
        result.skipped_duplicates,
        result.skipped_invalid,
        result.examined,
    )
    return ChessComImportResponse(
        **result.__dict__,
        analysis_queued=analysis_queued,
    )
