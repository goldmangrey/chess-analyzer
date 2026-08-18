from io import StringIO

import chess
import chess.pgn

from app.models import (
    Color,
    CriticalMomentType,
    ErrorConfidence,
    ErrorType,
    Game,
    GamePhase,
    GameResult,
    MoveAnalysis,
    MoveClassification,
)
from app.services.error_taxonomy_classifier import ErrorTaxonomyClassifier
from app.services.evaluation_context import MATE_EVALUATION_THRESHOLD


def scenario(
    fen: str,
    moves: str,
    *,
    user_color: Color = Color.WHITE,
    target_ply: int = 1,
    phase: GamePhase = GamePhase.MIDDLEGAME,
    severity: MoveClassification = MoveClassification.BLUNDER,
    loss: int = 200,
    before: int = 0,
    after: int = -200,
    best_move: str | None = None,
) -> tuple[Game, list[MoveAnalysis]]:
    pgn = f'[SetUp "1"]\n[FEN "{fen}"]\n[Result "*"]\n\n{moves} *'
    parsed = chess.pgn.read_game(StringIO(pgn))
    assert parsed is not None and not parsed.errors
    board = parsed.board()
    rows: list[MoveAnalysis] = []
    native_user = user_color == Color.WHITE
    for ply, move in enumerate(parsed.mainline_moves(), 1):
        player = Color.WHITE if board.turn else Color.BLACK
        is_target = ply == target_ply
        rows.append(MoveAnalysis(
            id=ply,
            game_id=1,
            ply=ply,
            move_number=(ply + 1) // 2,
            player_color=player,
            is_user_move=board.turn == native_user,
            fen_before=board.fen(),
            played_move_uci=move.uci(),
            played_move_san=board.san(move),
            best_move_uci=best_move if is_target else None,
            evaluation_before_cp=before if is_target else 0,
            evaluation_after_cp=after if is_target else 0,
            centipawn_loss=loss if is_target else 0,
            classification=severity if is_target else MoveClassification.NORMAL,
            phase=phase,
        ))
        board.push(move)
    game = Game(
        id=1,
        external_id="taxonomy",
        white_username="User" if user_color == Color.WHITE else "Opponent",
        black_username="User" if user_color == Color.BLACK else "Opponent",
        user_color=user_color,
        result=GameResult.LOSS,
        pgn=pgn,
    )
    return game, rows


def classify(*args, **kwargs):
    game, rows = scenario(*args, **kwargs)
    return ErrorTaxonomyClassifier().classify(game, rows)


def types(error) -> set[ErrorType]:
    return {item for item in (error.primary_type, *error.secondary_types) if item is not None}


def test_hanging_piece_requires_actual_capture_and_no_defender() -> None:
    error = classify("3r2k1/8/8/8/8/8/8/3QK3 w - - 0 1", "1. Qd4 Rxd4")[0]
    assert error.primary_type == ErrorType.HANGING_PIECE
    assert error.confidence == ErrorConfidence.HIGH

    defended = classify("3r2k1/8/8/8/8/8/8/Q2RK3 w - - 0 1", "1. Qd4 Rxd4")[0]
    assert ErrorType.HANGING_PIECE not in types(defended)


def test_missed_and_allowed_mate_reuse_shared_transition_logic() -> None:
    missed = classify("6k1/8/8/8/8/8/6P1/6K1 w - - 0 1", "1. g3", before=MATE_EVALUATION_THRESHOLD, after=20)[0]
    allowed = classify("6k1/8/8/8/8/8/6P1/6K1 w - - 0 1", "1. g3", before=0, after=-MATE_EVALUATION_THRESHOLD)[0]
    assert (missed.primary_type, missed.confidence) == (ErrorType.MISSED_MATE, ErrorConfidence.HIGH)
    assert (allowed.primary_type, allowed.confidence) == (ErrorType.ALLOWED_MATE, ErrorConfidence.HIGH)


def test_development_is_opening_only_and_random_error_stays_low_confidence() -> None:
    opening = classify(chess.STARTING_FEN, "1. e4 e5 2. Qh5", target_ply=3, phase=GamePhase.OPENING)[0]
    outside = classify(chess.STARTING_FEN, "1. e4 e5 2. Qh5", target_ply=3, phase=GamePhase.MIDDLEGAME)[0]
    assert opening.primary_type == ErrorType.DEVELOPMENT
    assert outside.primary_type is None and outside.confidence == ErrorConfidence.LOW


