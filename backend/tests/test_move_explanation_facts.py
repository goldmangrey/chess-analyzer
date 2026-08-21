from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import chess
import chess.pgn
import pytest

from app.models import Color, ErrorConfidence, ErrorType, GamePhase, MoveClassification
from app.services.error_taxonomy_classifier import ErrorClassification, MoveTaxonomyContext
from app.services.evaluation_context import MATE_EVALUATION_THRESHOLD
from app.services.move_explanation_facts import build_move_explanation_facts


def _before(fragment: str) -> tuple[str, str]:
    game = chess.pgn.read_game(StringIO(fragment))
    assert game is not None and not game.errors
    board = game.board()
    moves = tuple(game.mainline_moves())
    for move in moves[:-1]:
        board.push(move)
    return board.fen(), moves[-1].uci()


def _row(
    fen: str,
    played: str,
    *,
    best: str | None = None,
    classification=MoveClassification.BLUNDER,
    phase=GamePhase.MIDDLEGAME,
    before=0,
    after=-200,
    loss=200,
):
    return SimpleNamespace(
        game_id=7,
        ply=5,
        fen_before=fen,
        played_move_uci=played,
        best_move_uci=best,
        classification=classification,
        phase=phase,
        evaluation_before_cp=before,
        evaluation_after_cp=after,
        centipawn_loss=loss,
    )


def _taxonomy(event, *, confidence=ErrorConfidence.HIGH, secondary=()):
    return ErrorClassification(
        ply=5,
        move_number=3,
        move_san=None,
        move_uci="",
        phase=GamePhase.MIDDLEGAME,
        severity=MoveClassification.BLUNDER,
        primary_type=event,
        secondary_types=secondary,
        confidence=confidence,
        centipawn_loss=200,
        critical_moment_type=None,
    )


def _facts(fragment: str, **kwargs):
    fen, played = _before(fragment)
    return build_move_explanation_facts(
        move_analysis=_row(fen, played, **kwargs), user_color=Color.WHITE
    )


@pytest.mark.parametrize(
    ("fragment", "piece"),
    [
        ("1. e4", "pawn"),
        ("1. Nf3", "knight"),
        ("1. e4 e5 2. Bb5", "bishop"),
        ('[SetUp "1"]\n[FEN "4k3/8/8/8/8/8/8/R3K3 w Q - 0 1"]\n\n1. Ra4', "rook"),
        ('[SetUp "1"]\n[FEN "4k3/8/8/8/8/8/8/3QK3 w - - 0 1"]\n\n1. Qd4', "queen"),
        ('[SetUp "1"]\n[FEN "4k3/8/8/8/8/8/8/4K3 w - - 0 1"]\n\n1. Kf2', "king"),
    ],
)
def test_move_fact_identifies_piece_types(fragment, piece):
    fact = _facts(fragment).played_move
    assert fact is not None and fact.piece == piece


def test_capture_and_material_facts_are_immediate_only():
    result = _facts('[SetUp "1"]\n[FEN "4k3/8/8/8/8/8/4p3/3QK3 w - - 0 1"]\n\n1. Qxe2')
    assert result.played_move.captured_piece.piece == "pawn"
    assert result.material.immediate_capture_value == 1
    assert result.material.delta_for_played_color == 1
    assert result.material.before.black - result.material.after_played_move.black == 1


@pytest.mark.parametrize(
    ("victim", "value"),
    [("pawn", 1), ("knight", 3), ("bishop", 3), ("rook", 5), ("queen", 9)],
)
def test_named_piece_values_are_descriptive(victim, value):
    piece = {"pawn": "p", "knight": "n", "bishop": "b", "rook": "r", "queen": "q"}[victim]
    result = _facts(f'[SetUp "1"]\n[FEN "4k3/8/8/8/8/8/4{piece}3/3QK3 w - - 0 1"]\n\n1. Qxe2')
    assert result.played_move.captured_piece.value == value


def test_non_capture_does_not_claim_material_loss():
    result = _facts("1. e4")
    assert result.played_move.is_capture is False
    assert result.material.immediate_capture_value == 0
    assert result.material.delta_for_played_color == 0


def test_en_passant_reports_real_captured_square():
    result = _facts("1. e4 a6 2. e5 d5 3. exd6")
    assert result.played_move.is_capture
    assert result.played_move.captured_square == "d5"
    assert result.played_move.captured_piece.piece == "pawn"


