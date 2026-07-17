from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session

from app.models import AnalysisStatus, Color, Game, GameResult, MoveAnalysis, MoveClassification
from app.schemas import GameCreate


MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class GameListMetricsRow:
    game: Game
    opponent_username: str
    average_cp_loss: float | None
    mistakes: int
    blunders: int


class GameSort(str, Enum):
    NEWEST = "newest"
    OLDEST = "oldest"
    MOST_BLUNDERS = "most_blunders"
    HIGHEST_CP_LOSS = "highest_cp_loss"


def _validate_pagination(limit: int, offset: int) -> None:
    if not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
    if offset < 0:
        raise ValueError("offset must be greater than or equal to 0")


def _coerce_sort(sort: GameSort | str) -> GameSort:
    try:
        return GameSort(sort)
    except ValueError as error:
        raise ValueError(f"unsupported game sort: {sort}") from error


def create_game(session: Session, data: GameCreate) -> Game:
    """Add a game and flush it; the caller owns commit and rollback."""
    game = Game(**data.model_dump())
    session.add(game)
    session.flush()
    return game


def get_game_by_id(session: Session, game_id: int) -> Game | None:
    return session.get(Game, game_id)


def get_game_by_external_id(session: Session, external_id: str) -> Game | None:
    return session.scalar(select(Game).where(Game.external_id == external_id))


def external_id_exists(session: Session, external_id: str) -> bool:
    statement = select(
        select(Game.id).where(Game.external_id == external_id).exists()
    )
    return bool(session.scalar(statement))


def get_latest_game_by_ids(session: Session, game_ids: tuple[int, ...]) -> Game | None:
    if not game_ids:
        return None
    return session.scalar(
        select(Game)
        .where(Game.id.in_(game_ids))
        .order_by(Game.played_at.desc().nullslast(), Game.id.desc())
        .limit(1)
    )


def set_analysis_status(
    session: Session,
    game: Game,
    status: AnalysisStatus,
) -> Game:
    """Set analysis state and its completion timestamp, without committing."""
    if not isinstance(status, AnalysisStatus):
        try:
            status = AnalysisStatus(status)
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid analysis status: {status}") from error

    game.analysis_status = status
    game.analyzed_at = (
        datetime.now(timezone.utc) if status is AnalysisStatus.COMPLETED else None
    )
    session.flush()
    return game


