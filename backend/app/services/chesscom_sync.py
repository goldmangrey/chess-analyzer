from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import Settings
from app.repositories.games_repository import get_latest_game_by_ids
from app.schemas import SyncMode
from app.services.chesscom_client import ChessComClient, ChessComGameRecord
from app.services.game_importer import ImportGamesResult, import_game_records


@dataclass(frozen=True)
class SyncImportResult:
    result: ImportGamesResult
    latest_game_id: int | None


def _records_for_initial(
    client: ChessComClient, username: str, *, months: int, max_games: int
) -> list[ChessComGameRecord]:
    archives = client.get_archives(username)[:months]
    newest: list[ChessComGameRecord] = []
    for archive in archives:
        remaining = max_games - len(newest)
        if remaining <= 0:
            break
        newest.extend(client.get_archive_games(archive)[:remaining])
    return sorted(newest, key=lambda record: (record.end_time is not None, record.end_time or 0))


def _records_for_incremental(client: ChessComClient, username: str) -> list[ChessComGameRecord]:
    archives = client.get_archives(username)[:2]
    records = [record for archive in archives for record in client.get_archive_games(archive)]
    unique = {record.external_id: record for record in records}
    return sorted(unique.values(), key=lambda record: (record.end_time is not None, record.end_time or 0))


def synchronize_chesscom(
    session: Session,
    client: ChessComClient,
    username: str,
    mode: SyncMode,
    settings: Settings,
    *,
    initial_months: int | None = None,
) -> SyncImportResult:
    if mode is SyncMode.INITIAL:
        months = initial_months or settings.initial_sync_months
        records = _records_for_initial(
            client, username, months=months, max_games=settings.initial_sync_max_games
        )
        requested = settings.initial_sync_max_games
    else:
        records = _records_for_incremental(client, username)
        requested = len(records)
    result = import_game_records(session, records, username, requested=requested)
    latest = get_latest_game_by_ids(session, result.imported_game_ids)
    return SyncImportResult(result, latest.id if latest else None)