@pytest.mark.parametrize(
    ("fen", "move", "side"),
    [
        ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1", "kingside"),
        ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1c1", "queenside"),
    ],
)
def test_castling_side(fen, move, side):
    result = build_move_explanation_facts(
        move_analysis=_row(fen, move), user_color=Color.WHITE
    )
    assert result.played_move.is_castling and result.played_move.castling_side == side


@pytest.mark.parametrize(("move", "piece"), [("a7a8q", "queen"), ("a7a8n", "knight")])
def test_promotion_and_underpromotion(move, piece):
    result = build_move_explanation_facts(
        move_analysis=_row("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", move),
        user_color=Color.WHITE,
    )
    assert result.played_move.is_promotion and result.played_move.promotion_piece == piece


def test_check_and_best_san_are_calculated_from_same_fen_before():
    result = build_move_explanation_facts(
        move_analysis=_row(
            "6k1/8/8/8/8/8/8/3R2K1 w - - 0 1", "d1d2", best="d1d8"
        ),
        user_color=Color.WHITE,
    )
    assert result.played_move.san == "Rd2"
    assert result.best_move.san == "Rd8+"
    assert result.best_move.is_check


def test_malformed_played_and_best_moves_fail_independently():
    bad_played = build_move_explanation_facts(
        move_analysis=_row(chess.STARTING_FEN, "bad", best="e2e4"), user_color=Color.WHITE
    )
    assert bad_played.played_move is None and bad_played.best_move.san == "e4"
    bad_best = build_move_explanation_facts(
        move_analysis=_row(chess.STARTING_FEN, "e2e4", best="bad"), user_color=Color.WHITE
    )
    assert bad_best.played_move.san == "e4" and bad_best.best_move is None


def test_hanging_piece_details_are_attacked_undefended_and_legally_capturable():
    row = _row("k7/8/2p5/8/8/2N5/8/7K w - - 0 1", "c3b5")
    result = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE, taxonomy=_taxonomy(ErrorType.HANGING_PIECE)
    )
    assert result.hanging_piece.piece.piece == "knight"
    assert result.hanging_piece.piece.square == "b5"
    assert result.hanging_piece.is_undefended
    assert result.hanging_piece.opponent_capture_moves == ("cxb5",)
    assert result.fact_completeness == "complete"


def test_defended_attacked_piece_is_not_claimed_undefended():
    row = _row("k7/8/2p5/8/P7/2N5/8/7K w - - 0 1", "c3b5")
    result = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE, taxonomy=_taxonomy(ErrorType.HANGING_PIECE)
    )
    assert result.hanging_piece is not None
    assert result.hanging_piece.is_undefended is False
    assert any(piece.square == "a4" for piece in result.hanging_piece.defenders)


def test_hanging_piece_can_report_multiple_geometric_attackers():
    row = _row("kr6/8/2p5/8/8/2N5/8/7K w - - 0 1", "c3b5")
    result = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE,
        taxonomy=_taxonomy(ErrorType.HANGING_PIECE),
    )
    assert {piece.piece for piece in result.hanging_piece.attackers} == {"pawn", "rook"}


def test_hanging_taxonomy_without_specific_target_is_partial_not_lost_piece_claim():
    result = build_move_explanation_facts(
        move_analysis=_row(chess.STARTING_FEN, "e2e4"),
        user_color=Color.WHITE,
        taxonomy=_taxonomy(ErrorType.HANGING_PIECE),
    )
    assert result.primary_event is ErrorType.HANGING_PIECE
    assert result.hanging_piece is None
    assert result.fact_completeness == "partial"


def test_missed_capture_requires_capturing_best_move_and_exposes_target():
    row = _row("4k2r/8/8/8/8/8/8/3QK3 w - - 0 1", "d1d2", best="d1h5")
    partial = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE, taxonomy=_taxonomy(ErrorType.MISSED_CAPTURE)
    )
    assert partial.missed_capture is None and partial.fact_completeness == "partial"
    row.best_move_uci = "d1h5"  # legal but deliberately not a capture


def test_missed_capture_target_and_comparison():
    row = _row("4k2r/8/8/8/8/8/8/3QK3 w - - 0 1", "d1d2", best="d1h5")
    # Put the rook on h5 so the same legal diagonal is an immediate capture.
    row.fen_before = "4k3/8/8/7r/8/8/8/3QK3 w - - 0 1"
    result = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE, taxonomy=_taxonomy(ErrorType.MISSED_CAPTURE)
    )
    assert result.missed_capture.target.piece == "rook"
    assert result.missed_capture.target.value == 5
    assert result.comparison.best_move_wins_more_material


