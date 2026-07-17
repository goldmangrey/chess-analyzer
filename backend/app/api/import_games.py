import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.background_tasks import analyze_games_background
from app.config import Settings
from app.dependencies import (
    StockfishFactory,
    get_chesscom_client,
    get_database_session,
    get_settings_dependency,
    get_stockfish_factory,
)
from app.schemas import ChessComImportRequest, ChessComImportResponse
from app.services.chesscom_client import ChessComClient
from app.services.game_importer import import_recent_games


router = APIRouter(prefix="/api/import", tags=["import"])
logger = logging.getLogger(__name__)


@router.post("/chess-com", response_model=ChessComImportResponse)
def import_chesscom_games(
    request: ChessComImportRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_database_session),
    client: ChessComClient = Depends(get_chesscom_client),
    settings: Settings = Depends(get_settings_dependency),
    stockfish_factory: StockfishFactory = Depends(get_stockfish_factory),
) -> ChessComImportResponse:
    username = request.username or settings.chess_username
    limit = request.limit if request.limit is not None else settings.import_games_limit
    try:
        result = import_recent_games(session, client, username, limit)
        session.commit()
    except Exception:
        session.rollback()
        raise

    analysis_queued = len(result.imported_game_ids) if request.analyze else 0
    if analysis_queued:
        background_tasks.add_task(
            analyze_games_background,
            result.imported_game_ids,
            stockfish_factory,
        )
        logger.info("Queued analysis for game IDs %s", result.imported_game_ids)
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
