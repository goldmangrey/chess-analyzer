from pathlib import Path
import os

from sqlalchemy import Engine, inspect
from sqlalchemy.engine import make_url

from app.config import BACKEND_DIR, Settings
from app.database import ALEMBIC_HEAD
from app.database_url import database_backend, resolve_database_url
from app.schemas import (
    ChessComStatus,
    DatabaseStatus,
    StockfishStatus,
    SystemStatusResponse,
)


REQUIRED_TABLES = {"games", "move_analysis", "app_settings"}


def _safe_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BACKEND_DIR))
    except ValueError:
        return str(path)


def get_system_status(settings: Settings, engine: Engine) -> SystemStatusResponse:
    database_url = make_url(resolve_database_url(settings.database_url))
    backend = database_backend(settings.database_url)
    database_path = Path(database_url.database) if backend == "sqlite" and database_url.database else None
    parent = database_path.parent if database_path else None
    database_ready = False
    tables_ready = False
    migration_revision = None
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
            table_names = set(inspect(connection).get_table_names())
            if "alembic_version" in table_names:
                migration_revision = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
        tables_ready = REQUIRED_TABLES.issubset(table_names)
        revision_ready = settings.auto_create_schema or migration_revision == ALEMBIC_HEAD
        database_ready = tables_ready and revision_ready
    except Exception:
        database_ready = False

    configured_path = Path(settings.stockfish_path).expanduser()
    if not configured_path.is_absolute():
        configured_path = BACKEND_DIR / configured_path
    stockfish_file = configured_path.is_file()
    stockfish_executable = stockfish_file and os.access(configured_path, os.X_OK)

    database = DatabaseStatus(
        status="ready" if database_ready else "degraded",
        backend=backend,
        path=_safe_path(database_path) if database_path else None,
        writable=bool(parent and parent.exists() and os.access(parent, os.W_OK)) if backend == "sqlite" else True,
        tables_ready=tables_ready,
        schema_ready=tables_ready,
        migration_revision=migration_revision,
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
