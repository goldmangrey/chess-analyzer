from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AnalysisStatus, Color, Game, GameResult, MoveAnalysis, MoveClassification
from app.schemas import StatsSummary
from app.services.statistics_service import (
    compare_recent_periods,
    get_dashboard_statistics,
    get_recent_games,
    get_summary,
    get_trends,
    get_weakest_openings,
)


NOW = datetime(2026, 2, 1, tzinfo=timezone.utc)


def add_game(
    session: Session,
    identifier: str,
    *,
    day: int = 0,
    status: AnalysisStatus = AnalysisStatus.COMPLETED,
    result: GameResult = GameResult.WIN,
    color: Color = Color.WHITE,
    code: str | None = "C20",
    name: str | None = "King's Pawn",
) -> Game:
    game = Game(
        external_id=identifier,
        played_at=NOW + timedelta(days=day),
        white_username="User" if color is Color.WHITE else "White Opponent",
        black_username="Black Opponent" if color is Color.WHITE else "User",
        user_color=color,
        result=result,
        time_control="600+5",
        opening_code=code,
        opening_name=name,
        pgn="pgn",
        analysis_status=status,
    )
    session.add(game)
    session.flush()
    return game


def add_move(
    session: Session,
    game: Game,
    ply: int,
    loss: int,
    classification: MoveClassification,
    *,
    user: bool = True,
) -> None:
    session.add(MoveAnalysis(
        game_id=game.id,
        ply=ply,
        move_number=(ply + 1) // 2,
        player_color=Color.WHITE if ply % 2 else Color.BLACK,
        is_user_move=user,
        fen_before="fen",
        played_move_uci="e2e4",
        centipawn_loss=loss,
        classification=classification,
    ))
    session.flush()


def test_empty_summary_and_schema_contract(db_session: Session) -> None:
    summary = get_summary(db_session)
    assert summary.model_dump() == {
        "total_games": 0, "analyzed_games": 0, "wins": 0, "draws": 0, "losses": 0,
        "average_cp_loss": None, "mistakes_total": 0, "blunders_total": 0,
        "mistakes_per_game": None, "blunders_per_game": None,
        "blunder_free_games": 0, "blunder_free_percentage": None,
    }
    with pytest.raises(ValidationError):
        StatsSummary(**summary.model_dump(), invented=1)


def test_summary_global_weighting_status_and_opponent_isolation(db_session: Session) -> None:
    first = add_game(db_session, "first", result=GameResult.WIN)
    second = add_game(db_session, "second", result=GameResult.LOSS)
    no_user = add_game(db_session, "no-user", result=GameResult.DRAW)
    pending = add_game(db_session, "pending", status=AnalysisStatus.PENDING)
    failed = add_game(db_session, "failed", status=AnalysisStatus.FAILED)
    add_move(db_session, first, 1, 10, MoveClassification.NORMAL)
    add_move(db_session, first, 3, 30, MoveClassification.MISTAKE)
    add_move(db_session, first, 2, 9999, MoveClassification.BLUNDER, user=False)
    add_move(db_session, second, 1, 100, MoveClassification.BLUNDER)
    add_move(db_session, second, 2, 9999, MoveClassification.MISTAKE, user=False)
    add_move(db_session, no_user, 2, 9999, MoveClassification.BLUNDER, user=False)
    add_move(db_session, pending, 1, 500, MoveClassification.BLUNDER)
    add_move(db_session, failed, 1, 500, MoveClassification.BLUNDER)

    summary = get_summary(db_session)
    assert (summary.total_games, summary.analyzed_games) == (5, 3)
    assert (summary.wins, summary.draws, summary.losses) == (3, 1, 1)
    assert summary.average_cp_loss == 46.7  # (10 + 30 + 100) / 3, not average of game averages
    assert (summary.mistakes_total, summary.blunders_total) == (1, 1)
    assert (summary.mistakes_per_game, summary.blunders_per_game) == (0.5, 0.5)
    assert (summary.blunder_free_games, summary.blunder_free_percentage) == (1, 50.0)


def test_period_comparison_selection_changes_and_incomplete_data(db_session: Session) -> None:
    for day, loss in enumerate((100, 100, 10, 10)):
        game = add_game(db_session, f"period-{day}", day=day)
        add_move(db_session, game, 1, loss, MoveClassification.MISTAKE if day < 2 else MoveClassification.NORMAL)
        add_move(db_session, game, 2, 9999, MoveClassification.BLUNDER, user=False)

    comparison = compare_recent_periods(db_session, period_size=2)
    assert (comparison.recent_games_count, comparison.previous_games_count) == (2, 2)
    assert (comparison.recent_average_cp_loss, comparison.previous_average_cp_loss) == (10.0, 100.0)
    assert comparison.average_cp_loss_change == -90.0
    assert comparison.mistakes_per_game_change == -1.0
    assert comparison.blunders_per_game_change == 0.0

    partial = compare_recent_periods(db_session, period_size=3)
    assert (partial.recent_games_count, partial.previous_games_count) == (3, 1)
    empty_previous = compare_recent_periods(db_session, period_size=4)
    assert empty_previous.previous_games_count == 0
    assert empty_previous.average_cp_loss_change is None
    for invalid in (0, 101):
        with pytest.raises(ValueError):
            compare_recent_periods(db_session, invalid)


