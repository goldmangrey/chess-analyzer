import json
from types import SimpleNamespace
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.models import Color, Game, GameResult
from app.queues.cloud_tasks import CloudTasksAnalysisQueue


class FakeClient:
    def __init__(self): self.request = None
    def queue_path(self, project, region, queue): return f"projects/{project}/locations/{region}/queues/{queue}"
    def create_task(self, request): self.request=request; return SimpleNamespace(name=request["task"].name)


def test_cloud_task_contract(test_engine):
    factory=sessionmaker(bind=test_engine, expire_on_commit=False); s=factory(); item=Game(external_id="cloud-q", white_username="U", black_username="O", user_color=Color.WHITE, result=GameResult.WIN, pgn="1. e4"); s.add(item); s.commit(); game_id=item.id; s.close()
    settings=Settings(_env_file=None, ANALYSIS_QUEUE_BACKEND="cloud_tasks", GCP_PROJECT_ID="project", GCP_REGION="region", CLOUD_TASKS_QUEUE="queue", ANALYSIS_WORKER_URL="https://worker.example", CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL="worker@example.test", CLOUD_TASKS_OIDC_AUDIENCE="https://worker.example", ANALYSIS_WORKER_SHARED_SECRET="secret")
    client=FakeClient(); result=CloudTasksAnalysisQueue(settings, client=client, session_factory=factory).enqueue_game_analysis(game_id=game_id)
    task=client.request["task"]
    assert result.status == "queued" and client.request["parent"].endswith("/queues/queue")
    assert task.http_request.url == "https://worker.example/internal/tasks/analyze-game"
    assert json.loads(task.http_request.body) == {"game_id": game_id, "force": False, "schema_version": 1}
    assert task.http_request.oidc_token.service_account_email == "worker@example.test"
    assert task.dispatch_deadline.seconds == 1800
    assert "secret" not in task.name
