from pathlib import Path
from typing import Literal

from sqlalchemy.engine import make_url

DatabaseBackend = Literal["sqlite", "postgresql"]
BACKEND_DIR = Path(__file__).resolve().parent.parent


class UnsupportedDatabaseError(ValueError):
    pass


def database_backend(url: str) -> DatabaseBackend:
    driver = make_url(url).get_backend_name()
    if driver == "sqlite":
        return "sqlite"
    if driver in {"postgres", "postgresql"}:
        return "postgresql"
    raise UnsupportedDatabaseError(f"Unsupported database backend: {driver}")


def is_sqlite_url(url: str) -> bool:
    return database_backend(url) == "sqlite"


def is_postgresql_url(url: str) -> bool:
    return database_backend(url) == "postgresql"


def normalize_database_url(url: str) -> str:
    parsed = make_url(url)
    backend = database_backend(url)
    if backend == "postgresql" and parsed.drivername in {"postgres", "postgresql"}:
        parsed = parsed.set(drivername="postgresql+psycopg")
    return parsed.render_as_string(hide_password=False)


def resolve_database_url(url: str, *, base_dir: Path = BACKEND_DIR) -> str:
    parsed = make_url(normalize_database_url(url))
    backend = database_backend(url)
    if backend == "sqlite" and parsed.database and parsed.database != ":memory:" and not parsed.database.startswith("file:") and not Path(parsed.database).is_absolute():
        parsed = parsed.set(database=str((base_dir / parsed.database).resolve()))
    return parsed.render_as_string(hide_password=False)


def safe_database_description(url: str) -> str:
    parsed = make_url(resolve_database_url(url))
    if database_backend(url) == "sqlite":
        return f"sqlite:{parsed.database}"
    return f"postgresql://{parsed.host or 'localhost'}:{parsed.port or 5432}/{parsed.database or ''}"
