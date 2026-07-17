from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories.statistics_repository import (
    GameMetricsRow,
    get_opening_metrics,
    get_period_game_metrics,
    get_recent_game_rows,
    get_summary_row,
    get_trend_rows,
)
from app.schemas import (
    OpeningWeakness,
    RecentGameStats,
    StatisticsDashboard,
    StatsPeriodComparison,
    StatsSummary,
    TrendPoint,
)


def _average(total: int, count: int, digits: int = 1) -> float | None:
    return round(total / count, digits) if count else None


def get_summary(session: Session) -> StatsSummary:
    """Per-game denominators include completed games with user moves only."""
    row = get_summary_row(session)
    denominator = row.games_with_user_moves
    return StatsSummary(
        total_games=row.total_games,
        analyzed_games=row.analyzed_games,
        wins=row.wins,
        draws=row.draws,
        losses=row.losses,
        average_cp_loss=_average(row.total_cp_loss, row.user_move_count),
        mistakes_total=row.mistakes_total,
        blunders_total=row.blunders_total,
        mistakes_per_game=_average(row.mistakes_total, denominator, 2),
        blunders_per_game=_average(row.blunders_total, denominator, 2),
        blunder_free_games=row.blunder_free_games,
        blunder_free_percentage=_average(row.blunder_free_games * 100, denominator),
    )


@dataclass(frozen=True)
class _PeriodMetrics:
    count: int
    average_cp_loss: float | None
    mistakes_per_game: float | None
    blunders_per_game: float | None


def _period_metrics(rows: tuple[GameMetricsRow, ...]) -> _PeriodMetrics:
    count = len(rows)
    return _PeriodMetrics(
        count=count,
        average_cp_loss=_average(
            sum(row.total_cp_loss for row in rows),
            sum(row.user_move_count for row in rows),
        ),
        mistakes_per_game=_average(sum(row.mistakes for row in rows), count, 2),
        blunders_per_game=_average(sum(row.blunders for row in rows), count, 2),
    )


def _change(recent: float | None, previous: float | None, digits: int) -> float | None:
    return round(recent - previous, digits) if recent is not None and previous is not None else None


def compare_recent_periods(
    session: Session,
    period_size: int = 10,
) -> StatsPeriodComparison:
    if not 1 <= period_size <= 100:
        raise ValueError("period_size must be between 1 and 100")
    rows = get_period_game_metrics(session, limit=period_size * 2)
    recent = _period_metrics(rows[:period_size])
    previous = _period_metrics(rows[period_size:])
    return StatsPeriodComparison(
        recent_games_count=recent.count,
        previous_games_count=previous.count,
        recent_average_cp_loss=recent.average_cp_loss,
        previous_average_cp_loss=previous.average_cp_loss,
        average_cp_loss_change=_change(recent.average_cp_loss, previous.average_cp_loss, 1),
        recent_mistakes_per_game=recent.mistakes_per_game,
        previous_mistakes_per_game=previous.mistakes_per_game,
        mistakes_per_game_change=_change(recent.mistakes_per_game, previous.mistakes_per_game, 2),
        recent_blunders_per_game=recent.blunders_per_game,
        previous_blunders_per_game=previous.blunders_per_game,
        blunders_per_game_change=_change(recent.blunders_per_game, previous.blunders_per_game, 2),
    )


def get_weakest_openings(
    session: Session,
    minimum_games: int = 3,
    limit: int = 5,
) -> tuple[OpeningWeakness, ...]:
    if minimum_games < 1:
        raise ValueError("minimum_games must be at least 1")
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    rows = get_opening_metrics(session, minimum_games=minimum_games, limit=limit)
    openings = []
    for row in rows:
        loss_rate = row.losses / row.games_count
        average_cp_loss = row.total_cp_loss / row.user_move_count
        mistakes_per_game = row.mistakes / row.games_count
        blunders_per_game = row.blunders / row.games_count
        score = loss_rate * 100 + blunders_per_game * 25 + mistakes_per_game * 10 + average_cp_loss / 10
        openings.append(OpeningWeakness(
            opening_code=row.opening_code,
            opening_name=row.opening_name,
            games_count=row.games_count,
            wins=row.wins,
            draws=row.draws,
            losses=row.losses,
            loss_rate=round(loss_rate, 3),
            average_cp_loss=round(average_cp_loss, 1),
            mistakes_per_game=round(mistakes_per_game, 2),
            blunders_per_game=round(blunders_per_game, 2),
            weakness_score=round(score, 2),
        ))
    openings.sort(key=lambda item: (-item.weakness_score, -item.games_count, item.opening_name or ""))
    return tuple(openings[:limit])


def get_trends(session: Session, limit: int = 20) -> tuple[TrendPoint, ...]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    newest_first = get_trend_rows(session, limit=limit)
    return tuple(
        TrendPoint(
            game_id=row.game_id,
            played_at=row.played_at,
            opponent=row.opponent,
            result=row.result,
            user_color=row.user_color,
            opening_code=row.opening_code,
            opening_name=row.opening_name,
            average_cp_loss=round(row.total_cp_loss / row.user_move_count, 1),
            mistakes=row.mistakes,
            blunders=row.blunders,
        )
        for row in reversed(newest_first)
    )


def get_recent_games(session: Session, limit: int = 5) -> tuple[RecentGameStats, ...]:
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")
    return tuple(
        RecentGameStats(
            game_id=row.game_id,
            played_at=row.played_at,
            opponent_username=row.opponent_username,
            user_color=row.user_color,
            result=row.result,
            opening_code=row.opening_code,
            opening_name=row.opening_name,
            time_control=row.time_control,
            analysis_status=row.analysis_status,
            average_cp_loss=_average(row.total_cp_loss, row.user_move_count),
            mistakes=row.mistakes,
            blunders=row.blunders,
        )
        for row in get_recent_game_rows(session, limit=limit)
    )


def get_dashboard_statistics(
    session: Session,
    trend_limit: int = 20,
    recent_games_limit: int = 5,
    weakest_openings_limit: int = 5,
    period_size: int = 10,
) -> StatisticsDashboard:
    return StatisticsDashboard(
        summary=get_summary(session),
        comparison=compare_recent_periods(session, period_size),
        weakest_openings=get_weakest_openings(session, limit=weakest_openings_limit),
        trends=get_trends(session, trend_limit),
        recent_games=get_recent_games(session, recent_games_limit),
    )
