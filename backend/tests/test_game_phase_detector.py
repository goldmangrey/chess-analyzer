import chess

from app.models import GamePhase
from app.services.game_phase_detector import ENDGAME_PHASE_MAX, GamePhaseDetector, material_phase_units


def board_after(moves: tuple[str, ...]) -> chess.Board:
    board = chess.Board()
    for san in moves:
        board.push_san(san)
    return board


def test_normal_game_progresses_opening_middlegame_endgame() -> None:
    detector = GamePhaseDetector()
    board = chess.Board()
    phases = []
    sans = (
        "e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6",
        "O-O", "Be7", "Re1", "b5", "Bb3", "d6", "c3", "O-O",
    )
    for ply, san in enumerate(sans, 1):
        phases.append(detector.detect(board, ply))
        board.push_san(san)
    phases.append(detector.detect(board, 17))
    low_material = chess.Board("8/8/3k4/8/8/4K3/6R1/8 w - - 0 1")
    phases.append(detector.detect(low_material, 40))

    assert phases[0] is GamePhase.OPENING
    assert GamePhase.MIDDLEGAME in phases
    assert phases[-1] is GamePhase.ENDGAME


def test_short_mating_game_has_no_fake_endgame() -> None:
    detector = GamePhaseDetector()
    board = chess.Board()
    phases = []
    for ply, san in enumerate(("f3", "e5", "g4", "Qh4#"), 1):
        phases.append(detector.detect(board, ply))
        board.push_san(san)
    assert phases == [GamePhase.OPENING] * 4


def test_early_queen_trade_does_not_imply_endgame() -> None:
    board = chess.Board()
    board.remove_piece_at(chess.D1)
    board.remove_piece_at(chess.D8)
    detector = GamePhaseDetector()

    assert material_phase_units(board) > ENDGAME_PHASE_MAX
    assert detector.detect(board, 9) is GamePhase.OPENING


def test_queenless_developed_position_is_middlegame() -> None:
    board = board_after((
        "e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "O-O", "Nf6",
        "d3", "O-O", "Nc3", "d6", "Be3", "Be6",
    ))
    board.remove_piece_at(chess.D1)
    board.remove_piece_at(chess.D8)

    assert material_phase_units(board) > ENDGAME_PHASE_MAX
    assert GamePhaseDetector().detect(board, 15) is GamePhase.MIDDLEGAME


def test_low_material_position_is_endgame_even_when_early() -> None:
    board = chess.Board("8/8/3k4/8/8/4K3/6R1/8 w - - 0 1")
    assert GamePhaseDetector().detect(board, 7) is GamePhase.ENDGAME


def test_phase_transitions_never_regress() -> None:
    detector = GamePhaseDetector()
    developed = board_after((
        "e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "O-O", "Nf6",
        "d3", "O-O", "Nc3", "d6", "Be3", "Be6",
    ))
    assert detector.detect(developed, 15) is GamePhase.MIDDLEGAME
    assert detector.detect(chess.Board(), 16) is GamePhase.MIDDLEGAME

    low_material = chess.Board("8/8/3k4/8/8/4K3/6R1/8 w - - 0 1")
    assert detector.detect(low_material, 17) is GamePhase.ENDGAME
    assert detector.detect(chess.Board(), 18) is GamePhase.ENDGAME
