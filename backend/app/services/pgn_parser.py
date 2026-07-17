from dataclasses import dataclass
from datetime import datetime, time, timezone
from io import StringIO

import chess
import chess.pgn

from app.models import Color, GameResult


class PgnParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedPgnMove:
    ply: int
    move_number: int
    player_color: Color
    fen_before: str
    played_move_uci: str
    played_move_san: str


@dataclass(frozen=True)
class ParsedPgnGame:
    external_id: str
    platform: str
    played_at: datetime | None
    white_username: str
    black_username: str
    white_rating: int | None
    black_rating: int | None
    user_color: Color
    result: GameResult
    time_control: str | None
    opening_code: str | None
    opening_name: str | None
    pgn: str
    moves: tuple[ParsedPgnMove, ...]


def _optional_header(headers: chess.pgn.Headers, name: str) -> str | None:
    value = headers.get(name, "").strip()
    return value if value and value != "?" else None


def _rating(headers: chess.pgn.Headers, name: str) -> int | None:
    value = _optional_header(headers, name)
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _parse_date(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    parts = value.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        return None
    try:
        candidate = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return None
    return candidate.year, candidate.month, candidate.day


def _played_at(headers: chess.pgn.Headers) -> datetime | None:
    date_parts = _parse_date(_optional_header(headers, "UTCDate"))
    if date_parts:
        time_value = _optional_header(headers, "UTCTime")
        try:
            parsed_time = time.fromisoformat(time_value) if time_value else time()
        except ValueError:
            parsed_time = time()
        return datetime(*date_parts, parsed_time.hour, parsed_time.minute, parsed_time.second, tzinfo=timezone.utc)

    date_parts = _parse_date(_optional_header(headers, "Date"))
    return datetime(*date_parts, tzinfo=timezone.utc) if date_parts else None


def _user_result(user_color: Color, result: str) -> GameResult:
    if result == "1/2-1/2":
        return GameResult.DRAW
    if result not in {"1-0", "0-1"}:
        raise PgnParseError(f"PGN result is not a completed game: {result!r}")
    white_won = result == "1-0"
    user_won = white_won == (user_color is Color.WHITE)
    return GameResult.WIN if user_won else GameResult.LOSS


def parse_pgn(
    pgn: str,
    username: str,
    external_id: str,
    platform: str = "chess.com",
) -> ParsedPgnGame:
    if not pgn or not pgn.strip():
        raise PgnParseError("PGN is empty")

    try:
        game = chess.pgn.read_game(StringIO(pgn))
    except (ValueError, UnicodeError) as error:
        raise PgnParseError(f"Unable to parse PGN: {error}") from error
    if game is None or game.errors:
        detail = str(game.errors[0]) if game and game.errors else "no game found"
        raise PgnParseError(f"Unable to parse PGN: {detail}")

    headers = game.headers
    white = _optional_header(headers, "White")
    black = _optional_header(headers, "Black")
    result_header = _optional_header(headers, "Result")
    if not white or not black or not result_header:
        raise PgnParseError("PGN requires White, Black, and Result headers")

    normalized_username = username.strip().casefold()
    matches_white = bool(normalized_username) and white.strip().casefold() == normalized_username
    matches_black = bool(normalized_username) and black.strip().casefold() == normalized_username
    if matches_white == matches_black:
        raise PgnParseError("Username must match exactly one PGN player")
    user_color = Color.WHITE if matches_white else Color.BLACK

    board = game.board()
    parsed_moves: list[ParsedPgnMove] = []
    try:
        for ply, move in enumerate(game.mainline_moves(), start=1):
            parsed_moves.append(
                ParsedPgnMove(
                    ply=ply,
                    move_number=board.fullmove_number,
                    player_color=Color.WHITE if board.turn == chess.WHITE else Color.BLACK,
                    fen_before=board.fen(),
                    played_move_uci=move.uci(),
                    played_move_san=board.san(move),
                )
            )
            board.push(move)
    except (ValueError, AssertionError) as error:
        raise PgnParseError(f"Unable to traverse PGN mainline: {error}") from error

    return ParsedPgnGame(
        external_id=external_id,
        platform=platform,
        played_at=_played_at(headers),
        white_username=white,
        black_username=black,
        white_rating=_rating(headers, "WhiteElo"),
        black_rating=_rating(headers, "BlackElo"),
        user_color=user_color,
        result=_user_result(user_color, result_header),
        time_control=_optional_header(headers, "TimeControl"),
        opening_code=_optional_header(headers, "ECO"),
        opening_name=_optional_header(headers, "Opening"),
        pgn=pgn,
        moves=tuple(parsed_moves),
    )
