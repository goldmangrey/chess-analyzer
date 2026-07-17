from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import BACKEND_DIR, get_settings


class Base(DeclarativeBase):
    pass


def normalize_database_url(
    database_url: str,
    *,
    base_dir: Path = BACKEND_DIR,
) -> str:
    url = make_url(database_url)
    database = url.database

    if (
        url.get_backend_name() == "sqlite"
        and database
        and database != ":memory:"
        and not database.startswith("file:")
        and not Path(database).is_absolute()
    ):
        absolute_database = (base_dir / database).resolve()
        url = url.set(database=str(absolute_database))

    return url.render_as_string(hide_password=False)


def create_database_engine(database_url: str) -> Engine:
    normalized_url = normalize_database_url(database_url)
    is_sqlite = make_url(normalized_url).get_backend_name() == "sqlite"
    engine_options = (
        {"connect_args": {"check_same_thread": False, "timeout": 30}} if is_sqlite else {}
    )
    database_engine = create_engine(normalized_url, **engine_options)

    if is_sqlite:

        @event.listens_for(database_engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            if make_url(normalized_url).database != ":memory:":
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


def init_db(*, bind: Engine = engine) -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=bind)
