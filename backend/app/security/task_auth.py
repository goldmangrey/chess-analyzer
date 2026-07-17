import secrets

from fastapi import Depends, Header, HTTPException

from app.config import Settings
from app.dependencies import get_settings_dependency


def require_task_authentication(
    worker_secret: str | None = Header(default=None, alias="X-Analysis-Worker-Secret"),
    settings: Settings = Depends(get_settings_dependency),
) -> None:
    expected = settings.analysis_worker_shared_secret
    if expected and (worker_secret is None or not secrets.compare_digest(worker_secret, expected)):
        raise HTTPException(status_code=401, detail="Task authentication failed")
