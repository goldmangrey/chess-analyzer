from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AppSettings, SyncStatus, utc_now


def get_settings(session: Session) -> AppSettings | None:
    return session.get(AppSettings, 1)


def get_or_create_settings(session: Session) -> AppSettings:
    settings = get_settings(session)
    if settings is None:
        settings = AppSettings(id=1)
        session.add(settings)
        session.flush()
    return settings


def update_settings(
    session: Session,
    settings: AppSettings,
    *,
    chesscom_username: str | None | object = ...,
    auto_sync_enabled: bool | object = ...,
    auto_analyze_latest: bool | object = ...,
) -> AppSettings:
    if chesscom_username is not ...:
        settings.chesscom_username = chesscom_username  # type: ignore[assignment]
    if auto_sync_enabled is not ...:
        settings.auto_sync_enabled = auto_sync_enabled  # type: ignore[assignment]
    if auto_analyze_latest is not ...:
        settings.auto_analyze_latest = auto_analyze_latest  # type: ignore[assignment]
    session.flush()
    return settings


def mark_sync_started(session: Session, settings: AppSettings, *, at: datetime | None = None) -> None:
    settings.last_sync_started_at = at or utc_now()
    settings.last_sync_status = SyncStatus.RUNNING
    settings.last_sync_error = None
    session.flush()


def mark_sync_completed(
    session: Session,
    settings: AppSettings,
    *,
    initial: bool,
    at: datetime | None = None,
) -> None:
    settings.last_sync_completed_at = at or utc_now()
    settings.last_sync_status = SyncStatus.COMPLETED
    settings.last_sync_error = None
    if initial:
        settings.initial_sync_completed = True
    session.flush()


def mark_sync_failed(session: Session, settings: AppSettings, message: str) -> None:
    settings.last_sync_status = SyncStatus.FAILED
    settings.last_sync_error = message[:500]
    session.flush()
