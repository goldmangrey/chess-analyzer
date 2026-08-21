from dataclasses import dataclass
from math import isfinite
from typing import Literal, Sequence

import chess

from app.models import Color, ErrorConfidence, ErrorType, GamePhase, MoveClassification
from app.services.error_taxonomy_classifier import (
    ErrorClassification,
    MoveTaxonomyContext,
    PIECE_VALUES,
    _pawn_shield,
    _pawn_weaknesses,
    _undeveloped_minors,
)
from app.services.evaluation_context import (
    MATE_EVALUATION_THRESHOLD,
    MateTransition,
    evaluation_to_user_pov,
    mate_transition,
)


FactCompleteness = Literal["complete", "partial", "minimal"]
MateState = Literal["for_user", "against_user"]


@dataclass(frozen=True)
class PieceOnSquare:
    piece: str
    color: Color
    square: str
    value: int


@dataclass(frozen=True)
class MoveFact:
    uci: str
    san: str
    piece: str
    color: Color
    from_square: str
    to_square: str
    is_capture: bool
    captured_piece: PieceOnSquare | None
    captured_square: str | None
    is_check: bool
    is_castling: bool
    castling_side: Literal["kingside", "queenside"] | None
    is_promotion: bool
    promotion_piece: str | None


@dataclass(frozen=True)
class MaterialBalance:
    white: int
    black: int
    white_minus_black: int


@dataclass(frozen=True)
class MaterialFacts:
    before: MaterialBalance
    after_played_move: MaterialBalance
    immediate_capture_value: int
    delta_for_played_color: int


@dataclass(frozen=True)
class HangingPieceFacts:
    piece: PieceOnSquare
    attackers: tuple[PieceOnSquare, ...]
    defenders: tuple[PieceOnSquare, ...]
    is_undefended: bool
    opponent_capture_moves: tuple[str, ...]


@dataclass(frozen=True)
class MissedCaptureFacts:
    target: PieceOnSquare
    available_move: MoveFact


@dataclass(frozen=True)
class ForkFacts:
    attacker: PieceOnSquare
    targets: tuple[PieceOnSquare, ...]


@dataclass(frozen=True)
class PinFacts:
    pinned_piece: PieceOnSquare
    king_square: str
    attacking_sliders: tuple[PieceOnSquare, ...]


@dataclass(frozen=True)
class KingSafetyFacts:
    king_square_before: str | None
    king_square_after: str | None
    castling_rights_before: bool
    castling_rights_after: bool
    king_in_check_after: bool
    pawn_shield_before: int
    pawn_shield_after: int
    king_zone_attacks_before: int
    king_zone_attacks_after: int


@dataclass(frozen=True)
class DevelopmentFacts:
    moved_piece: str
    undeveloped_minor_pieces_before: int
    queen_moved: bool
    piece_returned_to_origin: bool


@dataclass(frozen=True)
class PawnStructureFacts:
    doubled_before: int
    doubled_after: int
    isolated_before: int
    isolated_after: int
    pawn_islands_before: int
    pawn_islands_after: int


@dataclass(frozen=True)
class PlayedBestComparison:
    is_engine_best: bool
    same_piece: bool
    same_destination: bool
    played_is_capture: bool
    best_is_capture: bool
    played_gives_check: bool
    best_gives_check: bool
    played_material_gain: int
    best_immediate_material_gain: int
    best_move_wins_more_material: bool


@dataclass(frozen=True)
class EvaluationFacts:
    before_cp: int | None
    after_cp: int | None
    centipawn_loss: int | None
    mate_before: MateState | None
    mate_after: MateState | None
    missed_mate: bool
    opponent_has_forced_mate: bool
    mate_distance: int | None


@dataclass(frozen=True)
class MoveExplanationFacts:
    game_id: int | None
    ply: int
    classification: MoveClassification | None
    phase: GamePhase | None
    played_color: Color | None
    opponent_color: Color | None
    played_move: MoveFact | None
    best_move: MoveFact | None
    primary_event: ErrorType | None
    secondary_events: tuple[ErrorType, ...]
    taxonomy_confidence: ErrorConfidence | None
    material: MaterialFacts | None
    hanging_piece: HangingPieceFacts | None
    missed_capture: MissedCaptureFacts | None
    missed_check: MoveFact | None
    missed_mate: bool
    allowed_mate: bool
    fork: ForkFacts | None
    pin: PinFacts | None
    king_safety: KingSafetyFacts | None
    development: DevelopmentFacts | None
    pawn_structure: PawnStructureFacts | None
    bad_exchange: MaterialFacts | None
    comparison: PlayedBestComparison | None
    evaluation: EvaluationFacts
    fact_completeness: FactCompleteness