def test_king_safety_needs_shield_damage_and_new_king_zone_pressure() -> None:
    exposed = classify("6rk/8/8/8/8/7p/6PP/7K w - - 0 1", "1. gxh3", loss=180)[0]
    random_pawn = classify("6k1/8/8/8/8/8/6PP/7K w - - 0 1", "1. h3", loss=180)[0]
    assert exposed.primary_type == ErrorType.KING_SAFETY
    assert exposed.confidence == ErrorConfidence.MEDIUM
    assert ErrorType.KING_SAFETY not in types(random_pawn)


def test_bad_exchange_and_forced_recapture_exception() -> None:
    error = classify("r5k1/p7/8/8/8/8/8/R5BK w - - 0 1", "1. Rxa7 Rxa7")[0]
    assert error.primary_type == ErrorType.BAD_EXCHANGE

    forced = classify(
        "3q2k1/3p4/4P3/8/8/8/8/3R2K1 w - - 0 1",
        "1. exd7 Qxd7 2. Rxd7",
        user_color=Color.BLACK,
        target_ply=2,
    )[0]
    assert ErrorType.BAD_EXCHANGE not in types(forced)


def test_created_doubled_and_isolated_pawns_are_positional_evidence() -> None:
    error = classify("6k1/8/8/8/2n5/3P4/2P5/6K1 w - - 0 1", "1. dxc4")[0]
    assert error.primary_type == ErrorType.PAWN_STRUCTURE
    assert error.confidence == ErrorConfidence.MEDIUM


def test_provable_fork_and_pin_use_board_geometry() -> None:
    fork = classify("6k1/8/8/4n3/8/8/1Q1R3P/6K1 w - - 0 1", "1. h3 Nc4")[0]
    assert fork.primary_type == ErrorType.FORK
    assert ErrorType.TACTICAL_PATTERN in fork.secondary_types

    pin = classify("4r1k1/8/8/8/8/4B3/4N3/4K3 w - - 0 1", "1. Bf4")[0]
    assert pin.primary_type == ErrorType.PIN
    assert ErrorType.TACTICAL_PATTERN in pin.secondary_types


def test_persisted_best_move_is_required_for_missed_capture_or_check() -> None:
    with_best = classify(
        "6k1/8/8/8/8/8/1q4P1/3R2K1 w - - 0 1",
        "1. g3",
        best_move="d1d8",
    )[0]
    without_best = classify("6k1/8/8/8/8/8/1q4P1/3R2K1 w - - 0 1", "1. g3")[0]
    assert ErrorType.MISSED_CHECK in types(with_best)
    assert ErrorType.MISSED_CHECK not in types(without_best)


def test_black_user_pov_opponent_and_normal_moves_are_handled() -> None:
    black = classify(
        "6k1/6p1/8/8/8/8/8/6K1 b - - 0 1",
        "1... g6",
        user_color=Color.BLACK,
        before=-MATE_EVALUATION_THRESHOLD,
        after=-10,
    )[0]
    assert black.primary_type == ErrorType.MISSED_MATE

    game, rows = scenario(chess.STARTING_FEN, "1. e4 e5", target_ply=1)
    rows[0].is_user_move = False
    assert ErrorTaxonomyClassifier().classify(game, rows) == ()
    rows[0].is_user_move = True
    rows[0].classification = MoveClassification.NORMAL
    assert ErrorTaxonomyClassifier().classify(game, rows) == ()


def test_multiple_causes_have_stable_priority_and_at_most_two_secondaries() -> None:
    error = classify(
        "6k1/8/8/8/8/8/1q4P1/3R2K1 w - - 0 1",
        "1. g3",
        before=0,
        after=-MATE_EVALUATION_THRESHOLD,
        best_move="d1d8",
    )[0]
    assert error.primary_type == ErrorType.ALLOWED_MATE
    assert ErrorType.MISSED_CHECK in error.secondary_types
    assert len(error.secondary_types) <= 2


def test_ply_or_uci_mismatch_fails_closed() -> None:
    game, rows = scenario(chess.STARTING_FEN, "1. e4 e5")
    rows[0].played_move_uci = "d2d4"
    assert ErrorTaxonomyClassifier().classify(game, rows) == ()


def test_critical_moment_type_and_phase_are_attached_without_gating_taxonomy() -> None:
    error = classify(
        chess.STARTING_FEN,
        "1. e4 e5 2. Qh5",
        target_ply=3,
        phase=GamePhase.OPENING,
        before=25,
        after=-340,
        loss=365,
    )[0]
    assert error.primary_type == ErrorType.DEVELOPMENT
    assert error.critical_moment_type == CriticalMomentType.TURNING_POINT
    assert error.phase == GamePhase.OPENING
