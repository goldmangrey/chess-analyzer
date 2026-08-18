from io import StringIO

import chess.pgn

from app.services.opening_resolver import resolve_opening


def moves(fragment: str):
    game = chess.pgn.read_game(StringIO(fragment))
    assert game is not None
    return tuple(game.mainline_moves())


def test_known_caro_kann_uses_deepest_local_line() -> None:
    opening = resolve_opening(moves("1. e4 c6 2. d4 d5 3. exd5 cxd5"), eco="B13")

    assert opening.eco == "B13"
    assert opening.name == "Caro-Kann Defense: Exchange Variation"
    assert opening.family == "Caro-Kann Defense"
    assert opening.variation == "Exchange Variation"
    assert (opening.source, opening.confidence) == ("local_database", "high")


def test_known_grob_line_is_specific_and_deterministic() -> None:
    line = moves("1. g4 d5 2. Bg2")
    first = resolve_opening(line, eco="A00")
    second = resolve_opening(line, eco="A00")

    assert first == second
    assert first.name == "Grob Opening: Grob Gambit"


def test_unknown_line_keeps_reliable_eco_without_inventing_name() -> None:
    opening = resolve_opening((), eco="A00")

    assert opening.eco == "A00"
    assert opening.name is None
    assert opening.source == "eco_only"


def test_missing_or_malformed_metadata_is_graceful() -> None:
    assert resolve_opening((), eco="bad", eco_url="not a url").name is None
    assert resolve_opening(()).eco is None


def test_chesscom_url_fallback_uses_canonical_database_name() -> None:
    opening = resolve_opening(
        (),
        eco="A00",
        eco_url="https://www.chess.com/openings/Grob-Opening-Grob-Gambit-with-2-Bg2",
    )

    assert opening.name == "Grob Opening: Grob Gambit"
    assert opening.source == "provider_metadata"


def test_standard_opening_header_is_provider_agnostic_fallback() -> None:
    opening = resolve_opening((), eco="C20", opening_name="King's Pawn Game")

    assert opening.name == "King's Pawn Game"
    assert opening.source == "pgn_header"
