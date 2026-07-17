import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.config import BACKEND_DIR, get_settings
from app.database import REQUIRED_TABLES
from app.database_url import database_backend, resolve_database_url


def inspect_existing_database(url: str) -> tuple[bool, str]:
    normalized = resolve_database_url(url)
    if database_backend(normalized) != "sqlite":
        return False, "Adoption is supported only for SQLite"
    engine = create_engine(normalized)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    if "alembic_version" in tables:
        return False, "Database is already managed by Alembic"
    if tables != REQUIRED_TABLES:
        return False, f"Unexpected schema: {sorted(tables)}"
    return True, "Schema matches games, move_analysis, and app_settings"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Adopt an existing create_all SQLite database")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    settings = get_settings()
    ok, message = inspect_existing_database(settings.database_url)
    print(message)
    if not ok:
        return 1
    print("Back up backend/data/chess.db before applying the stamp.")
    if not args.apply:
        print("Dry run only. Re-run with --apply to stamp 0001_initial_schema.")
        return 0
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    command.stamp(config, "head")
    print("Database stamped at Alembic head; application rows were not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
