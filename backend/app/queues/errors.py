class QueueError(RuntimeError):
    pass


class QueueConfigurationError(QueueError):
    pass


class QueueEnqueueError(QueueError):
    pass


class PermanentAnalysisTaskError(RuntimeError):
    pass


class TransientAnalysisTaskError(RuntimeError):
    pass


class TaskAuthenticationError(RuntimeError):
    pass
