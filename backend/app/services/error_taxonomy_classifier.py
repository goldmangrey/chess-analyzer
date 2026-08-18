from dataclasses import dataclass
from io import StringIO
from typing import Sequence

import chess
import chess.pgn

from app.models import (
    Color,
    CriticalMomentType,
    ErrorConfidence,
    ErrorType,
    Game,
    GamePhase,
    MoveAnalysis,
    MoveClassification,
)
from app.services.critical_moment_detector import CriticalMoment, CriticalMomentDetector
from app.services.evaluation_context import MateTransition, evaluation_to_user_pov, mate_transition


MIN_POSITIONAL_CP_LOSS = 100
MIN_KING_SAFETY_CP_LOSS = 150
MIN_HANGING_PIECE_VALUE = 3
MIN_BAD_EXCHANGE_VALUE_GAP = 2
MIN_UNDEVELOPED_MINORS = 3
MIN_NEW_KING_ZONE_ATTACKS = 1
MAX_SECONDARY_TYPES = 2

PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}

ERROR_PRIORITY = {
    ErrorType.MISSED_MATE: 100,
    ErrorType.ALLOWED_MATE: 95,
    ErrorType.HANGING_PIECE: 90,
    ErrorType.BAD_EXCHANGE: 85,
    ErrorType.KING_SAFETY: 80,
    ErrorType.FORK: 74,
    ErrorType.PIN: 73,
    ErrorType.SKEWER: 72,
    ErrorType.BACK_RANK: 71,
    ErrorType.TACTICAL_PATTERN: 70,
    ErrorType.MISSED_CAPTURE: 60,
    ErrorType.MISSED_CHECK: 55,
    ErrorType.DEVELOPMENT: 50,
    ErrorType.PAWN_STRUCTURE: 40,
}

CONFIDENCE_PRIORITY = {
    ErrorConfidence.HIGH: 3,
    ErrorConfidence.MEDIUM: 2,
    ErrorConfidence.LOW: 1,
}

_MINOR_STARTS = {
    Color.WHITE: ((chess.B1, chess.KNIGHT), (chess.G1, chess.KNIGHT), (chess.C1, chess.BISHOP), (chess.F1, chess.BISHOP)),
    Color.BLACK: ((chess.B8, chess.KNIGHT), (chess.G8, chess.KNIGHT), (chess.C8, chess.BISHOP), (chess.F8, chess.BISHOP)),
}


@dataclass(frozen=True)
class ErrorClassification:
    ply: int
    move_number: int
    move_san: str | None
    move_uci: str
    phase: GamePhase | None
    severity: MoveClassification
    primary_type: ErrorType | None
    secondary_types: tuple[ErrorType, ...]
    confidence: ErrorConfidence
    centipawn_loss: int
    critical_moment_type: CriticalMomentType | None


@dataclass(frozen=True)
class MoveTaxonomyContext:
    row: MoveAnalysis
    move: chess.Move
    before: chess.Board
    after: chess.Board
    previous: "MoveTaxonomyContext | None"
    next_move: chess.Move | None


def prepare_taxonomy_contexts(
    game: Game,
    rows: Sequence[MoveAnalysis],
) -> tuple[MoveTaxonomyContext, ...] | None:
    try:
        parsed = chess.pgn.read_game(StringIO(game.pgn))
    except (ValueError, UnicodeError):
        return None
    if parsed is None or parsed.errors:
        return None
    pgn_moves = tuple(parsed.mainline_moves())
    ordered = tuple(sorted(rows, key=lambda row: row.ply))
    if len(ordered) != len(pgn_moves):
        return None
    if any(row.ply != index or row.played_move_uci != move.uci() for index, (row, move) in enumerate(zip(ordered, pgn_moves), 1)):
        return None

    board = parsed.board()
    contexts: list[MoveTaxonomyContext] = []
    for index, (row, move) in enumerate(zip(ordered, pgn_moves)):
        before = board.copy(stack=False)
        expected_color = Color.WHITE if before.turn else Color.BLACK
        if row.player_color != expected_color or row.fen_before != before.fen():
            return None
        board.push(move)
        contexts.append(MoveTaxonomyContext(
            row=row,
            move=move,
            before=before,
            after=board.copy(stack=False),
            previous=contexts[-1] if contexts else None,
            next_move=pgn_moves[index + 1] if index + 1 < len(pgn_moves) else None,
        ))
    return tuple(contexts)


