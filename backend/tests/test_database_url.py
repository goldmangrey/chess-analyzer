import pytest

from app.database_url import (
    UnsupportedDatabaseError,
    database_backend,
    normalize_database_url,
    safe_database_description,
)


@pytest.mark.parametrize("url", ["sqlite:///:memory:", "sqlite+pysqlite:///:memory:"])
def test_sqlite_urls_are_recognized(url: str) -> None:
    assert database_backend(url) == "sqlite"
    assert normalize_database_url(url) == url


def test_relative_sqlite_url_is_preserved() -> None:
    assert normalize_database_url("sqlite:///./data/chess.db") == "sqlite:///./data/chess.db"


@pytest.mark.parametrize("prefix", ["postgres://", "postgresql://"])
def test_legacy_postgres_urls_use_psycopg_and_preserve_query(prefix: str) -> None:
    normalized = normalize_database_url(f"{prefix}user:secret@db:5432/chess?sslmode=require")
    assert normalized == "postgresql+psycopg://user:secret@db:5432/chess?sslmode=require"
    assert "secret" not in safe_database_description(normalized)


def test_psycopg_url_is_unchanged_and_unknown_backend_rejected() -> None:
    url = "postgresql+psycopg://user:secret@db/chess"
    assert normalize_database_url(url) == url
    with pytest.raises(UnsupportedDatabaseError, match="Unsupported database backend"):
        normalize_database_url("mysql://localhost/chess")
