import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import StockfishFactory, get_database_session, get_stockfish_factory
from app.queues.errors import PermanentAnalysisTaskError, TransientAnalysisTaskError
from app.schemas import AnalyzeGameTaskRequest, AnalyzeGameTaskResponse
from app.security.task_auth import require_task_authentication
from app.services.analysis_queue_service import execute_game_analysis

router = APIRouter(prefix="/internal/tasks", tags=["internal-tasks"])
logger = logging.getLogger(__name__)


@router.post("/analyze-game", response_model=AnalyzeGameTaskResponse)
def analyze_game_task(
    request: AnalyzeGameTaskRequest,
    _authenticated: None = Depends(require_task_authentication),
    session: Session = Depends(get_database_session),
    stockfish_factory: StockfishFactory = Depends(get_stockfish_factory),
) -> AnalyzeGameTaskResponse:
    try:
        result = execute_game_analysis(session, request.game_id, stockfish_factory)
    except PermanentAnalysisTaskError as error:
        raise HTTPException(404, detail="Game not found") from error
    except TransientAnalysisTaskError as error:
        logger.exception("Transient analysis task failure for game %s", request.game_id)
        raise HTTPException(503, detail="Analysis temporarily unavailable") from error
    return AnalyzeGameTaskResponse(
        game_id=request.game_id, status="completed" if result is not None else "already_completed"
    )
