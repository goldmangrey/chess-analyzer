from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    AnalysisStatus,
    Color,
    Game,
    GameResult,
    MoveAnalysis,
    MoveClassification,
)


@dataclass(frozen=True)
class SummaryRow:
    total_games: int
    analyzed_games: int
    wins: int
    draws: int
    losses: int
    games_with_user_moves: int
    user_move_count: int
    total_cp_loss: int
    mistakes_total: int
    blunders_total: int
    blunder_free_games: int


@dataclass(frozen=True)
class GameMetricsRow:
    game_id: int
    played_at: datetime | None
    user_move_count: int
    total_cp_loss: int
    mistakes: int
    blunders: int


@dataclass(frozen=True)
class OpeningMetricsRow:
    opening_code: str | None
    opening_name: str | None
    games_count: int
    wins: int
    draws: int
    losses: int
    user_move_count: int
    total_cp_loss: int
    mistakes: int
    blunders: int


@dataclass(frozen=True)
class TrendMetricsRow:
    game_id: int
    played_at: datetime | None
    opponent: str
    result: GameResult
    user_color: Color
    opening_code: str | None
    opening_name: str | None
    user_move_count: int
    total_cp_loss: int
    mistakes: int
    blunders: int


@dataclass(frozen=True)
class RecentGameMetricsRow:
    game_id: int
    played_at: datetime | None
    opponent_username: str
    user_color: Color
    result: GameResult
    opening_code: str | None
    opening_name: str | None
    time_control: str | None
    analysis_status: AnalysisStatus
    user_move_count: int
    total_cp_loss: int
    mistakes: int
    blunders: int


def _personal_metrics_subquery():
    return (
        select(
            MoveAnalysis.game_id.label("game_id"),
            func.count(MoveAnalysis.id).label("move_count"),
            func.sum(MoveAnalysis.centipawn_loss).label("total_cp_loss"),
            func.sum(
                case(
                    (MoveAnalysis.classification == MoveClassification.MISTAKE, 1),
                    else_=0,
                )
            ).label("mistakes"),
            func.sum(
                case(
                    (MoveAnalysis.classification == MoveClassification.BLUNDER, 1),
                    else_=0,
                )
            ).label("blunders"),
        )
        .where(MoveAnalysis.is_user_move.is_(True))
        .group_by(MoveAnalysis.game_id)
        .subquery()
    )


def get_summary_row(session: Session) -> SummaryRow:
    games = session.execute(
        select(
            func.count(Game.id),
            func.sum(case((Game.analysis_status == AnalysisStatus.COMPLETED, 1), else_=0)),
            func.sum(case((Game.result == GameResult.WIN, 1), else_=0)),
            func.sum(case((Game.result == GameResult.DRAW, 1), else_=0)),
            func.sum(case((Game.result == GameResult.LOSS, 1), else_=0)),
        )
    ).one()
    metrics = _personal_metrics_subquery()
    analyzed = session.execute(
        select(
            func.count(Game.id),
            func.coalesce(func.sum(metrics.c.move_count), 0),
            func.coalesce(func.sum(metrics.c.total_cp_loss), 0),
            func.coalesce(func.sum(metrics.c.mistakes), 0),
            func.coalesce(func.sum(metrics.c.blunders), 0),
            func.coalesce(func.sum(case((metrics.c.blunders == 0, 1), else_=0)), 0),
        )
        .join(metrics, metrics.c.game_id == Game.id)
        .where(Game.analysis_status == AnalysisStatus.COMPLETED)
    ).one()
    return SummaryRow(*(int(value or 0) for value in (*games, *analyzed)))


def get_period_game_metrics(session: Session, *, limit: int) -> tuple[GameMetricsRow, ...]:
    metrics = _personal_metrics_subquery()
    statement = (
        select(
            Game.id,
            Game.played_at,
            metrics.c.move_count,
            metrics.c.total_cp_loss,
            metrics.c.mistakes,
            metrics.c.blunders,
        )
        .join(metrics, metrics.c.game_id == Game.id)
        .where(Game.analysis_status == AnalysisStatus.COMPLETED)
        .order_by(Game.played_at.desc().nulls_last(), Game.id.desc())
        .limit(limit)
    )
    return tuple(GameMetricsRow(*row) for row in session.execute(statement))