def _best_move(context: MoveTaxonomyContext) -> chess.Move | None:
    if not context.row.best_move_uci:
        return None
    try:
        move = chess.Move.from_uci(context.row.best_move_uci)
    except ValueError:
        return None
    return move if move in context.before.legal_moves else None


def _immediately_captured_piece(context: MoveTaxonomyContext, color: chess.Color) -> tuple[int, chess.Piece] | None:
    if context.next_move is None or not context.after.is_capture(context.next_move):
        return None
    square = context.next_move.to_square
    victim = context.after.piece_at(square)
    if victim is None or victim.color != color:
        return None
    return square, victim


def _hanging_piece(context: MoveTaxonomyContext, user: chess.Color) -> bool:
    captured = _immediately_captured_piece(context, user)
    if captured is None:
        return False
    square, victim = captured
    return (
        PIECE_VALUES[victim.piece_type] >= MIN_HANGING_PIECE_VALUE
        and context.after.is_attacked_by(not user, square)
        and not context.after.is_attacked_by(user, square)
    )


def _forced_recapture(context: MoveTaxonomyContext) -> bool:
    previous = context.previous
    return bool(
        previous
        and previous.before.is_capture(previous.move)
        and context.move.to_square == previous.move.to_square
    )


def _bad_exchange(context: MoveTaxonomyContext, user: chess.Color) -> bool:
    if not context.before.is_capture(context.move) or _forced_recapture(context):
        return False
    attacker = context.before.piece_at(context.move.from_square)
    victim = context.before.piece_at(context.move.to_square)
    immediately_captured = _immediately_captured_piece(context, user)
    if attacker is None or victim is None or immediately_captured is None:
        return False
    captured_square, recaptured_piece = immediately_captured
    return (
        captured_square == context.move.to_square
        and recaptured_piece.piece_type == attacker.piece_type
        and PIECE_VALUES[attacker.piece_type] - PIECE_VALUES[victim.piece_type]
        >= MIN_BAD_EXCHANGE_VALUE_GAP
    )


def _pawn_weaknesses(board: chess.Board, color: chess.Color) -> tuple[int, int]:
    pawns = board.pieces(chess.PAWN, color)
    by_file = [len(pawns & chess.BB_FILES[file_index]) for file_index in range(8)]
    doubled = sum(max(0, count - 1) for count in by_file)
    isolated = sum(
        count
        for file_index, count in enumerate(by_file)
        if count and not any(
            by_file[adjacent]
            for adjacent in (file_index - 1, file_index + 1)
            if 0 <= adjacent < 8
        )
    )
    return doubled, isolated


def _pawn_structure_damage(context: MoveTaxonomyContext, user: chess.Color) -> bool:
    piece = context.before.piece_at(context.move.from_square)
    before_doubled, before_isolated = _pawn_weaknesses(context.before, user)
    after_doubled, after_isolated = _pawn_weaknesses(context.after, user)
    return bool(
        piece
        and piece.color == user
        and piece.piece_type == chess.PAWN
        and (after_doubled > before_doubled or after_isolated > before_isolated)
    )


def _king_zone(board: chess.Board, color: chess.Color) -> chess.SquareSet:
    king = board.king(color)
    return chess.SquareSet() if king is None else chess.SquareSet(chess.BB_KING_ATTACKS[king] | chess.BB_SQUARES[king])


def _enemy_king_zone_attacks(board: chess.Board, color: chess.Color) -> int:
    return sum(board.is_attacked_by(not color, square) for square in _king_zone(board, color))


