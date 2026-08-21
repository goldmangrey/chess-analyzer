from datetime import datetime, timezone

import chess
import pytest

from app.models import Color, GameResult
from app.services.pgn_parser import PgnParseError, parse_pgn


def pgn_fixture(
    *,
    white: str = "Yeskendir",
    black: str = "Opponent",
    result: str = "1-0",
    extra: str = "",
    moves: str = "1. e4 e5 2. Nf3 Nc6",
) -> str:
    return f'''[Event "Test"]
[Site "Chess.com"]
[Date "2026.07.16"]
[Round "-"]
[White "{white}"]
[Black "{black}"]
[Result "{result}"]
{extra}
{moves} {result}
'''


@pytest.mark.parametrize(
    ("white", "black", "result", "expected_color", "expected_result"),
    [
        ("Yeskendir", "Opponent", "1-0", Color.WHITE, GameResult.WIN),
        ("Yeskendir", "Opponent", "0-1", Color.WHITE, GameResult.LOSS),
        ("Opponent", "Yeskendir", "0-1", Color.BLACK, GameResult.WIN),
        ("Opponent", "Yeskendir", "1-0", Color.BLACK, GameResult.LOSS),
        ("Yeskendir", "Opponent", "1/2-1/2", Color.WHITE, GameResult.DRAW),
    ],
)
def test_color_and_result_perspective(
    white: str,
    black: str,
    result: str,
    expected_color: Color,
    expected_result: GameResult,
) -> None:
    parsed = parse_pgn(pgn_fixture(white=white, black=black, result=result), "Yeskendir", "id")
    assert parsed.user_color is expected_color
    assert parsed.result is expected_result


def test_username_is_case_insensitive_and_original_names_are_preserved() -> None:
    parsed = parse_pgn(pgn_fixture(white="YeSkEnDiR"), " yeskendir ", "id")
    assert parsed.white_username == "YeSkEnDiR"


@pytest.mark.parametrize(
    "pgn",
    ["", pgn_fixture(white="Other"), pgn_fixture(result="*"), '[White "Yeskendir"]\n[Black "Opponent"]\n\n1. e4'],
)
def test_invalid_or_inapplicable_pgn_is_rejected(pgn: str) -> None:
    with pytest.raises(PgnParseError):
        parse_pgn(pgn, "Yeskendir", "id")


def test_metadata_parsing_and_optional_values() -> None:
    parsed = parse_pgn(
        pgn_fixture(
            extra='[UTCDate "2026.07.16"]\n[UTCTime "12:34:56"]\n[WhiteElo "1800"]\n[BlackElo "-"]\n[ECO "C20"]\n[Opening "King\'s Pawn Game"]\n[TimeControl "600+5"]'
        ),
        "Yeskendir",
        "id",
    )
    assert parsed.played_at == datetime(2026, 7, 16, 12, 34, 56, tzinfo=timezone.utc)
    assert parsed.white_rating == 1800
    assert parsed.black_rating is None
    assert (parsed.opening_code, parsed.opening_name) == ("C44", "King's Knight Opening: Normal Variation")
    assert parsed.time_control == "600+5"


def test_partial_date_and_missing_optional_headers() -> None:
    raw = pgn_fixture(extra='[UTCDate "2026.07.??"]\n[Date "????.??.??"]')
    parsed = parse_pgn(raw, "Yeskendir", "id")
    assert parsed.played_at is None
    assert parsed.white_rating is None
    assert parsed.opening_code == "C44"
    assert parsed.opening_name == "King's Knight Opening: Normal Variation"
    assert parsed.time_control is None


def test_opening_is_resolved_from_moves_without_opening_or_eco_url_headers() -> None:
    parsed = parse_pgn(
        pgn_fixture(extra='[ECO "B13"]', moves="1. e4 c6 2. d4 d5 3. exd5 cxd5"),
        "Yeskendir",
        "id",
    )
    assert (parsed.opening_code, parsed.opening_name) == (
        "B13",
        "Caro-Kann Defense: Exchange Variation",
    )


def test_position_recognition_recovers_b13_name_without_opening_header() -> None:
    parsed = parse_pgn(
        pgn_fixture(extra='[ECO "B13"]', moves="1. e4 c6 2. d4 d5 3. exd5 cxd5"),
        "Yeskendir",
        "b13-position",
    )
    assert (parsed.opening_code, parsed.opening_name) == (
        "B13",
        "Caro-Kann Defense: Exchange Variation",
    )


def test_chesscom_eco_url_is_only_a_canonicalized_fallback() -> None:
    parsed = parse_pgn(
        pgn_fixture(
            extra='[ECO "A00"]\n[ECOUrl "https://www.chess.com/openings/Grob-Opening-Grob-Gambit-with-2-Bg2"]',
            moves="",
        ),
        "Yeskendir",
        "id",
    )
    assert parsed.opening_name == "Grob Opening: Grob Gambit"


def test_mainline_moves_include_pre_move_position_san_uci_and_no_variation() -> None:
    parsed = parse_pgn(
        pgn_fixture(moves="1. e4 (1. d4 d5) e5 2. Nf3 Nc6"),
        "Yeskendir",
        "id",
    )
    assert len(parsed.moves) == 4
    assert [move.ply for move in parsed.moves] == [1, 2, 3, 4]
    assert [move.move_number for move in parsed.moves] == [1, 1, 2, 2]
    assert [move.player_color for move in parsed.moves] == [Color.WHITE, Color.BLACK, Color.WHITE, Color.BLACK]
    assert parsed.moves[0].fen_before == chess.Board().fen()
    assert (parsed.moves[0].played_move_uci, parsed.moves[0].played_move_san) == ("e2e4", "e4")
    assert all(move.played_move_uci != "d2d4" for move in parsed.moves)
