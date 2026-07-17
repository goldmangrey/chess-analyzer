import pytest
from fastapi import BackgroundTasks
from pydantic import ValidationError

from app.config import Settings
from app.queues.cloud_tasks import CloudTasksAnalysisQueue
from app.queues.factory import create_analysis_queue
from app.queues.local import LocalAnalysisQueue


def test_local_default_and_cloud_validation():
    local=Settings(_env_file=None)
    assert isinstance(create_analysis_queue(local, background_tasks=BackgroundTasks(), stockfish_factory=lambda: None), LocalAnalysisQueue)
    with pytest.raises(ValidationError): Settings(_env_file=None, ANALYSIS_QUEUE_BACKEND="invalid")
    with pytest.raises(ValidationError): Settings(_env_file=None, ANALYSIS_QUEUE_BACKEND="cloud_tasks")


def test_cloud_factory_is_lazy():
    settings=Settings(_env_file=None, ANALYSIS_QUEUE_BACKEND="cloud_tasks", GCP_PROJECT_ID="p", ANALYSIS_WORKER_URL="https://worker", CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL="a@example.test")
    queue=create_analysis_queue(settings, background_tasks=BackgroundTasks(), stockfish_factory=lambda: None, cloud_client=object())
    assert isinstance(queue, CloudTasksAnalysisQueue)
