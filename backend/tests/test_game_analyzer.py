import chess
import pytest

from app.models import Color, Game, MoveClassification
from app.services.game_analyzer import GameAnalysisError, analyze_game_moves
from app.services.stockfish_service import PositionAnalysis


PGN = '''[Event "Test"]
[White "Yeskendir"]
[Black "Opponent"]
[Result "1/2-1/2"]

1. e4 (1. d4 d5) e5 2. Nf3 Nc6 1/2-1/2
'''


class SequentialStockfish:
    def __init__(self, evaluations: list[int]) -> None:
        self.evaluations = iter(evaluations)
        self.fens: list[str] = []

    def analyze_position(self, board: chess.Board) -> PositionAnalysis:
        self.fens.append(board.fen())
        move = next(iter(board.legal_moves), None)
        return PositionAnalysis(
            next(self.evaluations),
            move.uci() if move else None,
            board.san(move) if move else None,
            (board.san(move),) if move else (),
        )


def game(user_color: Color = Color.WHITE, pgn: str = PGN) -> Game:
    return Game(id=7, external_id="g", white_username="Yeskendir", black_username="Opponent", user_color=user_color, result="draw", pgn=pgn)


def test_analyzes_every_mainline_ply_for_both_players() -> None:
    stockfish = SequentialStockfish([100, 60, 60, 120, 120, -30, -30, 250])
    analyses = analyze_game_moves(game(), stockfish)  # type: ignore[arg-type]

    assert [item.ply for item in analyses] == [1, 2, 3, 4]
    assert [item.move_number for item in analyses] == [1, 1, 2, 2]
    assert [item.player_color for item in analyses] == [Color.WHITE, Color.BLACK, Color.WHITE, Color.BLACK]
    assert [item.is_user_move for item in analyses] == [True, False, True, False]
    assert [item.played_move_uci for item in analyses] == ["e2e4", "e7e5", "g1f3", "b8c6"]
    assert [item.played_move_san for item in analyses] == ["e4", "e5", "Nf3", "Nc6"]
    assert [item.evaluation_before_cp for item in analyses] == [100, 60, 120, -30]
    assert [item.evaluation_after_cp for item in analyses] == [60, 120, -30, 250]
    assert [item.centipawn_loss for item in analyses] == [40, 60, 150, 280]
    assert [item.classification for item in analyses] == [
        MoveClassification.NORMAL,
        MoveClassification.INACCURACY,
        MoveClassification.MISTAKE,
        MoveClassification.BLUNDER,
    ]
    assert analyses[0].fen_before == chess.Board().fen()
    assert analyses[0].best_move_uci is not None
    assert analyses[0].principal_variation is not None
    assert len(analyses) == 4  # variation is ignored


def test_black_user_flags_are_reversed() -> None:
    analyses = analyze_game_moves(game(Color.BLACK), SequentialStockfish([0] * 8))  # type: ignore[arg-type]
    assert [item.is_user_move for item in analyses] == [False, True, False, True]


def test_last_mating_ply_is_included() -> None:
    mating_pgn = '''[White "Yeskendir"]
[Black "Opponent"]
[Result "0-1"]

1. f3 e5 2. g4 Qh4# 0-1
'''
    analyses = analyze_game_moves(game(pgn=mating_pgn), SequentialStockfish([0] * 8))  # type: ignore[arg-type]
    assert len(analyses) == 4
    assert analyses[-1].played_move_san == "Qh4#"


def test_corrupt_pgn_does_not_return_partial_analysis() -> None:
    with pytest.raises(GameAnalysisError):
        analyze_game_moves(game(pgn="broken"), SequentialStockfish([0] * 8))  # type: ignore[arg-type]