def test_missed_check_requires_best_move_to_really_check():
    row = _row("6k1/8/8/8/8/8/8/3R2K1 w - - 0 1", "d1d2", best="d1d8")
    complete = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE, taxonomy=_taxonomy(ErrorType.MISSED_CHECK)
    )
    assert complete.missed_check.san == "Rd8+"
    row.best_move_uci = "d1d3"
    partial = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE, taxonomy=_taxonomy(ErrorType.MISSED_CHECK)
    )
    assert partial.missed_check is None and partial.fact_completeness == "partial"


@pytest.mark.parametrize(
    ("event", "before", "after", "field"),
    [
        (ErrorType.MISSED_MATE, MATE_EVALUATION_THRESHOLD, 20, "missed_mate"),
        (ErrorType.ALLOWED_MATE, 0, -MATE_EVALUATION_THRESHOLD, "allowed_mate"),
    ],
)
def test_mate_events_reuse_persisted_transition_without_sentinel_leak(event, before, after, field):
    row = _row(chess.STARTING_FEN, "e2e4", before=before, after=after)
    result = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE, taxonomy=_taxonomy(event)
    )
    assert getattr(result, field) is True
    assert result.evaluation.before_cp != MATE_EVALUATION_THRESHOLD
    assert result.evaluation.after_cp != -MATE_EVALUATION_THRESHOLD
    assert result.evaluation.mate_distance is None


def test_fork_uses_actual_next_move_and_high_value_targets():
    row = _row("6k1/8/8/4n3/8/8/1Q1R3P/6K1 w - - 0 1", "h2h3")
    result = build_move_explanation_facts(
        move_analysis=row,
        user_color=Color.WHITE,
        taxonomy=_taxonomy(ErrorType.FORK),
        next_move_uci="e5c4",
    )
    assert result.fork.attacker.piece == "knight"
    assert {target.piece for target in result.fork.targets} == {"queen", "rook"}


def test_pin_identifies_pinned_piece_and_king():
    row = _row("4r1k1/8/8/8/8/4B3/4N3/4K3 w - - 0 1", "e3f4")
    result = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE, taxonomy=_taxonomy(ErrorType.PIN)
    )
    assert result.pin.pinned_piece.piece == "knight"
    assert result.pin.king_square == "e1"
    assert any(piece.piece == "rook" and piece.square == "e8" for piece in result.pin.attacking_sliders)


def test_king_safety_reports_only_measurable_board_changes():
    row = _row("6rk/8/8/8/8/7p/6PP/7K w - - 0 1", "g2h3")
    result = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE, taxonomy=_taxonomy(ErrorType.KING_SAFETY)
    )
    assert result.king_safety.king_square_before == "h1"
    assert result.king_safety.pawn_shield_after <= result.king_safety.pawn_shield_before


def test_king_safety_reports_castling_rights_loss_without_interpretation():
    row = _row("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1f1")
    result = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE,
        taxonomy=_taxonomy(ErrorType.KING_SAFETY),
    )
    assert result.king_safety.castling_rights_before is True
    assert result.king_safety.castling_rights_after is False


def test_development_and_phase_are_factual_and_separate_from_severity():
    fen, move = _before("1. e4 e5 2. Qh5")
    row = _row(fen, move, phase=GamePhase.OPENING, classification=MoveClassification.MISTAKE)
    result = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE, taxonomy=_taxonomy(ErrorType.DEVELOPMENT)
    )
    assert result.classification is MoveClassification.MISTAKE
    assert result.primary_event is ErrorType.DEVELOPMENT
    assert result.phase is GamePhase.OPENING
    assert result.development.queen_moved
    assert result.development.undeveloped_minor_pieces_before == 4


def test_pawn_structure_reports_doubled_isolated_and_islands_before_after():
    row = _row("6k1/8/8/8/2n5/3P4/2P5/6K1 w - - 0 1", "d3c4")
    result = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE, taxonomy=_taxonomy(ErrorType.PAWN_STRUCTURE)
    )
    assert result.pawn_structure.doubled_after > result.pawn_structure.doubled_before
    assert result.pawn_structure.pawn_islands_after >= 1


