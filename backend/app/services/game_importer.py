from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AnalysisStatus
from app.repositories.games_repository import create_game, external_id_exists
from app.schemas import GameCreate
from app.services.chesscom_client import ChessComClient, ChessComGameRecord
from app.services.pgn_parser import PgnParseError, parse_pgn


@dataclass(frozen=True)
class ImportGamesResult:
    requested: int
    imported: int
    skipped_duplicates: int
    skipped_invalid: int
    examined: int
    imported_game_ids: tuple[int, ...]


def import_recent_games(
    session: Session,
    client: ChessComClient,
    username: str,
    limit: int,
) -> ImportGamesResult:
    """Prepare up to limit new games; the caller owns commit and rollback."""
    normalized_username = username.strip()
    if not normalized_username:
        raise ValueError("username must not be empty")
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")

    imported_ids: list[int] = []
    duplicates = invalid = examined = 0
    candidates = iter(client.iter_recent_games(normalized_username))
    while len(imported_ids) < limit:
        try:
            record = next(candidates)
        except StopIteration:
            break
        examined += 1
        if external_id_exists(session, record.external_id):
            duplicates += 1
            continue
        if not record.pgn:
            invalid += 1
            continue
        try:
            parsed = parse_pgn(record.pgn, normalized_username, record.external_id)
        except PgnParseError:
            invalid += 1
            continue

        data = GameCreate(
            external_id=parsed.external_id,
            platform="chess.com",
            played_at=parsed.played_at,
            white_username=parsed.white_username,
            black_username=parsed.black_username,
            white_rating=parsed.white_rating,
            black_rating=parsed.black_rating,
            user_color=parsed.user_color,
            result=parsed.result,
            time_control=parsed.time_control,
            opening_code=parsed.opening_code,
            opening_name=parsed.opening_name,
            pgn=parsed.pgn,
            analysis_status=AnalysisStatus.PENDING,
        )
        try:
            with session.begin_nested():
                game = create_game(session, data)
        except IntegrityError:
            duplicates += 1
            continue
        imported_ids.append(game.id)

    return ImportGamesResult(
        requested=limit,
        imported=len(imported_ids),
        skipped_duplicates=duplicates,
        skipped_invalid=invalid,
        examined=examined,
        imported_game_ids=tuple(imported_ids),
    )


def import_game_records(
    session: Session,
    records: Iterable[ChessComGameRecord],
    username: str,
    *,
    requested: int,
) -> ImportGamesResult:
    """Import a bounded record collection without committing or analyzing it."""
    normalized_username = username.strip()
    if not normalized_username:
        raise ValueError("username must not be empty")
    imported_ids: list[int] = []
    duplicates = invalid = examined = 0
    for record in records:
        examined += 1
        if external_id_exists(session, record.external_id):
            duplicates += 1
            continue
        if not record.pgn:
            invalid += 1
            continue
        try:
            parsed = parse_pgn(record.pgn, normalized_username, record.external_id)
        except PgnParseError:
            invalid += 1
            continue
        data = GameCreate(
            external_id=parsed.external_id,
            platform="chess.com",
            played_at=parsed.played_at,
            white_username=parsed.white_username,
            black_username=parsed.black_username,
            white_rating=parsed.white_rating,
            black_rating=parsed.black_rating,
            user_color=parsed.user_color,
            result=parsed.result,
            time_control=parsed.time_control,
            opening_code=parsed.opening_code,
            opening_name=parsed.opening_name,
            pgn=parsed.pgn,
            analysis_status=AnalysisStatus.PENDING,
        )
        try:
            with session.begin_nested():
                game = create_game(session, data)
        except IntegrityError:
            duplicates += 1
            continue
        imported_ids.append(game.id)
    return ImportGamesResult(requested, len(imported_ids), duplicates, invalid, examined, tuple(imported_ids))
