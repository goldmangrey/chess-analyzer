import secrets

from fastapi import Depends, Header, HTTPException

from app.config import Settings
from app.dependencies import get_settings_dependency


def require_scheduled_sync_authentication(
    supplied: str | None = Header(default=None, alias="X-Scheduled-Sync-Secret"),
    settings: Settings = Depends(get_settings_dependency),
) -> None:
    expected = settings.scheduled_sync_shared_secret
    if expected and (supplied is None or not secrets.compare_digest(supplied, expected)):
        raise HTTPException(401, detail="Scheduled sync authentication failed")
