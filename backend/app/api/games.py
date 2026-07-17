from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.background_tasks import analyze_game_background, release_analysis, reserve_analysis
from app.dependencies import StockfishFactory, get_database_session, get_stockfish_factory
from app.models import AnalysisStatus, GameResult
from app.repositories.games_repository import (
    GameSort,
    count_games,
    get_game_by_id,
    list_games_with_personal_metrics,
)
from app.repositories.move_analysis_repository import (
    get_classification_counts,
    get_personal_aggregates,
    list_moves_for_game,
)
from app.schemas import (
    AnalyzeGameResponse,
    ApiGameListItem,
    GameDetailResponse,
    GameMovesResponse,
    GamesListResponse,
    MoveAnalysisRead,
)
from app.services.analysis_service import GameNotFoundError


router = APIRouter(prefix="/api/games", tags=["games"])


def _run_reserved_analysis(game_id: int, stockfish_factory: StockfishFactory) -> None:
    try:
        analyze_game_background(game_id, stockfish_factory)
    finally:
        release_analysis(game_id)


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
    is_completed = game.analysis_status is AnalysisStatus.COMPLETED
    aggregates = get_personal_aggregates(session, game_id) if is_completed else None
    counts = (
        get_classification_counts(session, game_id)
        if is_completed
        else {"inaccuracy": 0, "mistake": 0, "blunder": 0}
    )
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
        average_cp_loss=(
            round(aggregates.average_cp_loss, 1)
            if aggregates is not None and aggregates.average_cp_loss is not None
            else None
        ),
        inaccuracies=counts["inaccuracy"],
        mistakes=counts["mistake"],
        blunders=counts["blunder"],
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


@router.post(
    "/{game_id}/analyze",
    response_model=AnalyzeGameResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def queue_game_analysis(
    game_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_database_session),
    stockfish_factory: StockfishFactory = Depends(get_stockfish_factory),
) -> AnalyzeGameResponse:
    game = _require_game(session, game_id)
    if game.analysis_status is AnalysisStatus.ANALYZING or not reserve_analysis(game_id):
        return AnalyzeGameResponse(game_id=game_id, status="already_analyzing")
    background_tasks.add_task(_run_reserved_analysis, game_id, stockfish_factory)
    return AnalyzeGameResponse(game_id=game_id, status="queued")
