import pytest
from pydantic import ValidationError
from pathlib import Path

from app.config import AnalysisQueueBackend, Settings
from app.services.system_status import get_system_status


BASE = dict(
    APP_ENV="production", AUTO_CREATE_SCHEMA=False,
    ANALYSIS_QUEUE_BACKEND="cloud_tasks", GCP_PROJECT_ID="project",
    ANALYSIS_WORKER_URL="https://worker.example",
    CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL="tasks@example.test",
    DATABASE_URL="postgresql+psycopg://user:password@host/database",
)


def test_valid_production_runtime_and_worker_normalization():
    settings = Settings(_env_file=None, **BASE)
    assert settings.analysis_queue_backend is AnalysisQueueBackend.CLOUD_TASKS
    assert settings.analysis_worker_audience == "https://worker.example"


@pytest.mark.parametrize("override", [
    {"ANALYSIS_QUEUE_BACKEND": "local"},
    {"AUTO_CREATE_SCHEMA": True},
    {"DATABASE_URL": "sqlite:///cloud.db"},
])
def test_unsafe_production_configuration_rejected(override):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **(BASE | override))


def test_secret_not_in_repr():
    settings = Settings(_env_file=None, DATABASE_PASSWORD="do-not-print", DATABASE_HOST="host", DATABASE_NAME="db", DATABASE_USER="user")
    assert "do-not-print" not in repr(settings)


def test_cloud_entrypoint_uses_cloud_run_port():
    script = (Path(__file__).parents[1] / "scripts" / "start_cloud_run.sh").read_text()
    assert '${PORT:-8080}' in script and "--host 0.0.0.0" in script


def test_diagnostics_never_expose_secrets(test_engine):
    settings = Settings(_env_file=None, **BASE, DATABASE_PASSWORD="top-secret", ANALYSIS_WORKER_SHARED_SECRET="worker-secret")
    payload = get_system_status(settings, test_engine).model_dump_json()
    assert "top-secret" not in payload and "worker-secret" not in payload
