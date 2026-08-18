from dataclasses import dataclass

import chess

from app.models import GamePhase


# Standard tapered-evaluation phase units: Q=4, R=2, B/N=1 (initial total 24).
QUEEN_PHASE_WEIGHT = 4
ROOK_PHASE_WEIGHT = 2
MINOR_PHASE_WEIGHT = 1
ENDGAME_PHASE_MAX = 8

OPENING_MIN_PLY = 10
OPENING_MAX_PLY = 24
DEVELOPED_MINOR_PIECES = 4
KING_COMMITMENT_PLY = 14
KNOWN_LINE_MIN_PLY = 8
HEAVY_PIECES_OPENING_MIN = 4

_MINOR_STARTS = {
    chess.B1: chess.KNIGHT,
    chess.G1: chess.KNIGHT,
    chess.C1: chess.BISHOP,
    chess.F1: chess.BISHOP,
    chess.B8: chess.KNIGHT,
    chess.G8: chess.KNIGHT,
    chess.C8: chess.BISHOP,
    chess.F8: chess.BISHOP,
}


def material_phase_units(board: chess.Board) -> int:
    return (
        len(board.pieces(chess.QUEEN, chess.WHITE) | board.pieces(chess.QUEEN, chess.BLACK))
        * QUEEN_PHASE_WEIGHT
        + len(board.pieces(chess.ROOK, chess.WHITE) | board.pieces(chess.ROOK, chess.BLACK))
        * ROOK_PHASE_WEIGHT
        + len(
            board.pieces(chess.BISHOP, chess.WHITE)
            | board.pieces(chess.BISHOP, chess.BLACK)
            | board.pieces(chess.KNIGHT, chess.WHITE)
            | board.pieces(chess.KNIGHT, chess.BLACK)
        )
        * MINOR_PHASE_WEIGHT
    )


def _developed_minors(board: chess.Board) -> int:
    return sum(
        board.piece_type_at(square) != piece_type
        for square, piece_type in _MINOR_STARTS.items()
    )


def _committed_kings(board: chess.Board) -> int:
    return int(board.king(chess.WHITE) != chess.E1) + int(board.king(chess.BLACK) != chess.E8)


def _heavy_pieces(board: chess.Board) -> int:
    return sum(
        len(board.pieces(piece_type, color))
        for piece_type in (chess.QUEEN, chess.ROOK)
        for color in chess.COLORS
    )


@dataclass
class GamePhaseDetector:
    """Stateful, monotonic phase detector for consecutive game positions."""

    known_opening_end_ply: int | None = None
    phase: GamePhase = GamePhase.OPENING

    def detect(self, board: chess.Board, ply: int) -> GamePhase:
        if self.phase is GamePhase.ENDGAME:
            return self.phase

        if material_phase_units(board) <= ENDGAME_PHASE_MAX:
            self.phase = GamePhase.ENDGAME
            return self.phase

        if self.phase is GamePhase.MIDDLEGAME:
            return self.phase

        developed = _developed_minors(board)
        opening_line_finished = (
            self.known_opening_end_ply is not None
            and self.known_opening_end_ply >= KNOWN_LINE_MIN_PLY
            and ply > self.known_opening_end_ply
            and developed >= DEVELOPED_MINOR_PIECES
        )
        development_finished = (
            ply >= OPENING_MIN_PLY
            and developed >= DEVELOPED_MINOR_PIECES
            and (_committed_kings(board) > 0 or ply >= KING_COMMITMENT_PLY)
        )
        main_battle_started = (
            ply >= OPENING_MIN_PLY
            and _heavy_pieces(board) < HEAVY_PIECES_OPENING_MIN
        )
        if opening_line_finished or development_finished or main_battle_started or ply > OPENING_MAX_PLY:
            self.phase = GamePhase.MIDDLEGAME
        return self.phase
