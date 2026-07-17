from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import compose_cloud_sql_database_url, get_settings
from app.database import Base
from app.database_url import database_backend, resolve_database_url
from app import models  # noqa: F401


config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)
configured_url = config.attributes.get("database_url") or os.getenv("DATABASE_URL", "").strip()
if not configured_url and os.getenv("DATABASE_HOST", "").strip():
    configured_url = compose_cloud_sql_database_url(
        host=os.environ["DATABASE_HOST"],
        port=int(os.getenv("DATABASE_PORT", "5432")),
        name=os.environ["DATABASE_NAME"],
        user=os.environ["DATABASE_USER"],
        password=os.environ["DATABASE_PASSWORD"],
    )
if not configured_url:
    configured_url = get_settings().database_url
normalized_url = resolve_database_url(configured_url)
config.set_main_option("sqlalchemy.url", normalized_url.replace("%", "%%"))
target_metadata = Base.metadata


def migration_options() -> dict:
    return {
        "target_metadata": target_metadata,
        "compare_type": True,
        "render_as_batch": database_backend(normalized_url) == "sqlite",
    }


def run_migrations_offline() -> None:
    context.configure(url=normalized_url, literal_binds=True, dialect_opts={"paramstyle": "named"}, **migration_options())
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, **migration_options())
        with context.begin_transaction():
            context.run_migrations()


run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
