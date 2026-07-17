from sqlalchemy import inspect
import pytest

from app.config import Settings
from app.database import create_database_engine, init_db


def test_sqlite_engine_pragmas_and_auto_create_modes(tmp_path) -> None:
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'portable.db'}")
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar().lower() == "wal"
        init_db(bind=engine, auto_create_schema=True)
        assert set(inspect(engine).get_table_names()) == {"games", "move_analysis", "app_settings"}
    finally:
        engine.dispose()


def test_auto_create_false_validates_without_creating(tmp_path) -> None:
    engine = create_database_engine(f"sqlite+pysqlite:///{tmp_path / 'empty.db'}")
    try:
        with pytest.raises(RuntimeError, match="alembic upgrade head"):
            init_db(bind=engine, auto_create_schema=False)
        assert set(inspect(engine).get_table_names()) == set()
    finally:
        engine.dispose()


def test_postgresql_engine_options_do_not_include_sqlite_args(monkeypatch) -> None:
    captured = {}
    sentinel = object()
    monkeypatch.setattr("app.database.create_engine", lambda url, **options: captured.update(url=url, options=options) or sentinel)
    settings = Settings(_env_file=None, DB_POOL_SIZE=3, DB_MAX_OVERFLOW=2, DB_POOL_TIMEOUT=11, DB_POOL_RECYCLE=900)
    assert create_database_engine("postgresql://u:p@db/chess", settings=settings) is sentinel
    assert captured["url"].startswith("postgresql+psycopg://")
    assert captured["options"] == {"pool_pre_ping": True, "pool_size": 3, "max_overflow": 2, "pool_timeout": 11, "pool_recycle": 900}
