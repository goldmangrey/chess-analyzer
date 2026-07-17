from app.config import AnalysisQueueBackend
from app.queues.cloud_tasks import CloudTasksAnalysisQueue
from app.queues.errors import QueueConfigurationError
from app.queues.local import LocalAnalysisQueue


def create_analysis_queue(settings, *, background_tasks, stockfish_factory, session_factory=None, cloud_client=None):
    kwargs = {"session_factory": session_factory} if session_factory is not None else {}
    if settings.analysis_queue_backend is AnalysisQueueBackend.LOCAL:
        return LocalAnalysisQueue(background_tasks, stockfish_factory, **kwargs)
    if settings.analysis_queue_backend is AnalysisQueueBackend.CLOUD_TASKS:
        return CloudTasksAnalysisQueue(settings, client=cloud_client, **kwargs)
    raise QueueConfigurationError("Unsupported analysis queue backend")
