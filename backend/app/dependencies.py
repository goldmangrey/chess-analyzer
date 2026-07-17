from collections.abc import Callable, Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.services.chesscom_client import ChessComClient
from app.services.stockfish_service import StockfishService


StockfishFactory = Callable[[], StockfishService]


def get_settings_dependency() -> Settings:
    return get_settings()


def get_database_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_chesscom_client(
    settings: Settings = Depends(get_settings_dependency),
) -> Generator[ChessComClient, None, None]:
    client = ChessComClient(settings.chesscom_user_agent)
    try:
        yield client
    finally:
        client.close()


def get_stockfish_factory(
    settings: Settings = Depends(get_settings_dependency),
) -> StockfishFactory:
    return lambda: StockfishService(
        settings.stockfish_path,
        settings.stockfish_move_time_ms,
        settings.stockfish_pv_length,
    )
