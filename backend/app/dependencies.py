from collections.abc import Callable, Generator

from fastapi import BackgroundTasks, Depends
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.database import get_db, get_engine
from app.services.chesscom_client import ChessComClient
from app.services.stockfish_service import StockfishService
from app.queues.factory import create_analysis_queue


StockfishFactory = Callable[[], StockfishService]


def get_database_engine() -> Engine:
    return get_engine()


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


def get_analysis_queue(
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings_dependency),
    stockfish_factory: StockfishFactory = Depends(get_stockfish_factory),
    session: Session = Depends(get_database_session),
):
    session_factory = sessionmaker(
        bind=session.get_bind(), autoflush=False, expire_on_commit=False
    )
    return create_analysis_queue(
        settings,
        background_tasks=background_tasks,
        stockfish_factory=stockfish_factory,
        session_factory=session_factory,
    )
