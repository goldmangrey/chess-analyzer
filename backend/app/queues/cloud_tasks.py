import json
import uuid

from google.api_core.exceptions import AlreadyExists
from google.cloud import tasks_v2
from google.protobuf import duration_pb2

from app.database import SessionLocal
from app.queues.base import AnalysisEnqueueResult
from app.queues.errors import QueueEnqueueError
from app.services.analysis_queue_service import mark_enqueue_failed, reserve_analysis_committed


class CloudTasksAnalysisQueue:
    def __init__(self, settings, *, client=None, session_factory=SessionLocal):
        self.settings = settings
        self._client = client
        self.session_factory = session_factory

    @property
    def client(self):
        if self._client is None:
            self._client = tasks_v2.CloudTasksClient()
        return self._client

    def enqueue_game_analysis(self, *, game_id: int, force: bool = False) -> AnalysisEnqueueResult:
        session = self.session_factory()
        previous = None
        try:
            reservation = reserve_analysis_committed(session, game_id, force=force)
            previous = reservation.previous_status
            if reservation.status != "queued":
                return AnalysisEnqueueResult(game_id, reservation.status)
        finally:
            session.close()

        parent = self.client.queue_path(
            self.settings.gcp_project_id, self.settings.gcp_region, self.settings.cloud_tasks_queue
        )
        # The first pending enqueue is deterministic for quick duplicate protection.
        # Retries after a failed/completed attempt need a fresh Cloud Tasks name,
        # because deleted task names can remain reserved by the service.
        suffix = "initial" if previous is not None and previous.value == "pending" and not force else uuid.uuid4().hex
        task_name = f"{parent}/tasks/game-{game_id}-analysis-{suffix}"
        headers = {"Content-Type": "application/json"}
        if self.settings.analysis_worker_shared_secret:
            headers["X-Analysis-Worker-Secret"] = self.settings.analysis_worker_shared_secret
        task = tasks_v2.Task(
            name=task_name,
            http_request=tasks_v2.HttpRequest(
                http_method=tasks_v2.HttpMethod.POST,
                url=f"{self.settings.analysis_worker_url.rstrip('/')}/internal/tasks/analyze-game",
                headers=headers,
                body=json.dumps({"game_id": game_id, "force": force, "schema_version": 1}).encode(),
                oidc_token=tasks_v2.OidcToken(
                    service_account_email=self.settings.cloud_tasks_service_account_email,
                    audience=self.settings.analysis_worker_audience,
                ),
            ),
            dispatch_deadline=duration_pb2.Duration(seconds=self.settings.cloud_tasks_task_deadline_seconds),
        )
        try:
            created = self.client.create_task(request={"parent": parent, "task": task})
            returned_name = created.name
        except AlreadyExists:
            returned_name = task_name
        except Exception as error:
            recovery = self.session_factory()
            try:
                mark_enqueue_failed(recovery, game_id, previous)
                recovery.commit()
            finally:
                recovery.close()
            raise QueueEnqueueError(f"Could not create Cloud Task for game {game_id}") from error
        return AnalysisEnqueueResult(game_id, "queued", returned_name)
