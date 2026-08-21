from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_analysis_queue, get_database_session
from app.models import AnalysisStatus, GameResult
from app.repositories.games_repository import (
    GameSort,
    count_games,
    get_game_by_id,
    list_games_with_personal_metrics,
)
from app.repositories.move_analysis_repository import (
    list_moves_for_game,
)
from app.schemas import (
    AnalyzeGameResponse,
    AnalyzeGameRequest,
    ApiGameListItem,
    GameDetailResponse,
    GameIntelligenceResponse,
    GameMovesResponse,
    GamesListResponse,
    MoveAnalysisRead,
)
from app.services.analysis_service import GameNotFoundError
from app.services.game_intelligence_service import GameIntelligenceService
from app.queues.errors import PermanentAnalysisTaskError


router = APIRouter(prefix="/api/games", tags=["games"])


def _require_game(session: Session, game_id: int):
    game = get_game_by_id(session, game_id)
    if game is None:
        raise GameNotFoundError(f"Game {game_id} was not found")
    return game


@router.get("", response_model=GamesListResponse)
def get_games(
    session: Session = Depends(get_database_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    result: GameResult | None = None,
    opening: str | None = None,
    analysis_status: AnalysisStatus | None = None,
    sort: GameSort = GameSort.NEWEST,
) -> GamesListResponse:
    rows = list_games_with_personal_metrics(
        session,
        result=result,
        opening=opening,
        analysis_status=analysis_status,
        limit=limit,
        offset=offset,
        sort=sort,
    )
    items = tuple(
        ApiGameListItem(
            id=row.game.id,
            played_at=row.game.played_at,
            opponent_username=row.opponent_username,
            user_color=row.game.user_color,
            result=row.game.result,
            white_rating=row.game.white_rating,
            black_rating=row.game.black_rating,
            opening_code=row.game.opening_code,
            opening_name=row.game.opening_name,
            time_control=row.game.time_control,
            analysis_status=row.game.analysis_status,
            average_cp_loss=(
                round(row.average_cp_loss, 1)
                if row.average_cp_loss is not None
                else None
            ),
            mistakes=row.mistakes,
            blunders=row.blunders,
        )
        for row in rows
    )
    total = count_games(
        session,
        result=result,
        opening=opening,
        analysis_status=analysis_status,
    )
    return GamesListResponse(
        items=items,
        limit=limit,
        offset=offset,
        returned_count=len(items),
        total=total,
    )


@router.get("/{game_id}", response_model=GameDetailResponse)
def get_game_detail(
    game_id: int,
    session: Session = Depends(get_database_session),
) -> GameDetailResponse:
    game = _require_game(session, game_id)
    intelligence = GameIntelligenceService(session).build(game)
    summary = intelligence.summary
    return GameDetailResponse(
        id=game.id,
        external_id=game.external_id,
        platform=game.platform,
        played_at=game.played_at,
        white_username=game.white_username,
        black_username=game.black_username,
        white_rating=game.white_rating,
        black_rating=game.black_rating,
        user_color=game.user_color,
        result=game.result,
        opening_code=game.opening_code,
        opening_name=game.opening_name,
        time_control=game.time_control,
        pgn=game.pgn,
        analysis_status=game.analysis_status,
        average_cp_loss=summary.average_cp_loss if summary else None,
        inaccuracies=summary.inaccuracies if summary else 0,
        mistakes=summary.mistakes if summary else 0,
        blunders=summary.blunders if summary else 0,
        phases={
            phase: {
                "start_ply": row.start_ply,
                "end_ply": row.end_ply,
                "user_moves": row.user_moves,
                "average_cp_loss": round(row.average_cp_loss, 1) if row.average_cp_loss is not None else None,
                "accuracy": row.accuracy,
                "accuracy_eligible_moves": row.accuracy_eligible_moves,
                "accuracy_coverage_rate": row.accuracy_coverage_rate,
                "accuracy_quality_band": row.accuracy_quality_band,
                "inaccuracies": row.inaccuracies,
                "mistakes": row.mistakes,
                "blunders": row.blunders,
            }
            for phase, row in intelligence.phases.items()
        },
        critical_moments=tuple(
            {
                "ply": moment.ply,
                "move_number": moment.move_number,
                "move_san": moment.move_san,
                "move_uci": moment.move_uci,
                "phase": moment.phase,
                "type": moment.type,
                "severity": moment.severity,
                "centipawn_loss": moment.centipawn_loss,
                "evaluation_before": moment.evaluation_before,
                "evaluation_after": moment.evaluation_after,
                "evaluation_before_user_pov": moment.evaluation_before_user_pov,
                "evaluation_after_user_pov": moment.evaluation_after_user_pov,
                "importance_score": moment.importance_score,
            }
            for moment in intelligence.critical_moments
        ),
        errors=tuple(
            {
                "ply": error.ply,
                "move_number": error.move_number,
                "move_san": error.move_san,
                "phase": error.phase,
                "severity": error.severity,
                "primary_type": error.primary_type,
                "secondary_types": error.secondary_types,
                "confidence": error.confidence,
                "centipawn_loss": error.centipawn_loss,
                "critical_moment_type": error.critical_moment_type,
            }
            for error in intelligence.errors
        ),
    )


@router.get("/{game_id}/moves", response_model=GameMovesResponse)
def get_game_moves(
    game_id: int,
    session: Session = Depends(get_database_session),
) -> GameMovesResponse:
    game = _require_game(session, game_id)
    moves = list_moves_for_game(session, game_id)
    return GameMovesResponse(
        game_id=game.id,
        analysis_status=game.analysis_status,
        items=tuple(MoveAnalysisRead.model_validate(move) for move in moves),
    )


@router.get("/{game_id}/intelligence", response_model=GameIntelligenceResponse)
def get_game_intelligence(
    game_id: int,
    session: Session = Depends(get_database_session),
) -> GameIntelligenceResponse:
    game = _require_game(session, game_id)
    intelligence = GameIntelligenceService(session).build(game)
    return GameIntelligenceResponse.model_validate(intelligence)


@router.post(
    "/{game_id}/analyze",
    response_model=AnalyzeGameResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_game_analysis(
    game_id: int,
    request: AnalyzeGameRequest | None = None,
    analysis_queue=Depends(get_analysis_queue),
) -> AnalyzeGameResponse:
    try:
        result = analysis_queue.enqueue_game_analysis(
            game_id=game_id, force=request.force if request else False
        )
    except PermanentAnalysisTaskError as error:
        raise GameNotFoundError(str(error)) from error
    return AnalyzeGameResponse(game_id=game_id, status=result.status, task_id=result.task_id)