def _color(native: chess.Color) -> Color:
    return Color.WHITE if native else Color.BLACK


def _piece_name(piece_type: int) -> str:
    return chess.piece_name(piece_type)


def _piece(board: chess.Board, square: int) -> PieceOnSquare | None:
    value = board.piece_at(square)
    if value is None:
        return None
    return PieceOnSquare(
        _piece_name(value.piece_type),
        _color(value.color),
        chess.square_name(square),
        PIECE_VALUES[value.piece_type],
    )


def _capture_square(board: chess.Board, move: chess.Move) -> int | None:
    if not board.is_capture(move):
        return None
    if board.is_en_passant(move):
        return move.to_square - 8 if board.turn == chess.WHITE else move.to_square + 8
    return move.to_square


def _move_fact(board: chess.Board, uci: str | None) -> MoveFact | None:
    if not uci:
        return None
    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        return None
    if move not in board.legal_moves:
        return None
    mover = board.piece_at(move.from_square)
    if mover is None:
        return None
    capture_square = _capture_square(board, move)
    captured = _piece(board, capture_square) if capture_square is not None else None
    castling = board.is_castling(move)
    return MoveFact(
        uci=move.uci(),
        san=board.san(move),
        piece=_piece_name(mover.piece_type),
        color=_color(mover.color),
        from_square=chess.square_name(move.from_square),
        to_square=chess.square_name(move.to_square),
        is_capture=capture_square is not None,
        captured_piece=captured,
        captured_square=chess.square_name(capture_square) if capture_square is not None else None,
        is_check=board.gives_check(move),
        is_castling=castling,
        castling_side=(
            "kingside" if castling and chess.square_file(move.to_square) > chess.square_file(move.from_square)
            else "queenside" if castling else None
        ),
        is_promotion=move.promotion is not None,
        promotion_piece=_piece_name(move.promotion) if move.promotion else None,
    )


def _material(board: chess.Board) -> MaterialBalance:
    white = sum(len(board.pieces(kind, chess.WHITE)) * value for kind, value in PIECE_VALUES.items())
    black = sum(len(board.pieces(kind, chess.BLACK)) * value for kind, value in PIECE_VALUES.items())
    return MaterialBalance(white, black, white - black)


def _material_facts(before: chess.Board, after: chess.Board, move: MoveFact) -> MaterialFacts:
    first = _material(before)
    second = _material(after)
    signed_before = first.white_minus_black if move.color is Color.WHITE else -first.white_minus_black
    signed_after = second.white_minus_black if move.color is Color.WHITE else -second.white_minus_black
    return MaterialFacts(
        first,
        second,
        move.captured_piece.value if move.captured_piece else 0,
        signed_after - signed_before,
    )


def _pieces_at(board: chess.Board, squares) -> tuple[PieceOnSquare, ...]:
    return tuple(item for square in sorted(squares) if (item := _piece(board, square)) is not None)


def _hanging(after: chess.Board, played_color: chess.Color) -> HangingPieceFacts | None:
    candidates: list[HangingPieceFacts] = []
    for square, value in after.piece_map().items():
        if value.color != played_color or PIECE_VALUES[value.piece_type] < 3:
            continue
        captures = tuple(
            after.san(move)
            for move in after.legal_moves
            if after.is_capture(move) and move.to_square == square
        )
        if not captures:
            continue
        attackers = _pieces_at(after, after.attackers(not played_color, square))
        defenders = _pieces_at(after, after.attackers(played_color, square))
        piece = _piece(after, square)
        if piece is not None:
            candidates.append(HangingPieceFacts(piece, attackers, defenders, not defenders, captures))
    undefended = [item for item in candidates if item.is_undefended]
    pool = undefended or candidates
    return sorted(pool, key=lambda item: (-item.piece.value, item.piece.square))[0] if pool else None


def _fork(after: chess.Board, next_move_uci: str | None, played_color: chess.Color) -> ForkFacts | None:
    move_fact = _move_fact(after, next_move_uci)
    if move_fact is None:
        return None
    move = chess.Move.from_uci(move_fact.uci)
    board = after.copy(stack=False)
    board.push(move)
    attacker = _piece(board, move.to_square)
    if attacker is None or attacker.color is _color(played_color):
        return None
    targets = tuple(
        target
        for square in board.attacks(move.to_square)
        if (target := _piece(board, square)) is not None
        and target.color is _color(played_color)
        and (target.piece == "king" or target.value >= 3)
    )
    return ForkFacts(attacker, targets) if len(targets) >= 2 else None