def get_opening_metrics(
    session: Session,
    *,
    minimum_games: int,
    limit: int,
) -> tuple[OpeningMetricsRow, ...]:
    metrics = _personal_metrics_subquery()
    games_count = func.count(Game.id)
    losses = func.sum(case((Game.result == GameResult.LOSS, 1), else_=0))
    mistakes = func.sum(metrics.c.mistakes)
    blunders = func.sum(metrics.c.blunders)
    total_cp_loss = func.sum(metrics.c.total_cp_loss)
    move_count = func.sum(metrics.c.move_count)
    weakness_score = (
        losses * 100.0 / games_count
        + blunders * 25.0 / games_count
        + mistakes * 10.0 / games_count
        + total_cp_loss / move_count / 10.0
    )
    statement = (
        select(
            Game.opening_code,
            Game.opening_name,
            games_count,
            func.sum(case((Game.result == GameResult.WIN, 1), else_=0)),
            func.sum(case((Game.result == GameResult.DRAW, 1), else_=0)),
            losses,
            move_count,
            total_cp_loss,
            mistakes,
            blunders,
        )
        .join(metrics, metrics.c.game_id == Game.id)
        .where(
            Game.analysis_status == AnalysisStatus.COMPLETED,
            (Game.opening_code.is_not(None) | Game.opening_name.is_not(None)),
        )
        .group_by(Game.opening_code, Game.opening_name)
        .having(games_count >= minimum_games)
        .order_by(
            weakness_score.desc(),
            games_count.desc(),
            Game.opening_name.asc().nulls_last(),
        )
        .limit(limit)
    )
    return tuple(OpeningMetricsRow(*row) for row in session.execute(statement))


def get_trend_rows(session: Session, *, limit: int) -> tuple[TrendMetricsRow, ...]:
    metrics = _personal_metrics_subquery()
    opponent = case(
        (Game.user_color == Color.WHITE, Game.black_username),
        else_=Game.white_username,
    )
    statement = (
        select(
            Game.id,
            Game.played_at,
            opponent,
            Game.result,
            Game.user_color,
            Game.opening_code,
            Game.opening_name,
            metrics.c.move_count,
            metrics.c.total_cp_loss,
            metrics.c.mistakes,
            metrics.c.blunders,
        )
        .join(metrics, metrics.c.game_id == Game.id)
        .where(Game.analysis_status == AnalysisStatus.COMPLETED)
        .order_by(Game.played_at.desc().nulls_last(), Game.id.desc())
        .limit(limit)
    )
    return tuple(TrendMetricsRow(*row) for row in session.execute(statement))


def get_recent_game_rows(
    session: Session,
    *,
    limit: int,
) -> tuple[RecentGameMetricsRow, ...]:
    metrics = _personal_metrics_subquery()
    is_completed = Game.analysis_status == AnalysisStatus.COMPLETED
    opponent = case(
        (Game.user_color == Color.WHITE, Game.black_username),
        else_=Game.white_username,
    )
    statement = (
        select(
            Game.id,
            Game.played_at,
            opponent,
            Game.user_color,
            Game.result,
            Game.opening_code,
            Game.opening_name,
            Game.time_control,
            Game.analysis_status,
            case((is_completed, func.coalesce(metrics.c.move_count, 0)), else_=0),
            case((is_completed, func.coalesce(metrics.c.total_cp_loss, 0)), else_=0),
            case((is_completed, func.coalesce(metrics.c.mistakes, 0)), else_=0),
            case((is_completed, func.coalesce(metrics.c.blunders, 0)), else_=0),
        )
        .outerjoin(metrics, metrics.c.game_id == Game.id)
        .order_by(Game.played_at.desc().nulls_last(), Game.id.desc())
        .limit(limit)
    )
    return tuple(RecentGameMetricsRow(*row) for row in session.execute(statement))