def list_games_by_analysis_status(
    session: Session,
    status: AnalysisStatus,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[Game]:
    return list_games(
        session,
        analysis_status=status,
        limit=limit,
        offset=offset,
        sort=GameSort.OLDEST,
    )


def list_analyzable_games(
    session: Session,
    *,
    limit: int = 100,
) -> list[Game]:
    _validate_pagination(limit, 0)
    statement = (
        select(Game)
        .where(Game.analysis_status.in_([AnalysisStatus.PENDING, AnalysisStatus.FAILED]))
        .order_by(Game.created_at.asc(), Game.id.asc())
        .limit(limit)
    )
    return list(session.scalars(statement).all())


def list_games(
    session: Session,
    *,
    result: GameResult | None = None,
    opening: str | None = None,
    analysis_status: AnalysisStatus | None = None,
    limit: int = 20,
    offset: int = 0,
    sort: GameSort | str = GameSort.NEWEST,
) -> list[Game]:
    """Filter, aggregate-sort, and paginate games entirely in SQL."""
    _validate_pagination(limit, offset)
    selected_sort = _coerce_sort(sort)
    statement: Select[tuple[Game]] = select(Game)

    if result is not None:
        statement = statement.where(Game.result == result)
    if analysis_status is not None:
        statement = statement.where(Game.analysis_status == analysis_status)
    if opening and (term := opening.strip()):
        pattern = f"%{term.lower()}%"
        statement = statement.where(
            or_(
                func.lower(Game.opening_name).like(pattern),
                func.lower(Game.opening_code).like(pattern),
            )
        )

    newest_tie_breaker = (Game.played_at.desc().nulls_last(), Game.id.desc())
    if selected_sort is GameSort.NEWEST:
        statement = statement.order_by(*newest_tie_breaker)
    elif selected_sort is GameSort.OLDEST:
        statement = statement.order_by(Game.played_at.asc().nulls_last(), Game.id.asc())
    elif selected_sort is GameSort.MOST_BLUNDERS:
        blunders = (
            select(
                MoveAnalysis.game_id.label("game_id"),
                func.sum(
                    case(
                        (
                            MoveAnalysis.classification
                            == MoveClassification.BLUNDER,
                            1,
                        ),
                        else_=0,
                    )
                ).label("blunder_count"),
            )
            .where(MoveAnalysis.is_user_move.is_(True))
            .group_by(MoveAnalysis.game_id)
            .subquery()
        )
        statement = statement.outerjoin(blunders, blunders.c.game_id == Game.id).order_by(
            blunders.c.blunder_count.desc().nulls_last(), *newest_tie_breaker
        )
    else:
        average_loss = (
            select(
                MoveAnalysis.game_id.label("game_id"),
                func.avg(MoveAnalysis.centipawn_loss).label("average_cp_loss"),
            )
            .where(MoveAnalysis.is_user_move.is_(True))
            .group_by(MoveAnalysis.game_id)
            .subquery()
        )
        statement = statement.outerjoin(
            average_loss, average_loss.c.game_id == Game.id
        ).order_by(average_loss.c.average_cp_loss.desc().nulls_last(), *newest_tie_breaker)

    return list(session.scalars(statement.offset(offset).limit(limit)).all())


def count_games(
    session: Session,
    *,
    result: GameResult | None = None,
    opening: str | None = None,
    analysis_status: AnalysisStatus | None = None,
) -> int:
    statement = select(func.count(Game.id))
    if result is not None:
        statement = statement.where(Game.result == result)
    if analysis_status is not None:
        statement = statement.where(Game.analysis_status == analysis_status)
    if opening and (term := opening.strip()):
        pattern = f"%{term.lower()}%"
        statement = statement.where(
            or_(
                func.lower(Game.opening_name).like(pattern),
                func.lower(Game.opening_code).like(pattern),
            )
        )
    return int(session.scalar(statement) or 0)


def list_games_with_personal_metrics(
    session: Session,
    *,
    result: GameResult | None = None,
    opening: str | None = None,
    analysis_status: AnalysisStatus | None = None,
    limit: int = 20,
    offset: int = 0,
    sort: GameSort | str = GameSort.NEWEST,
) -> tuple[GameListMetricsRow, ...]:
    games = list_games(
        session,
        result=result,
        opening=opening,
        analysis_status=analysis_status,
        limit=limit,
        offset=offset,
        sort=sort,
    )
    if not games:
        return ()
    game_ids = [game.id for game in games]
    metrics_statement = (
        select(
            MoveAnalysis.game_id,
            func.avg(MoveAnalysis.centipawn_loss),
            func.sum(
                case(
                    (MoveAnalysis.classification == MoveClassification.MISTAKE, 1),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (MoveAnalysis.classification == MoveClassification.BLUNDER, 1),
                    else_=0,
                )
            ),
        )
        .join(Game, Game.id == MoveAnalysis.game_id)
        .where(
            MoveAnalysis.game_id.in_(game_ids),
            MoveAnalysis.is_user_move.is_(True),
            Game.analysis_status == AnalysisStatus.COMPLETED,
        )
        .group_by(MoveAnalysis.game_id)
    )
    metrics = {
        row[0]: (float(row[1]), int(row[2]), int(row[3]))
        for row in session.execute(metrics_statement)
    }
    return tuple(
        GameListMetricsRow(
            game=game,
            opponent_username=(
                game.black_username
                if game.user_color is Color.WHITE
                else game.white_username
            ),
            average_cp_loss=metrics.get(game.id, (None, 0, 0))[0],
            mistakes=metrics.get(game.id, (None, 0, 0))[1],
            blunders=metrics.get(game.id, (None, 0, 0))[2],
        )
        for game in games
    )
