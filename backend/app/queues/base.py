from dataclasses import dataclass
from typing import Literal, Protocol


EnqueueStatus = Literal["queued", "already_queued", "already_analyzing", "already_completed"]


@dataclass(frozen=True)
class AnalysisEnqueueResult:
    game_id: int
    status: EnqueueStatus
    task_id: str | None = None


class AnalysisQueue(Protocol):
    def enqueue_game_analysis(self, *, game_id: int, force: bool = False) -> AnalysisEnqueueResult: ...
