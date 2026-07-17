from collections.abc import Generator
from pathlib import Path
import logging

from sqlalchemy import Engine, MetaData, create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings, get_settings
from app.database_url import database_backend, normalize_database_url, resolve_database_url


logger = logging.getLogger(__name__)
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
REQUIRED_TABLES = {"games", "move_analysis", "app_settings"}
ALEMBIC_HEAD = "0001_initial_schema"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_database_engine(database_url: str, *, settings: Settings | None = None) -> Engine:
    normalized_url = resolve_database_url(database_url)
    backend = database_backend(normalized_url)
    active = settings or get_settings()
    engine_options = {"connect_args": {"check_same_thread": False, "timeout": 30}} if backend == "sqlite" else {
        "pool_pre_ping": True,
        "pool_size": active.db_pool_size,
        "max_overflow": active.db_max_overflow,
        "pool_timeout": active.db_pool_timeout,
        "pool_recycle": active.db_pool_recycle,
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


engine = create_database_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    database_session = SessionLocal()
    try:
        yield database_session
    finally:
        database_session.close()


def init_db(*, bind: Engine = engine, auto_create_schema: bool | None = None) -> None:
    from app import models  # noqa: F401

    enabled = get_settings().auto_create_schema if auto_create_schema is None else auto_create_schema
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
    with bind.connect() as connection:
        revision = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
    if revision != ALEMBIC_HEAD:
        raise RuntimeError("Database migration is not at head. Run alembic upgrade head")
