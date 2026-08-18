from importlib.util import module_from_spec, spec_from_file_location

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.config import BACKEND_DIR


def config_for(url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["database_url"] = url
    return config


def test_initial_migration_imports() -> None:
    path = BACKEND_DIR / "alembic/versions/0001_initial_schema.py"
    spec = spec_from_file_location("initial_migration", path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "0001_initial_schema"


def test_upgrade_downgrade_upgrade_on_temporary_sqlite(tmp_path) -> None:
    path = tmp_path / "migration.db"
    url = f"sqlite+pysqlite:///{path}"
    config = config_for(url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    assert set(inspect(engine).get_table_names()) == {"games", "move_analysis", "app_settings", "alembic_version"}
    assert "phase" in {column["name"] for column in inspect(engine).get_columns("move_analysis")}
    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    command.upgrade(config, "head")
    assert {"games", "move_analysis", "app_settings"}.issubset(inspect(engine).get_table_names())
    engine.dispose()
