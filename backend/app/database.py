from collections.abc import Generator
import logging
import threading

from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.database_url import database_backend, resolve_database_url
from app.db.alembic_state import get_migration_head
from app.db.base import Base


logger = logging.getLogger(__name__)
REQUIRED_TABLES = {"games", "move_analysis", "app_settings"}


def create_database_engine(database_url: str, *, settings: Settings | None = None) -> Engine:
    normalized_url = resolve_database_url(database_url)
    backend = database_backend(normalized_url)
    active = settings
    engine_options = {"connect_args": {"check_same_thread": False, "timeout": 30}} if backend == "sqlite" else {
        "pool_pre_ping": True,
        "pool_size": active.db_pool_size if active else 5,
        "max_overflow": active.db_max_overflow if active else 5,
        "pool_timeout": active.db_pool_timeout if active else 30,
        "pool_recycle": active.db_pool_recycle if active else 1800,
    }
    database_engine = create_engine(normalized_url, **engine_options)

    if backend == "sqlite":

        @event.listens_for(database_engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            if database_engine.url.database != ":memory:":
                cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()
            dbapi_connection.isolation_level = None

        @event.listens_for(database_engine, "begin")
        def begin_sqlite_transaction(connection) -> None:
            connection.exec_driver_sql("BEGIN")

    return database_engine


_runtime_lock = threading.RLock()
_runtime_engine: Engine | None = None
_runtime_session_factory: sessionmaker[Session] | None = None


def create_session_factory(bind: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=bind, autoflush=False, expire_on_commit=False)


def get_engine(settings: Settings | None = None) -> Engine:
    global _runtime_engine
    if _runtime_engine is None:
        with _runtime_lock:
            if _runtime_engine is None:
                active = settings or get_settings()
                _runtime_engine = create_database_engine(
                    active.database_url, settings=active
                )
    return _runtime_engine


def get_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    global _runtime_session_factory
    if _runtime_session_factory is None:
        with _runtime_lock:
            if _runtime_session_factory is None:
                _runtime_session_factory = create_session_factory(get_engine(settings))
    return _runtime_session_factory


def dispose_database_engine() -> None:
    global _runtime_engine, _runtime_session_factory
    with _runtime_lock:
        if _runtime_engine is not None:
            _runtime_engine.dispose()
        _runtime_engine = None
        _runtime_session_factory = None


def get_db() -> Generator[Session, None, None]:
    database_session = get_session_factory()()
    try:
        yield database_session
    finally:
        database_session.close()


def init_db(
    *,
    bind: Engine | None = None,
    auto_create_schema: bool | None = None,
    settings: Settings | None = None,
) -> None:
    from app import models  # noqa: F401

    active = settings
    if bind is None:
        active = active or get_settings()
        bind = get_engine(active)
    enabled = (active or get_settings()).auto_create_schema if auto_create_schema is None else auto_create_schema
    backend = database_backend(str(bind.url))
    logger.info("Initializing database backend=%s auto_create_schema=%s", backend, enabled)
    if enabled:
        Base.metadata.create_all(bind=bind)
        return
    with bind.connect():
        pass
    table_names = set(inspect(bind).get_table_names())
    missing = REQUIRED_TABLES - table_names
    if missing:
        raise RuntimeError("Database schema is not ready. Run alembic upgrade head")
    if "alembic_version" not in table_names:
        raise RuntimeError("Database is not stamped. Run alembic stamp head after schema verification")
    expected_revision = get_migration_head()
    with bind.connect() as connection:
        revisions = frozenset(
            connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalars()
        )
    if revisions != {expected_revision}:
        raise RuntimeError("Database migration is not at head. Run alembic upgrade head")