def test_bad_exchange_exposes_only_immediate_capture_material():
    row = _row("r5k1/p7/8/8/8/8/8/R5BK w - - 0 1", "a1a7")
    result = build_move_explanation_facts(
        move_analysis=row, user_color=Color.WHITE, taxonomy=_taxonomy(ErrorType.BAD_EXCHANGE)
    )
    assert result.bad_exchange.immediate_capture_value == 1
    assert not hasattr(result.bad_exchange, "forced_loss")


def test_best_equals_played_and_positive_move_facts_need_no_positive_taxonomy():
    row = _row(chess.STARTING_FEN, "e2e4", best="e2e4", classification=MoveClassification.NORMAL, loss=0)
    result = build_move_explanation_facts(move_analysis=row, user_color=Color.WHITE)
    assert result.comparison.is_engine_best
    assert result.primary_event is None
    assert result.fact_completeness == "minimal"


def test_low_confidence_taxonomy_is_not_promoted_and_secondary_does_not_replace_primary():
    low = build_move_explanation_facts(
        move_analysis=_row(chess.STARTING_FEN, "e2e4"), user_color=Color.WHITE,
        taxonomy=_taxonomy(ErrorType.HANGING_PIECE, confidence=ErrorConfidence.LOW, secondary=(ErrorType.FORK,)),
    )
    assert low.primary_event is None and low.secondary_events == ()
    medium = build_move_explanation_facts(
        move_analysis=_row(chess.STARTING_FEN, "e2e4"), user_color=Color.WHITE,
        taxonomy=_taxonomy(ErrorType.DEVELOPMENT, confidence=ErrorConfidence.MEDIUM, secondary=(ErrorType.FORK,)),
    )
    assert medium.primary_event is ErrorType.DEVELOPMENT
    assert medium.secondary_events == (ErrorType.FORK,)


def test_black_user_evaluation_is_user_pov_and_nulls_are_safe():
    row = _row(chess.STARTING_FEN, "e2e4", before=200, after=-100)
    result = build_move_explanation_facts(move_analysis=row, user_color=Color.BLACK)
    assert (result.evaluation.before_cp, result.evaluation.after_cp) == (-200, 100)
    row.evaluation_before_cp = row.evaluation_after_cp = None
    null = build_move_explanation_facts(move_analysis=row, user_color=Color.BLACK)
    assert null.evaluation.before_cp is None and null.evaluation.after_cp is None


def test_non_finite_evaluation_and_cp_loss_fail_closed():
    row = _row(chess.STARTING_FEN, "e2e4")
    row.evaluation_before_cp = float("inf")
    row.evaluation_after_cp = float("nan")
    row.centipawn_loss = float("inf")
    result = build_move_explanation_facts(move_analysis=row, user_color=Color.WHITE)
    assert result.evaluation.before_cp is None
    assert result.evaluation.after_cp is None
    assert result.evaluation.centipawn_loss is None


def test_invalid_fen_is_minimal_or_partial_without_exception():
    result = build_move_explanation_facts(
        move_analysis=_row("invalid", "e2e4"), user_color=Color.WHITE,
        taxonomy=_taxonomy(ErrorType.KING_SAFETY),
    )
    assert result.played_move is None and result.fact_completeness == "partial"


def test_repeated_build_is_deterministic_and_has_no_io_dependencies():
    row = _row(chess.STARTING_FEN, "e2e4", best="e2e4")
    first = build_move_explanation_facts(move_analysis=row, user_color=Color.WHITE)
    second = build_move_explanation_facts(move_analysis=row, user_color=Color.WHITE)
    assert first == second
    source = Path(__import__("app.services.move_explanation_facts", fromlist=["x"]).__file__).read_text()
    assert all(token not in source for token in ("Stockfish", "urllib", "requests", "Session", "select("))


def test_prepared_taxonomy_context_can_be_reused_without_reconstructing_board():
    row = _row(chess.STARTING_FEN, "e2e4")
    before = chess.Board(row.fen_before)
    move = chess.Move.from_uci(row.played_move_uci)
    after = before.copy(stack=False)
    after.push(move)
    context = MoveTaxonomyContext(row, move, before, after, None, None)
    result = build_move_explanation_facts(
        move_analysis=row,
        user_color=Color.WHITE,
        taxonomy_context=context,
    )
    assert result.played_move.san == "e4"