def _pin(after: chess.Board, played_color: chess.Color) -> PinFacts | None:
    king = after.king(played_color)
    if king is None:
        return None
    for square, value in sorted(after.piece_map().items()):
        if value.color == played_color and value.piece_type != chess.KING and after.is_pinned(played_color, square):
            pinned = _piece(after, square)
            sliders = tuple(
                item
                for attacker_square in after.attackers(not played_color, square)
                if (item := _piece(after, attacker_square)) is not None
                and item.piece in {"bishop", "rook", "queen"}
            )
            if pinned is not None:
                return PinFacts(pinned, chess.square_name(king), sliders)
    return None


def _king_zone_attacks(board: chess.Board, color: chess.Color) -> int:
    king = board.king(color)
    if king is None:
        return 0
    zone = chess.SquareSet(chess.BB_KING_ATTACKS[king] | chess.BB_SQUARES[king])
    return sum(board.is_attacked_by(not color, square) for square in zone)


def _pawn_islands(board: chess.Board, color: chess.Color) -> int:
    occupied = [bool(board.pieces(chess.PAWN, color) & chess.BB_FILES[index]) for index in range(8)]
    return sum(value and (index == 0 or not occupied[index - 1]) for index, value in enumerate(occupied))


def _evaluation(row, user_color: Color) -> EvaluationFacts:
    before = evaluation_to_user_pov(getattr(row, "evaluation_before_cp", None), user_color)
    after = evaluation_to_user_pov(getattr(row, "evaluation_after_cp", None), user_color)
    before = before if before is not None and isfinite(before) else None
    after = after if after is not None and isfinite(after) else None
    transition = mate_transition(before, after) if before is not None and after is not None else None
    def state(value: int | None) -> MateState | None:
        if value is None or abs(value) < MATE_EVALUATION_THRESHOLD:
            return None
        return "for_user" if value > 0 else "against_user"
    return EvaluationFacts(
        before_cp=None if state(before) else before,
        after_cp=None if state(after) else after,
        centipawn_loss=(
            int(row.centipawn_loss)
            if getattr(row, "centipawn_loss", None) is not None
            and isfinite(row.centipawn_loss)
            and row.centipawn_loss >= 0
            else None
        ),
        mate_before=state(before),
        mate_after=state(after),
        missed_mate=transition is MateTransition.MISSED_MATE,
        opponent_has_forced_mate=transition is MateTransition.ALLOWED_MATE,
        mate_distance=None,
    )


