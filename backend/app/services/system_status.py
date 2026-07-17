from pathlib import Path
import os

from sqlalchemy import Engine, inspect
from sqlalchemy.engine import make_url

from app.config import BACKEND_DIR, Settings
from app.database import normalize_database_url
from app.schemas import (
    ChessComStatus,
    DatabaseStatus,
    StockfishStatus,
    SystemStatusResponse,
)


REQUIRED_TABLES = {"games", "move_analysis"}


def _safe_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BACKEND_DIR))
    except ValueError:
        return str(path)


def get_system_status(settings: Settings, engine: Engine) -> SystemStatusResponse:
    database_url = make_url(normalize_database_url(settings.database_url))
    database_path = Path(database_url.database) if database_url.database else BACKEND_DIR
    parent = database_path.parent
    database_ready = False
    tables_ready = False
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        tables_ready = REQUIRED_TABLES.issubset(set(inspect(engine).get_table_names()))
        database_ready = tables_ready
    except Exception:
        database_ready = False

    configured_path = Path(settings.stockfish_path).expanduser()
    if not configured_path.is_absolute():
        configured_path = BACKEND_DIR / configured_path
    stockfish_file = configured_path.is_file()
    stockfish_executable = stockfish_file and os.access(configured_path, os.X_OK)

    database = DatabaseStatus(
        status="ready" if database_ready else "unavailable",
        path=_safe_path(database_path),
        writable=parent.exists() and os.access(parent, os.W_OK),
        tables_ready=tables_ready,
    )
    stockfish = StockfishStatus(
        status="ready" if stockfish_executable else "unavailable",
        path=_safe_path(configured_path),
        executable=stockfish_executable,
    )
    chesscom = ChessComStatus(
        configured=bool(settings.chess_username.strip()),
        user_agent_configured=bool(settings.chesscom_user_agent.strip()),
    )
    ready = (
        database.status == "ready"
        and stockfish.status == "ready"
        and chesscom.configured
        and chesscom.user_agent_configured
    )
    return SystemStatusResponse(
        status="ready" if ready else "degraded",
        backend="ready",
        database=database,
        stockfish=stockfish,
        chesscom=chesscom,
    )