def _pawn_shield(board: chess.Board, color: chess.Color) -> int:
    king = board.king(color)
    if king is None:
        return 0
    direction = 1 if color == chess.WHITE else -1
    target_rank = chess.square_rank(king) + direction
    if not 0 <= target_rank < 8:
        return 0
    return sum(
        board.piece_at(chess.square(file_index, target_rank)) == chess.Piece(chess.PAWN, color)
        for file_index in range(max(0, chess.square_file(king) - 1), min(7, chess.square_file(king) + 1) + 1)
    )


def _king_safety_damage(context: MoveTaxonomyContext, user: chess.Color) -> bool:
    piece = context.before.piece_at(context.move.from_square)
    if piece is None or piece.color != user or piece.piece_type not in {chess.PAWN, chess.KING}:
        return False
    return (
        _pawn_shield(context.after, user) < _pawn_shield(context.before, user)
        and _enemy_king_zone_attacks(context.after, user) - _enemy_king_zone_attacks(context.before, user)
        >= MIN_NEW_KING_ZONE_ATTACKS
    )


def _undeveloped_minors(board: chess.Board, color: Color) -> int:
    native_color = color == Color.WHITE
    return sum(
        board.piece_at(square) == chess.Piece(piece_type, native_color)
        for square, piece_type in _MINOR_STARTS[color]
    )


def _development_error(context: MoveTaxonomyContext, history: Sequence[MoveTaxonomyContext], color: Color) -> bool:
    if context.row.phase != GamePhase.OPENING or _undeveloped_minors(context.before, color) < MIN_UNDEVELOPED_MINORS:
        return False
    piece = context.before.piece_at(context.move.from_square)
    if piece is None:
        return False
    if piece.piece_type == chess.QUEEN:
        return True
    if piece.piece_type in {chess.KNIGHT, chess.BISHOP}:
        return any(
            prior.row.player_color == color and prior.move.to_square == context.move.from_square
            for prior in history
        )
    if piece.piece_type == chess.PAWN:
        pawn_moves = sum(
            prior.row.player_color == color
            and prior.before.piece_type_at(prior.move.from_square) == chess.PAWN
            for prior in history
        )
        return pawn_moves >= 3
    if piece.piece_type == chess.KING:
        native_color = color == Color.WHITE
        return (
            context.before.has_castling_rights(native_color)
            and not context.after.has_castling_rights(native_color)
            and not context.before.is_castling(context.move)
        )
    return False


def _new_pin(context: MoveTaxonomyContext, user: chess.Color) -> bool:
    return any(
        piece.piece_type != chess.KING
        and context.after.is_pinned(user, square)
        and not context.before.is_pinned(user, square)
        for square, piece in context.after.piece_map().items()
        if piece.color == user
    )


def _allows_fork(context: MoveTaxonomyContext, user: chess.Color) -> bool:
    if context.next_move is None:
        return False
    board = context.after.copy(stack=False)
    if context.next_move not in board.legal_moves:
        return False
    board.push(context.next_move)
    attacker = board.piece_at(context.next_move.to_square)
    if attacker is None or attacker.color == user:
        return False
    valuable_targets = [
        square
        for square in board.attacks(context.next_move.to_square)
        if (piece := board.piece_at(square)) is not None
        and piece.color == user
        and PIECE_VALUES[piece.piece_type] >= 3
    ]
    return len(valuable_targets) >= 2


def _add(evidence: dict[ErrorType, ErrorConfidence], error_type: ErrorType, confidence: ErrorConfidence) -> None:
    current = evidence.get(error_type)
    if current is None or CONFIDENCE_PRIORITY[confidence] > CONFIDENCE_PRIORITY[current]:
        evidence[error_type] = confidence


