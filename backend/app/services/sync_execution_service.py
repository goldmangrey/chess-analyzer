from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Literal

from sqlalchemy.orm import Session

from app.config import Settings
from app.queues.errors import QueueEnqueueError
from app.repositories import app_settings_repository
from app.schemas import SyncMode
from app.services.app_settings_service import normalize_username
from app.services.chesscom_sync import synchronize_chesscom
from app.services.sync_execution_lock import SyncExecutionLock

logger = logging.getLogger(__name__)


class SyncUsernameNotConfiguredError(ValueError):
    pass


@dataclass(frozen=True)
class SyncExecutionResult:
    status: Literal["completed", "already_running", "disabled"]
    mode: SyncMode
    username: str | None
    examined: int = 0
    imported: int = 0
    duplicates: int = 0
    invalid: int = 0
    imported_game_ids: tuple[int, ...] = ()
    latest_game_id: int | None = None
    analysis_queued_game_id: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


def execute_chesscom_sync(
    *, session: Session, client, queue, config: Settings, execution_lock: SyncExecutionLock,
    mode: SyncMode, username_override: str | None = None,
    auto_analyze_latest: bool | None = None, initial_months: int | None = None,
    source: Literal["manual", "browser", "scheduler"] = "manual",
) -> SyncExecutionResult:
    with execution_lock.acquire() as acquired:
        if not acquired:
            logger.info("Chess.com sync skipped: source=%s result=already_running", source)
            return SyncExecutionResult("already_running", mode, username_override)
        app_settings = app_settings_repository.get_or_create_settings(session)
        if source == "scheduler" and not app_settings.auto_sync_enabled:
            logger.info("Scheduled sync skipped: disabled")
            return SyncExecutionResult("disabled", mode, app_settings.chesscom_username)
        try:
            username = normalize_username(username_override or app_settings.chesscom_username or "")
        except ValueError as error:
            raise SyncUsernameNotConfiguredError("Chess.com username is not configured") from error
        if username_override:
            app_settings_repository.update_settings(session, app_settings, chesscom_username=username)
        if auto_analyze_latest is not None:
            app_settings_repository.update_settings(session, app_settings, auto_analyze_latest=auto_analyze_latest)
        started_at = datetime.now(timezone.utc)
        app_settings_repository.mark_sync_started(session, app_settings, at=started_at)
        session.commit()
        try:
            synchronized = synchronize_chesscom(
                session, client, username, mode, config, initial_months=initial_months
            )
            session.commit()  # Imported games are durable before queue interaction.
            queued_id = None
            latest_id = synchronized.latest_game_id
            if latest_id is not None and app_settings.auto_analyze_latest:
                try:
                    enqueue = queue.enqueue_game_analysis(game_id=latest_id)
                    if enqueue.status == "queued":
                        queued_id = latest_id
                except QueueEnqueueError:
                    logger.exception("Sync imported game %s but queue enqueue failed", latest_id)
            completed_at = datetime.now(timezone.utc)
            current = app_settings_repository.get_or_create_settings(session)
            app_settings_repository.mark_sync_completed(
                session, current, initial=mode is SyncMode.INITIAL, at=completed_at
            )
            session.commit()
        except Exception:
            session.rollback()
            failed = app_settings_repository.get_or_create_settings(session)
            app_settings_repository.mark_sync_failed(session, failed, "Chess.com synchronization failed")
            session.commit()
            logger.exception("Chess.com sync failed: source=%s", source)
            raise
        result = synchronized.result
        logger.info(
            "Chess.com sync completed: source=%s examined=%s imported=%s duplicates=%s",
            source, result.examined, result.imported, result.skipped_duplicates,
        )
        return SyncExecutionResult(
            "completed", mode, username, result.examined, result.imported,
            result.skipped_duplicates, result.skipped_invalid, result.imported_game_ids,
            latest_id, queued_id, started_at, completed_at,
        )
