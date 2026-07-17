from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from app.config import BACKEND_DIR, get_settings
from app.database_url import database_backend, resolve_database_url, safe_database_description


def main() -> int:
    settings = get_settings()
    normalized = resolve_database_url(settings.database_url)
    print(f"Backend: {database_backend(normalized)}")
    print(f"Database: {safe_database_description(normalized)}")
    engine = create_engine(normalized)
    try:
        tables = set(inspect(engine).get_table_names())
        print(f"Tables: {', '.join(sorted(tables)) or 'none'}")
    finally:
        engine.dispose()
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    print(f"Alembic head: {ScriptDirectory.from_config(config).get_current_head()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