class ErrorTaxonomyClassifier:
    def classify(
        self,
        game: Game,
        moves: Sequence[MoveAnalysis],
        critical_moments: Sequence[CriticalMoment] | None = None,
    ) -> tuple[ErrorClassification, ...]:
        contexts = prepare_taxonomy_contexts(game, moves)
        return self.classify_prepared(game, moves, contexts, critical_moments)

    def classify_prepared(
        self,
        game: Game,
        moves: Sequence[MoveAnalysis],
        contexts: tuple[MoveTaxonomyContext, ...] | None,
        critical_moments: Sequence[CriticalMoment] | None = None,
    ) -> tuple[ErrorClassification, ...]:
        if contexts is None:
            return ()
        moments = critical_moments
        if moments is None:
            moments = CriticalMomentDetector(game.user_color).detect(moves)
        critical_by_ply = {moment.ply: moment.type for moment in moments}
        native_user_color = game.user_color == Color.WHITE
        errors: list[ErrorClassification] = []

        for index, context in enumerate(contexts):
            row = context.row
            if not row.is_user_move or row.classification == MoveClassification.NORMAL:
                continue
            evidence: dict[ErrorType, ErrorConfidence] = {}
            before = evaluation_to_user_pov(row.evaluation_before_cp, game.user_color)
            after = evaluation_to_user_pov(row.evaluation_after_cp, game.user_color)
            if before is not None and after is not None:
                transition = mate_transition(before, after)
                if transition == MateTransition.MISSED_MATE:
                    _add(evidence, ErrorType.MISSED_MATE, ErrorConfidence.HIGH)
                elif transition == MateTransition.ALLOWED_MATE:
                    _add(evidence, ErrorType.ALLOWED_MATE, ErrorConfidence.HIGH)

            best = _best_move(context)
            if row.centipawn_loss >= MIN_POSITIONAL_CP_LOSS and best is not None and best != context.move:
                if context.before.is_capture(best):
                    _add(evidence, ErrorType.MISSED_CAPTURE, ErrorConfidence.HIGH)
                if context.before.gives_check(best):
                    _add(evidence, ErrorType.MISSED_CHECK, ErrorConfidence.HIGH)

            if row.centipawn_loss >= MIN_POSITIONAL_CP_LOSS:
                if _hanging_piece(context, native_user_color):
                    _add(evidence, ErrorType.HANGING_PIECE, ErrorConfidence.HIGH)
                if _bad_exchange(context, native_user_color):
                    _add(evidence, ErrorType.BAD_EXCHANGE, ErrorConfidence.HIGH)
                if _pawn_structure_damage(context, native_user_color):
                    _add(evidence, ErrorType.PAWN_STRUCTURE, ErrorConfidence.MEDIUM)
                if _development_error(context, contexts[:index], game.user_color):
                    _add(evidence, ErrorType.DEVELOPMENT, ErrorConfidence.MEDIUM)
                if _new_pin(context, native_user_color):
                    _add(evidence, ErrorType.TACTICAL_PATTERN, ErrorConfidence.MEDIUM)
                    _add(evidence, ErrorType.PIN, ErrorConfidence.MEDIUM)
                if _allows_fork(context, native_user_color):
                    _add(evidence, ErrorType.TACTICAL_PATTERN, ErrorConfidence.HIGH)
                    _add(evidence, ErrorType.FORK, ErrorConfidence.HIGH)
            if row.centipawn_loss >= MIN_KING_SAFETY_CP_LOSS and _king_safety_damage(context, native_user_color):
                _add(evidence, ErrorType.KING_SAFETY, ErrorConfidence.MEDIUM)

            ranked = sorted(evidence, key=lambda item: (-ERROR_PRIORITY[item], item.value))
            primary = ranked[0] if ranked else None
            secondary = tuple(ranked[1:1 + MAX_SECONDARY_TYPES])
            errors.append(ErrorClassification(
                ply=row.ply,
                move_number=row.move_number,
                move_san=row.played_move_san,
                move_uci=row.played_move_uci,
                phase=row.phase,
                severity=row.classification,
                primary_type=primary,
                secondary_types=secondary,
                confidence=evidence[primary] if primary else ErrorConfidence.LOW,
                centipawn_loss=row.centipawn_loss,
                critical_moment_type=critical_by_ply.get(row.ply),
            ))
        return tuple(errors)
