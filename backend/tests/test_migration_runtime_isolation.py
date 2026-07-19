from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect, make_url

from app.config import Settings
from app.database import (
    create_database_engine,
    dispose_database_engine,
    get_engine,
    get_session_factory,
)
from app.db.base import Base
from app.db.migration_url import build_migration_database_url, load_database_environment


BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_neutral_base_import_has_no_runtime_settings_side_effect() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from app.db.base import Base; "
            "assert 'app.config' not in sys.modules; print(Base.__name__)",
        ],
        cwd=BACKEND_DIR,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Base"


def test_database_module_import_does_not_validate_application_settings() -> None:
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "production",
            "DATABASE_HOST": "/cloudsql/test:region:instance",
            "DATABASE_NAME": "chess_ai_teacher",
            "DATABASE_USER": "chess_app",
            "DATABASE_PASSWORD": "test-password",
        }
    )
    for name in (
        "DATABASE_URL",
        "ANALYSIS_QUEUE_BACKEND",
        "ANALYSIS_WORKER_URL",
        "CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL",
    ):
        env.pop(name, None)
    result = subprocess.run(
        [sys.executable, "-c", "import app.database; print('imported')"],
        cwd=BACKEND_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "imported"


def test_cloud_sql_migration_url_uses_socket_and_encodes_password() -> None:
    password = "p@ss:/?#[]"
    rendered = build_migration_database_url(
        {
            "DATABASE_URL": "",
            "DATABASE_HOST": "/cloudsql/project:region:instance",
            "DATABASE_NAME": "chess_ai_teacher",
            "DATABASE_USER": "chess_app",
            "DATABASE_PASSWORD": password,
            "DATABASE_PORT": "",
        }
    )
    parsed = make_url(rendered)
    assert parsed.drivername == "postgresql+psycopg"
    assert parsed.host is None
    assert parsed.query["host"] == "/cloudsql/project:region:instance"
    assert parsed.password == password
    assert "%40" in rendered and "%2F" in rendered


def test_explicit_database_url_has_priority() -> None:
    explicit = "sqlite+pysqlite:///:memory:"
    assert build_migration_database_url(
        {
            "DATABASE_URL": explicit,
            "DATABASE_HOST": "/cloudsql/ignored",
            "DATABASE_NAME": "ignored",
            "DATABASE_USER": "ignored",
            "DATABASE_PASSWORD": "ignored",
        }
    ) == explicit


def test_process_components_outrank_env_file_database_url(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=sqlite:///from-file.db\n", encoding="utf-8")
    values = load_database_environment(
        {
            "DATABASE_HOST": "/cloudsql/project:region:instance",
            "DATABASE_NAME": "chess_ai_teacher",
            "DATABASE_USER": "chess_app",
            "DATABASE_PASSWORD": "test-password",
        },
        env_file=env_file,
    )
    assert values["DATABASE_URL"] == ""
    assert build_migration_database_url(values).startswith("postgresql+psycopg://")


def test_alembic_offline_needs_only_production_database_components() -> None:
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "production",
            "DATABASE_HOST": "/cloudsql/test-project:europe-west1:test-instance",
            "DATABASE_NAME": "chess_ai_teacher",
            "DATABASE_USER": "chess_app",
            "DATABASE_PASSWORD": "test-password",
        }
    )
    for name in (
        "DATABASE_URL",
        "ANALYSIS_QUEUE_BACKEND",
        "ANALYSIS_WORKER_URL",
        "CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL",
        "STOCKFISH_PATH",
        "CHESSCOM_USER_AGENT",
        "ANALYSIS_WORKER_SHARED_SECRET",
    ):
        env.pop(name, None)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=BACKEND_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "CREATE TABLE games" in result.stdout
    assert "PostgresqlImpl" in result.stderr
    assert "ANALYSIS_QUEUE_BACKEND" not in result.stderr


def test_metadata_and_runtime_singletons(tmp_path: Path) -> None:
    from app import models  # noqa: F401

    assert set(Base.metadata.tables) == {"games", "move_analysis", "app_settings"}
    settings = Settings(
        _env_file=None,
        DATABASE_URL=f"sqlite+pysqlite:///{tmp_path / 'runtime.db'}",
    )
    dispose_database_engine()
    first = get_engine(settings)
    second = get_engine(settings)
    first_factory = get_session_factory(settings)
    second_factory = get_session_factory(settings)
    try:
        Base.metadata.create_all(first)
        assert first is second
        assert first_factory is second_factory
        assert set(inspect(first).get_table_names()) == {
            "games",
            "move_analysis",
            "app_settings",
        }
    finally:
        dispose_database_engine()


def test_migration_job_keeps_database_only_environment() -> None:
    script = (BACKEND_DIR.parent / "scripts/gcp/deploy-migration-job.sh").read_text(
        encoding="utf-8"
    )
    assert "DATABASE_PASSWORD=DATABASE_PASSWORD:latest" in script
    for unrelated in (
        "ANALYSIS_QUEUE_BACKEND",
        "ANALYSIS_WORKER_URL",
        "CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL",
        "STOCKFISH_PATH",
        "CHESSCOM_USER_AGENT",
        "ANALYSIS_WORKER_SHARED_SECRET",
    ):
        assert unrelated not in script

    alembic_environment = (BACKEND_DIR / "alembic/env.py").read_text(encoding="utf-8")
    assert "get_settings" not in alembic_environment
    assert "from app.database import" not in alembic_environment
    assert "from app.config import" not in alembic_environment
