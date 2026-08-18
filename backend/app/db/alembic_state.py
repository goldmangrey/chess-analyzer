from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


BACKEND_DIR = Path(__file__).resolve().parents[2]
ALEMBIC_CONFIG_PATH = BACKEND_DIR / "alembic.ini"


def get_migration_heads() -> frozenset[str]:
    config = Config(str(ALEMBIC_CONFIG_PATH))
    scripts = ScriptDirectory.from_config(config)
    return frozenset(scripts.get_heads())


def get_migration_head() -> str:
    heads = get_migration_heads()
    if len(heads) != 1:
        rendered = ", ".join(sorted(heads)) or "none"
        raise RuntimeError(
            f"Alembic migration graph must have exactly one head; found: {rendered}"
        )
    return next(iter(heads))
