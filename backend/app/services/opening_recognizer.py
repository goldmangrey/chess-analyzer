from collections.abc import Iterable
from dataclasses import dataclass
from io import StringIO
from typing import Literal

import chess
import chess.pgn

from app.services.opening_book import (
    OpeningRecord,
    load_opening_book,
    normalize_position_key,
    parse_opening_name,
)


RecognitionSource = Literal["position_book", "pgn_header", "eco_only", "unknown"]


@dataclass(frozen=True)
class OpeningMatch:
    game_ply: int
    record: OpeningRecord
    move_san: str
    move_uci: str


@dataclass(frozen=True)
class OpeningRecognitionResult:
    eco: str | None
    name: str | None
    family: str | None
    variation: str | None
    subvariation: str | None
    canonical_record_ply: int | None
    deepest_match_ply: int | None
    deepest_match_move_san: str | None
    deepest_match_move_uci: str | None
    last_named_match_ply: int | None
    last_named_match_move_san: str | None
    last_named_match_move_uci: str | None
    last_sequence_book_ply: int | None
    last_sequence_book_move_san: str | None
    last_sequence_book_move_uci: str | None
    first_deviation_ply: int | None
    first_deviation_move_san: str | None
    first_deviation_move_uci: str | None
    transposition_reentry: bool
    first_reentry_ply: int | None
    matches: tuple[OpeningMatch, ...]
    source: RecognitionSource


def _empty(
    *,
    eco: str | None = None,
    name: str | None = None,
    source: RecognitionSource = "unknown",
) -> OpeningRecognitionResult:
    family, variations = parse_opening_name(name) if name else (None, ())
    return OpeningRecognitionResult(
        eco=eco,
        name=name,
        family=family,
        variation=variations[0] if variations else None,
        subvariation=", ".join(variations[1:]) if len(variations) > 1 else None,
        canonical_record_ply=None,
        deepest_match_ply=None,
        deepest_match_move_san=None,
        deepest_match_move_uci=None,
        last_named_match_ply=None,
        last_named_match_move_san=None,
        last_named_match_move_uci=None,
        last_sequence_book_ply=None,
        last_sequence_book_move_san=None,
        last_sequence_book_move_uci=None,
        first_deviation_ply=None,
        first_deviation_move_san=None,
        first_deviation_move_uci=None,
        transposition_reentry=False,
        first_reentry_ply=None,
        matches=(),
        source=source,
    )


def _fallback(eco: str | None, opening_name: str | None) -> OpeningRecognitionResult:
    normalized_eco = (eco or "").strip().upper()
    if len(normalized_eco) != 3 or normalized_eco[0] not in "ABCDE" or not normalized_eco[1:].isdigit():
        normalized_eco = ""
    name = (opening_name or "").strip()
    if name and name != "?":
        return _empty(eco=normalized_eco or None, name=name, source="pgn_header")
    if normalized_eco:
        return _empty(eco=normalized_eco, source="eco_only")
    return _empty()


def recognize_moves(
    moves: Iterable[chess.Move | str],
    *,
    starting_board: chess.Board | None = None,
    eco: str | None = None,
    opening_name: str | None = None,
) -> OpeningRecognitionResult:
    board = (
        starting_board.copy(stack=False)
        if starting_board is not None
        else chess.Board()
    )
    if normalize_position_key(board) != normalize_position_key(chess.Board()):
        return _fallback(eco, opening_name)
    book = load_opening_book()
    sequence: list[str] = []
    played: list[tuple[int, str, str]] = []
    matches: list[OpeningMatch] = []
    first_deviation: tuple[int, str, str] | None = None
    last_sequence: tuple[int, str, str] | None = None
    try:
        for ply, value in enumerate(moves, start=1):
            move = value if isinstance(value, chess.Move) else chess.Move.from_uci(value)
            if move not in board.legal_moves:
                return _fallback(eco, opening_name)
            san = board.san(move)
            uci = move.uci()
            sequence.append(uci)
            played.append((ply, san, uci))
            if first_deviation is None:
                if book.is_sequence_prefix(sequence):
                    last_sequence = played[-1]
                else:
                    first_deviation = played[-1]
            board.push(move)
            record = book.preferred_position(board)
            if record is not None:
                matches.append(OpeningMatch(ply, record, san, uci))
    except (AssertionError, ValueError):
        return _fallback(eco, opening_name)

    if not matches:
        return _fallback(eco, opening_name)
    deepest = max(matches, key=lambda item: item.game_ply)
    reentries = (
        tuple(match for match in matches if match.game_ply >= first_deviation[0])
        if first_deviation is not None
        else ()
    )
    return OpeningRecognitionResult(
        eco=deepest.record.eco,
        name=deepest.record.name,
        family=deepest.record.family,
        variation=deepest.record.variation,
        subvariation=deepest.record.subvariation,
        canonical_record_ply=deepest.record.ply,
        deepest_match_ply=deepest.game_ply,
        deepest_match_move_san=deepest.move_san,
        deepest_match_move_uci=deepest.move_uci,
        last_named_match_ply=matches[-1].game_ply,
        last_named_match_move_san=matches[-1].move_san,
        last_named_match_move_uci=matches[-1].move_uci,
        last_sequence_book_ply=last_sequence[0] if last_sequence else None,
        last_sequence_book_move_san=last_sequence[1] if last_sequence else None,
        last_sequence_book_move_uci=last_sequence[2] if last_sequence else None,
        first_deviation_ply=first_deviation[0] if first_deviation else None,
        first_deviation_move_san=first_deviation[1] if first_deviation else None,
        first_deviation_move_uci=first_deviation[2] if first_deviation else None,
        transposition_reentry=bool(reentries),
        first_reentry_ply=reentries[0].game_ply if reentries else None,
        matches=tuple(matches),
        source="position_book",
    )


def recognize_pgn(
    pgn: str,
    *,
    eco: str | None = None,
    opening_name: str | None = None,
) -> OpeningRecognitionResult:
    if not pgn or not pgn.strip():
        return _fallback(eco, opening_name)
    try:
        game = chess.pgn.read_game(StringIO(pgn))
    except (UnicodeError, ValueError):
        return _fallback(eco, opening_name)
    if game is None or game.errors:
        return _fallback(eco, opening_name)
    return recognize_moves(
        game.mainline_moves(),
        starting_board=game.board(),
        eco=eco or game.headers.get("ECO"),
        opening_name=opening_name or game.headers.get("Opening"),
    )
