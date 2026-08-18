from sqlalchemy import func, select

from app.models import AnalysisStatus, Color, Game, MoveAnalysis, MoveClassification
from app.services.opening_backfill_service import refresh_game_opening


def test_refresh_opening_metadata_does_not_touch_saved_analysis(db_session) -> None:
    game = Game(
        external_id="backfill",
        white_username="Yeskendir",
        black_username="Opponent",
        user_color=Color.WHITE,
        result="win",
        pgn='''[White "Yeskendir"]
[Black "Opponent"]
[Result "1-0"]
[ECO "B13"]

1. e4 c6 2. d4 d5 3. exd5 cxd5 1-0
''',
        opening_code="B13",
        opening_name=None,
        analysis_status=AnalysisStatus.COMPLETED,
    )
    db_session.add(game)
    db_session.flush()
    db_session.add(MoveAnalysis(
        game_id=game.id,
        ply=1,
        move_number=1,
        player_color=Color.WHITE,
        is_user_move=True,
        fen_before="fen",
        played_move_uci="e2e4",
        centipawn_loss=10,
        classification=MoveClassification.NORMAL,
    ))
    db_session.flush()
    move_ids_before = tuple(db_session.scalars(select(MoveAnalysis.id)))

    changed = refresh_game_opening(game)
    db_session.flush()

    assert changed
    assert game.opening_name == "Caro-Kann Defense: Exchange Variation"
    assert tuple(db_session.scalars(select(MoveAnalysis.id))) == move_ids_before
    assert db_session.scalar(select(func.count(MoveAnalysis.id))) == 1
