from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import URL


DEFAULT_SQLITE_URL = "sqlite:///./data/chess.db"
DB_ENVIRONMENT_NAMES = (
    "DATABASE_URL",
    "DATABASE_HOST",
    "DATABASE_PORT",
    "DATABASE_NAME",
    "DATABASE_USER",
    "DATABASE_PASSWORD",
)


def load_database_environment(
    environ: Mapping[str, str] | None = None,
    *,
    env_file: Path | None = None,
) -> dict[str, str]:
    """Load database-only config; process environment wins over .env."""

    process = os.environ if environ is None else environ
    file_values = dotenv_values(env_file) if env_file and env_file.exists() else {}
    values = {
        name: str(process[name] if name in process else file_values.get(name) or "").strip()
        for name in DB_ENVIRONMENT_NAMES
    }
    component_names = DB_ENVIRONMENT_NAMES[1:]
    if "DATABASE_URL" not in process and any(name in process for name in component_names):
        # Explicit process-level Cloud SQL components outrank a local .env URL.
        values["DATABASE_URL"] = ""
    return values


def build_migration_database_url(values: Mapping[str, str]) -> str:
    explicit = values.get("DATABASE_URL", "").strip()
    if explicit:
        return explicit

    host = values.get("DATABASE_HOST", "").strip()
    name = values.get("DATABASE_NAME", "").strip()
    user = values.get("DATABASE_USER", "").strip()
    password = values.get("DATABASE_PASSWORD", "")
    components = (host, name, user, password)
    if not any(components):
        return DEFAULT_SQLITE_URL
    if not all(components):
        raise ValueError(
            "DATABASE_HOST, DATABASE_NAME, DATABASE_USER and DATABASE_PASSWORD "
            "must be set together for migrations"
        )

    port_text = values.get("DATABASE_PORT", "").strip()
    port = int(port_text) if port_text else 5432
    if host.startswith("/"):
        url = URL.create(
            "postgresql+psycopg",
            username=user,
            password=password,
            database=name,
            query={"host": host},
        )
    else:
        url = URL.create(
            "postgresql+psycopg",
            username=user,
            password=password,
            host=host,
            port=port,
            database=name,
        )
    return url.render_as_string(hide_password=False)
