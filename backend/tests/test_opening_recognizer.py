from io import StringIO
from pathlib import Path

import chess
import chess.pgn
import pytest

from app.services.opening_book import load_opening_book
from app.services.opening_recognizer import recognize_moves, recognize_pgn
from app.services.opening_resolver import resolve_opening


def _game(fragment: str) -> chess.pgn.Game:
    game = chess.pgn.read_game(StringIO(fragment))
    assert game is not None and not game.errors
    return game


def _recognize(fragment: str):
    game = _game(fragment)
    return recognize_moves(game.mainline_moves(), starting_board=game.board())


def test_empty_and_malformed_games_fail_closed():
    assert recognize_pgn("").name is None
    assert recognize_pgn("not valid pgn").name is None


@pytest.mark.parametrize(
    ("line", "name"),
    [
        ("1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5", "Italian Game: Giuoco Piano"),
        ("1. e4 e5 2. Nf3 Nc6 3. Bb5", "Ruy Lopez"),
        ("1. e4 c5", "Sicilian Defense"),
        ("1. e4 e6", "French Defense"),
        ("1. e4 c6", "Caro-Kann Defense"),
        ("1. d4 d5 2. c4", "Queen's Gambit"),
        ("1. d4 Nf6 2. c4 g6 3. Nf3 Bg7 4. g3", "King's Indian Defense: Fianchetto Variation"),
        ("1. c4", "English Opening"),
    ],
)
def test_standard_opening_families_use_deepest_exact_position(line, name):
    assert _recognize(line).name == name


def test_deep_variation_exposes_structured_name_and_actual_move():
    result = _recognize(
        "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be3"
    )
    assert result.name == "Sicilian Defense: Najdorf Variation, English Attack"
    assert result.family == "Sicilian Defense"
    assert result.variation == "Najdorf Variation"
    assert result.subvariation == "English Attack"
    assert result.deepest_match_ply == 11
    assert (result.deepest_match_move_san, result.deepest_match_move_uci) == (
        "Be3", "c1e3"
    )


def test_game_ply_is_not_canonical_record_depth_after_delayed_transposition():
    result = _recognize(
        "1. Nf3 Nf6 2. Ng1 Ng8 3. Nf3 Nf6 4. c4 e6 5. d4 b6"
    )
    assert result.name == "Queen's Indian Defense"
    assert result.deepest_match_ply == 10
    assert result.canonical_record_ply == 6
    assert result.deepest_match_move_san == "b6"
    assert result.deepest_match_move_uci == "b7b6"


def test_match_history_is_ordered_and_deepest_match_wins():
    result = _recognize("1. e4 c6 2. d4 d5 3. exd5 cxd5")
    assert result.name == "Caro-Kann Defense: Exchange Variation"
    assert tuple(match.game_ply for match in result.matches) == tuple(
        sorted(match.game_ply for match in result.matches)
    )
    assert result.matches[-1].record.name == result.name


def test_canonical_line_has_no_deviation_and_tracks_sequence_book_move():
    result = _recognize("1. e4 c6 2. d4 d5 3. exd5 cxd5")
    assert result.first_deviation_ply is None
    assert result.last_sequence_book_ply == 6
    assert result.last_sequence_book_move_san == "cxd5"


def test_first_deviation_on_black_move_is_exact_and_preserved():
    result = _recognize("1. e4 c6 2. d4 d5 3. Nc3 h6")
    assert result.first_deviation_ply == 6
    assert result.first_deviation_move_san == "h6"
    assert result.first_deviation_move_uci == "h7h6"
    assert result.last_sequence_book_ply == 5
    assert result.transposition_reentry is False


def test_transposition_reentry_preserves_deviation_and_position_identity():
    canonical = _recognize("1. d4 Nf6 2. c4 e6 3. Nf3 b6")
    transposed = _recognize("1. Nf3 Nf6 2. c4 e6 3. d4 b6")
    assert canonical.name == transposed.name == "Queen's Indian Defense"
    assert transposed.first_deviation_ply == 4
    assert transposed.transposition_reentry is True
    assert transposed.first_reentry_ply == 5
    assert transposed.deepest_match_ply == 6
    assert transposed.deepest_match_move_san == "b6"


def test_recognition_is_deterministic_and_reuses_cached_book():
    game = _game("1. e4 e5 2. Nf3 Nc6 3. Bb5")
    first = recognize_moves(game.mainline_moves())
    second = recognize_moves(game.mainline_moves())
    assert first == second
    assert load_opening_book() is load_opening_book()


def test_eco_and_explicit_header_are_safe_fallbacks_without_false_variation():
    eco_only = recognize_moves((), eco="B13")
    assert (eco_only.eco, eco_only.name, eco_only.variation, eco_only.source) == (
        "B13", None, None, "eco_only"
    )
    header = recognize_moves((), eco="B13", opening_name="Caro-Kann Defense")
    assert (header.eco, header.name, header.source) == (
        "B13", "Caro-Kann Defense", "pgn_header"
    )


def test_position_book_has_precedence_over_conflicting_headers():
    game = _game("1. e4 c6")
    result = recognize_moves(
        game.mainline_moves(), eco="A00", opening_name="Explicit Wrong Header"
    )
    assert (result.eco, result.name, result.source) == (
        "B10", "Caro-Kann Defense", "position_book"
    )


def test_nonstandard_starting_position_does_not_use_standard_book():
    game = _game('[SetUp "1"]\n[FEN "8/8/8/8/8/8/K6k/8 w - - 0 1"]\n\n*')
    result = recognize_moves(game.mainline_moves(), starting_board=game.board())
    assert result.name is None and result.matches == ()


def test_partial_legal_game_can_return_only_the_position_it_reached():
    result = recognize_pgn("1. e4 *")
    assert result.name == "King's Pawn Game"
    assert result.deepest_match_ply == 1


def test_illegal_move_stream_fails_closed_to_metadata():
    result = recognize_moves(("e2e5",), eco="B13")
    assert result.name is None and result.eco == "B13"


def test_b13_position_recovers_name_but_unknown_position_keeps_eco_only():
    known = _game("1. e4 c6 2. d4 d5 3. exd5 cxd5")
    resolved = resolve_opening(known.mainline_moves(), eco="B13")
    assert resolved.name == "Caro-Kann Defense: Exchange Variation"
    unknown = resolve_opening((), eco="B13")
    assert unknown.eco == "B13" and unknown.name is None


def test_runtime_recognizer_has_no_network_or_engine_dependency():
    source = Path(__import__("app.services.opening_recognizer", fromlist=["x"]).__file__).read_text()
    assert "Stockfish" not in source
    assert "urllib" not in source and "requests" not in source


def test_prefix_index_is_nonempty_and_compact_relative_to_source_expansion():
    book = load_opening_book()
    assert book.sequence_prefix_count > book.record_count
    assert book.sequence_prefix_count < book.record_count * 10
