from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import (
    AnalysisStatus,
    Color,
    Game,
    GameResult,
    MoveAnalysis,
    MoveClassification,
)
from app.repositories.statistics_repository import (
    get_opening_metrics,
    get_period_game_metrics,
    get_recent_game_rows,
    get_summary_row,
    get_trend_rows,
)


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def add_game(
    session: Session,
    identifier: str,
    *,
    status: AnalysisStatus = AnalysisStatus.COMPLETED,
    result: GameResult = GameResult.WIN,
    user_color: Color = Color.WHITE,
    played_at: datetime | None = NOW,
    opening_code: str | None = "C20",
    opening_name: str | None = "King's Pawn",
) -> Game:
    game = Game(
        external_id=identifier,
        white_username="User" if user_color is Color.WHITE else "WhiteOpponent",
        black_username="BlackOpponent" if user_color is Color.WHITE else "User",
        user_color=user_color,
        result=result,
        pgn="pgn",
        analysis_status=status,
        played_at=played_at,
        opening_code=opening_code,
        opening_name=opening_name,
    )
    session.add(game)
    session.flush()
    return game


def add_move(
    session: Session,
    game: Game,
    ply: int,
    *,
    user: bool,
    loss: int,
    classification: MoveClassification,
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


def test_repository_rows_are_sql_aggregated_and_do_not_commit(db_session: Session) -> None:
    completed = add_game(db_session, "completed", result=GameResult.LOSS)
    pending = add_game(db_session, "pending", status=AnalysisStatus.PENDING)
    add_move(db_session, completed, 1, user=True, loss=20, classification=MoveClassification.MISTAKE)
    add_move(db_session, completed, 2, user=False, loss=999, classification=MoveClassification.BLUNDER)
    add_move(db_session, pending, 1, user=True, loss=500, classification=MoveClassification.BLUNDER)

    summary = get_summary_row(db_session)
    assert summary.total_games == 2
    assert summary.analyzed_games == 1
    assert summary.user_move_count == 1
    assert summary.total_cp_loss == 20
    assert summary.mistakes_total == 1
    assert summary.blunders_total == 0

    db_session.rollback()
    assert get_summary_row(db_session).total_games == 0


def test_repository_period_trend_recent_and_opening_rows(db_session: Session) -> None:
    older = add_game(db_session, "older", played_at=NOW, result=GameResult.LOSS)
    newer = add_game(
        db_session,
        "newer",
        played_at=NOW + timedelta(days=1),
        user_color=Color.BLACK,
    )
    pending = add_game(
        db_session,
        "pending",
        played_at=NOW + timedelta(days=2),
        status=AnalysisStatus.PENDING,
    )
    for game, loss in ((older, 100), (newer, 10)):
        add_move(db_session, game, 1, user=True, loss=loss, classification=MoveClassification.NORMAL)
        add_move(db_session, game, 2, user=False, loss=900, classification=MoveClassification.BLUNDER)

    assert [row.game_id for row in get_period_game_metrics(db_session, limit=2)] == [newer.id, older.id]
    assert [row.game_id for row in get_trend_rows(db_session, limit=2)] == [newer.id, older.id]
    recent = get_recent_game_rows(db_session, limit=3)
    assert [row.game_id for row in recent] == [pending.id, newer.id, older.id]
    assert recent[0].user_move_count == 0
    assert recent[1].opponent_username == "WhiteOpponent"

    openings = get_opening_metrics(db_session, minimum_games=1, limit=5)
    assert openings[0].games_count == 2
    assert openings[0].total_cp_loss == 110
