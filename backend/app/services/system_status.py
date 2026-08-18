from pathlib import Path
import os
from urllib.parse import urlsplit

from sqlalchemy import Engine, inspect
from sqlalchemy.engine import make_url

from app.config import BACKEND_DIR, Settings
from app.database_url import database_backend, resolve_database_url
from app.db.alembic_state import get_migration_head
from app.schemas import (
    ChessComStatus,
    AnalysisQueueStatus,
    ScheduledSyncStatus,
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
        revision_ready = settings.auto_create_schema or migration_revision == get_migration_head()
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
    cloud = settings.analysis_queue_backend.value == "cloud_tasks"
    queue_configured = not cloud or all((
        settings.gcp_project_id, settings.gcp_region, settings.cloud_tasks_queue,
        settings.analysis_worker_url, settings.cloud_tasks_service_account_email,
    ))
    worker_host = urlsplit(settings.analysis_worker_url).netloc or None
    analysis_queue = AnalysisQueueStatus(
        backend=settings.analysis_queue_backend.value,
        status="ready" if queue_configured else "degraded",
        configured=queue_configured,
        queue_name=settings.cloud_tasks_queue if cloud else None,
        worker_url_host=worker_host if cloud else None,
    )
    scheduled_ready = (
        settings.scheduled_sync_enabled
        and settings.analysis_queue_backend.value == "cloud_tasks"
        and bool(settings.scheduled_sync_shared_secret)
    )
    scheduled_sync = ScheduledSyncStatus(
        enabled=settings.scheduled_sync_enabled,
        mode="server" if settings.scheduled_sync_enabled else "browser",
        status=("ready" if scheduled_ready else "degraded") if settings.scheduled_sync_enabled else "disabled",
    )
    ready = (
        database.status == "ready"
        and stockfish.status == "ready"
        and chesscom.configured
        and chesscom.user_agent_configured
        and analysis_queue.status == "ready"
        and (not scheduled_sync.enabled or scheduled_sync.status == "ready")
    )
    return SystemStatusResponse(
        status="ready" if ready else "degraded",
        backend="ready",
        app_environment=settings.app_env,
        database=database,
        stockfish=stockfish,
        chesscom=chesscom,
        analysis_queue=analysis_queue,
        scheduled_sync=scheduled_sync,
    )