def test_weakest_openings_formula_threshold_sort_limit_and_unknown(db_session: Session) -> None:
    for index in range(3):
        weak = add_game(db_session, f"weak-{index}", day=index, result=GameResult.LOSS, code="B20", name="Sicilian")
        add_move(db_session, weak, 1, 100, MoveClassification.BLUNDER)
        add_move(db_session, weak, 2, 9999, MoveClassification.BLUNDER, user=False)
        strong = add_game(db_session, f"strong-{index}", day=index + 3, code="C20", name="King's Pawn")
        add_move(db_session, strong, 1, 10, MoveClassification.NORMAL)
    for index in range(2):
        small = add_game(db_session, f"small-{index}", code="A00", name="Small")
        add_move(db_session, small, 1, 500, MoveClassification.BLUNDER)
    unknown = add_game(db_session, "unknown", code=None, name=None)
    add_move(db_session, unknown, 1, 999, MoveClassification.BLUNDER)

    openings = get_weakest_openings(db_session, minimum_games=3, limit=1)
    assert len(openings) == 1
    weak = openings[0]
    assert (weak.opening_code, weak.games_count, weak.losses) == ("B20", 3, 3)
    assert weak.loss_rate == 1.0
    assert weak.average_cp_loss == 100.0
    assert weak.blunders_per_game == 1.0
    assert weak.weakness_score == 135.0
    for kwargs in ({"minimum_games": 0}, {"limit": 0}, {"limit": 51}):
        with pytest.raises(ValueError):
            get_weakest_openings(db_session, **kwargs)


def test_trends_latest_chronological_opponents_and_isolation(db_session: Session) -> None:
    old = add_game(db_session, "old", day=1, color=Color.WHITE)
    middle = add_game(db_session, "middle", day=2, color=Color.BLACK)
    newest = add_game(db_session, "new", day=3)
    no_user = add_game(db_session, "no-user", day=4)
    pending = add_game(db_session, "pending", day=5, status=AnalysisStatus.PENDING)
    for game, loss in ((old, 30), (middle, 20), (newest, 10)):
        add_move(db_session, game, 1, loss, MoveClassification.MISTAKE)
        add_move(db_session, game, 2, 9999, MoveClassification.BLUNDER, user=False)
    add_move(db_session, no_user, 2, 9999, MoveClassification.BLUNDER, user=False)
    add_move(db_session, pending, 1, 500, MoveClassification.BLUNDER)

    trends = get_trends(db_session, limit=2)
    assert [item.game_id for item in trends] == [middle.id, newest.id]
    assert [item.opponent for item in trends] == ["White Opponent", "Black Opponent"]
    assert [item.average_cp_loss for item in trends] == [20.0, 10.0]
    assert all(item.mistakes == 1 and item.blunders == 0 for item in trends)
    for invalid in (0, 101):
        with pytest.raises(ValueError):
            get_trends(db_session, invalid)


def test_recent_games_all_statuses_metrics_sort_limit_and_no_duplicates(db_session: Session) -> None:
    completed = add_game(db_session, "completed", day=1, color=Color.BLACK)
    failed = add_game(db_session, "failed", day=2, status=AnalysisStatus.FAILED)
    pending = add_game(db_session, "pending", day=3, status=AnalysisStatus.PENDING)
    add_move(db_session, completed, 1, 20, MoveClassification.MISTAKE)
    add_move(db_session, completed, 2, 9999, MoveClassification.BLUNDER, user=False)
    add_move(db_session, failed, 1, 500, MoveClassification.BLUNDER)

    recent = get_recent_games(db_session, limit=3)
    assert [item.game_id for item in recent] == [pending.id, failed.id, completed.id]
    assert len({item.game_id for item in recent}) == 3
    assert recent[0].average_cp_loss is None and recent[0].blunders == 0
    assert recent[1].average_cp_loss is None and recent[1].blunders == 0
    assert recent[2].opponent_username == "White Opponent"
    assert (recent[2].average_cp_loss, recent[2].mistakes, recent[2].blunders) == (20.0, 1, 0)
    for invalid in (0, 51):
        with pytest.raises(ValueError):
            get_recent_games(db_session, invalid)


def test_dashboard_contains_sections_passes_limits_and_does_not_mutate(db_session: Session) -> None:
    game = add_game(db_session, "dashboard")
    add_move(db_session, game, 1, 10, MoveClassification.NORMAL)
    db_session.commit()
    before = db_session.scalar(select(func.count(Game.id)))

    dashboard = get_dashboard_statistics(
        db_session,
        trend_limit=1,
        recent_games_limit=1,
        weakest_openings_limit=1,
        period_size=1,
    )
    assert dashboard.summary.total_games == 1
    assert len(dashboard.trends) == len(dashboard.recent_games) == 1
    assert len(dashboard.weakest_openings) == 0  # default minimum is three games
    assert db_session.scalar(select(func.count(Game.id))) == before
