from app.models import AnalysisStatus, Color, Game, MoveAnalysis, MoveClassification
from app.repositories.move_analysis_repository import list_moves_for_game
from app.services.phase_backfill_service import assign_game_phases


def test_phase_backfill_does_not_change_stockfish_metrics(db_session) -> None:
    game = Game(
        external_id="phase-backfill",
        white_username="User",
        black_username="Opponent",
        user_color=Color.WHITE,
        result="loss",
        pgn='''[White "User"]
[Black "Opponent"]
[Result "0-1"]

1. f3 e5 2. g4 Qh4# 0-1
''',
        analysis_status=AnalysisStatus.COMPLETED,
    )
    db_session.add(game)
    db_session.flush()
    for ply in range(1, 5):
        db_session.add(MoveAnalysis(
            game_id=game.id,
            ply=ply,
            move_number=(ply + 1) // 2,
            player_color=Color.WHITE if ply % 2 else Color.BLACK,
            is_user_move=bool(ply % 2),
            fen_before=f"fen-{ply}",
            played_move_uci="move",
            evaluation_before_cp=ply * 10,
            evaluation_after_cp=ply * -10,
            centipawn_loss=ply * 20,
            classification=MoveClassification.NORMAL,
        ))
    db_session.flush()
    rows = list_moves_for_game(db_session, game.id)
    metrics_before = [
        (row.evaluation_before_cp, row.evaluation_after_cp, row.centipawn_loss, row.classification)
        for row in rows
    ]

    changed = assign_game_phases(game, rows)
    db_session.flush()

    assert changed == 4
    assert {row.phase.value for row in rows if row.phase} == {"opening"}
    assert [
        (row.evaluation_before_cp, row.evaluation_after_cp, row.centipawn_loss, row.classification)
        for row in rows
    ] == metrics_before
