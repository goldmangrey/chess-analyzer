from io import StringIO

import chess.pgn

from app.models import Game, MoveAnalysis
from app.services.game_phase_detector import GamePhaseDetector
from app.services.opening_resolver import known_opening_ply


class PhaseBackfillError(ValueError):
    pass


def assign_game_phases(game: Game, analyses: list[MoveAnalysis]) -> int:
    """Assign persisted phases from PGN only; Stockfish metrics remain untouched."""
    try:
        parsed = chess.pgn.read_game(StringIO(game.pgn))
    except (ValueError, UnicodeError) as error:
        raise PhaseBackfillError("saved PGN cannot be parsed") from error
    if parsed is None or parsed.errors:
        raise PhaseBackfillError("saved PGN cannot be parsed")
    moves = tuple(parsed.mainline_moves())
    rows_by_ply = {row.ply: row for row in analyses}
    expected_plies = set(range(1, len(moves) + 1))
    if set(rows_by_ply) != expected_plies:
        raise PhaseBackfillError("PGN plies do not match persisted analysis rows")

    detector = GamePhaseDetector(known_opening_end_ply=known_opening_ply(moves))
    board = parsed.board()
    changed = 0
    for ply, move in enumerate(moves, 1):
        phase = detector.detect(board, ply)
        row = rows_by_ply[ply]
        if row.phase != phase:
            row.phase = phase
            changed += 1
        board.push(move)
    return changed
