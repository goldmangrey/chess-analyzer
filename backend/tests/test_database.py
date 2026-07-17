from pathlib import Path

from sqlalchemy import Engine, inspect, text

from app.config import BACKEND_DIR
from app.database_url import normalize_database_url, resolve_database_url


def test_sqlite_foreign_keys_are_enabled(test_engine: Engine) -> None:
    with test_engine.connect() as connection:
        enabled = connection.scalar(text("PRAGMA foreign_keys"))

    assert enabled == 1


def test_init_db_creates_only_expected_tables(test_engine: Engine) -> None:
    table_names = set(inspect(test_engine).get_table_names())

    assert table_names == {"games", "move_analysis", "app_settings"}


def test_relative_sqlite_path_is_resolved_from_backend() -> None:
    normalized = resolve_database_url("sqlite:///./data/chess.db")

    assert normalized == f"sqlite:///{BACKEND_DIR / 'data/chess.db'}"


def test_memory_and_absolute_sqlite_urls_are_preserved(tmp_path: Path) -> None:
    absolute_url = f"sqlite:///{tmp_path / 'absolute.db'}"

    assert normalize_database_url("sqlite:///:memory:") == "sqlite:///:memory:"
    assert normalize_database_url(absolute_url) == absolute_url
