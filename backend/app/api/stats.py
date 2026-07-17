from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_database_session
from app.schemas import (
    OpeningsResponse,
    StatisticsDashboard,
    StatsPeriodComparison,
    StatsSummary,
    TrendsResponse,
)
from app.services.statistics_service import (
    compare_recent_periods,
    get_dashboard_statistics,
    get_summary,
    get_trends,
    get_weakest_openings,
)


router = APIRouter(prefix="/api/stats", tags=["statistics"])


@router.get("/summary", response_model=StatsSummary)
def stats_summary(session: Session = Depends(get_database_session)) -> StatsSummary:
    return get_summary(session)


@router.get("/trends", response_model=TrendsResponse)
def stats_trends(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    session: Session = Depends(get_database_session),
) -> TrendsResponse:
    return TrendsResponse(items=get_trends(session, limit))


@router.get("/openings", response_model=OpeningsResponse)
def stats_openings(
    minimum_games: Annotated[int, Query(ge=1)] = 3,
    limit: Annotated[int, Query(ge=1, le=50)] = 5,
    session: Session = Depends(get_database_session),
) -> OpeningsResponse:
    return OpeningsResponse(
        items=get_weakest_openings(session, minimum_games, limit)
    )


@router.get("/performance", response_model=StatsPeriodComparison)
def stats_performance(
    period_size: Annotated[int, Query(ge=1, le=100)] = 10,
    session: Session = Depends(get_database_session),
) -> StatsPeriodComparison:
    return compare_recent_periods(session, period_size)


@router.get("/dashboard", response_model=StatisticsDashboard)
def stats_dashboard(
    trend_limit: Annotated[int, Query(ge=1, le=100)] = 20,
    recent_games_limit: Annotated[int, Query(ge=1, le=50)] = 5,
    weakest_openings_limit: Annotated[int, Query(ge=1, le=50)] = 5,
    period_size: Annotated[int, Query(ge=1, le=100)] = 10,
    minimum_opening_games: Annotated[int, Query(ge=1)] = 3,
    session: Session = Depends(get_database_session),
) -> StatisticsDashboard:
    return get_dashboard_statistics(
        session,
        trend_limit=trend_limit,
        recent_games_limit=recent_games_limit,
        weakest_openings_limit=weakest_openings_limit,
        period_size=period_size,
        minimum_opening_games=minimum_opening_games,
    )