def build_move_explanation_facts(
    *,
    move_analysis,
    user_color: Color,
    taxonomy: ErrorClassification | None = None,
    next_move_uci: str | None = None,
    taxonomy_context: MoveTaxonomyContext | None = None,
) -> MoveExplanationFacts:
    evaluation = _evaluation(move_analysis, user_color)
    classification = getattr(move_analysis, "classification", None)
    classification = classification if isinstance(classification, MoveClassification) else None
    phase = getattr(move_analysis, "phase", None)
    phase = phase if isinstance(phase, GamePhase) else None
    taxonomy_usable = bool(
        taxonomy
        and taxonomy.confidence in {ErrorConfidence.MEDIUM, ErrorConfidence.HIGH}
        and taxonomy.primary_type is not None
    )
    primary = taxonomy.primary_type if taxonomy_usable else None
    secondary = taxonomy.secondary_types if taxonomy_usable else ()
    taxonomy_confidence = taxonomy.confidence if taxonomy else None
    def failed(played_move=None, best_move=None) -> MoveExplanationFacts:
        return MoveExplanationFacts(
            game_id=getattr(move_analysis, "game_id", None),
            ply=getattr(move_analysis, "ply", 0),
            classification=classification,
            phase=phase,
            played_color=played_move.color if played_move else None,
            opponent_color=None,
            played_move=played_move,
            best_move=best_move,
            primary_event=primary,
            secondary_events=secondary,
            taxonomy_confidence=taxonomy_confidence,
            material=None,
            hanging_piece=None,
            missed_capture=None,
            missed_check=None,
            missed_mate=evaluation.missed_mate,
            allowed_mate=evaluation.opponent_has_forced_mate,
            fork=None,
            pin=None,
            king_safety=None,
            development=None,
            pawn_structure=None,
            bad_exchange=None,
            comparison=None,
            evaluation=evaluation,
            fact_completeness="partial" if primary else "minimal",
        )
    context_matches = bool(
        taxonomy_context
        and taxonomy_context.row.ply == getattr(move_analysis, "ply", None)
        and taxonomy_context.move.uci() == getattr(move_analysis, "played_move_uci", None)
    )
    if context_matches:
        before = taxonomy_context.before.copy(stack=False)
    else:
        try:
            before = chess.Board(move_analysis.fen_before)
            if not before.is_valid():
                raise ValueError
        except (AttributeError, TypeError, ValueError):
            return failed()
    played = _move_fact(before, getattr(move_analysis, "played_move_uci", None))
    best = _move_fact(before, getattr(move_analysis, "best_move_uci", None))
    if played is None:
        return failed(best_move=best)
    played_move = chess.Move.from_uci(played.uci)
    if context_matches:
        after = taxonomy_context.after.copy(stack=False)
        if next_move_uci is None and taxonomy_context.next_move is not None:
            next_move_uci = taxonomy_context.next_move.uci()
    else:
        after = before.copy(stack=False)
        after.push(played_move)
    native_color = played.color is Color.WHITE
    material = _material_facts(before, after, played)
    best_gain = best.captured_piece.value if best and best.captured_piece else 0
    comparison = (
        PlayedBestComparison(
            played.uci == best.uci,
            played.piece == best.piece,
            played.to_square == best.to_square,
            played.is_capture,
            best.is_capture,
            played.is_check,
            best.is_check,
            material.immediate_capture_value,
            best_gain,
            best_gain > material.immediate_capture_value,
        ) if best else None
    )
    hanging = _hanging(after, native_color) if primary is ErrorType.HANGING_PIECE else None
    missed_capture = (
        MissedCaptureFacts(best.captured_piece, best)
        if primary is ErrorType.MISSED_CAPTURE and best and best.captured_piece
        else None
    )
    missed_check = best if primary is ErrorType.MISSED_CHECK and best and best.is_check else None
    fork = _fork(after, next_move_uci, native_color) if primary is ErrorType.FORK else None
    pin = _pin(after, native_color) if primary is ErrorType.PIN else None
    king = None
    if primary is ErrorType.KING_SAFETY:
        king = KingSafetyFacts(
            chess.square_name(before.king(native_color)) if before.king(native_color) is not None else None,
            chess.square_name(after.king(native_color)) if after.king(native_color) is not None else None,
            before.has_castling_rights(native_color), after.has_castling_rights(native_color),
            after.is_check(), _pawn_shield(before, native_color), _pawn_shield(after, native_color),
            _king_zone_attacks(before, native_color), _king_zone_attacks(after, native_color),
        )
    development = None
    if primary is ErrorType.DEVELOPMENT:
        rank = "1" if native_color else "8"
        origin_squares = {
            "knight": {f"b{rank}", f"g{rank}"},
            "bishop": {f"c{rank}", f"f{rank}"},
            "queen": {f"d{rank}"},
            "king": {f"e{rank}"},
        }.get(played.piece, set())
        development = DevelopmentFacts(
            played.piece,
            _undeveloped_minors(before, played.color),
            played.piece == "queen",
            played.to_square in origin_squares,
        )
    pawn_structure = None
    if primary is ErrorType.PAWN_STRUCTURE:
        bd, bi = _pawn_weaknesses(before, native_color)
        ad, ai = _pawn_weaknesses(after, native_color)
        pawn_structure = PawnStructureFacts(
            bd, ad, bi, ai, _pawn_islands(before, native_color), _pawn_islands(after, native_color)
        )
    details = {
        ErrorType.HANGING_PIECE: hanging,
        ErrorType.MISSED_CAPTURE: missed_capture,
        ErrorType.MISSED_CHECK: missed_check,
        ErrorType.FORK: fork,
        ErrorType.PIN: pin,
        ErrorType.KING_SAFETY: king,
        ErrorType.DEVELOPMENT: development,
        ErrorType.PAWN_STRUCTURE: pawn_structure,
        ErrorType.BAD_EXCHANGE: material if played.is_capture else None,
        ErrorType.MISSED_MATE: evaluation.missed_mate or None,
        ErrorType.ALLOWED_MATE: evaluation.opponent_has_forced_mate or None,
    }
    completeness: FactCompleteness = (
        "complete" if primary is not None and details.get(primary) is not None
        else "partial" if primary is not None
        else "minimal"
    )
    return MoveExplanationFacts(
        getattr(move_analysis, "game_id", None), getattr(move_analysis, "ply", 0),
        classification, phase, played.color, Color.BLACK if played.color is Color.WHITE else Color.WHITE,
        played, best, primary, secondary, taxonomy_confidence, material, hanging,
        missed_capture, missed_check, evaluation.missed_mate, evaluation.opponent_has_forced_mate,
        fork, pin, king, development, pawn_structure,
        material if primary is ErrorType.BAD_EXCHANGE and played.is_capture else None,
        comparison, evaluation, completeness,
    )
