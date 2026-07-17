from app.models import SyncStatus
from app.repositories import app_settings_repository as repository


def test_singleton_settings_lifecycle(db_session) -> None:
    first = repository.get_or_create_settings(db_session)
    second = repository.get_or_create_settings(db_session)
    assert first.id == second.id == 1
    assert first.auto_sync_enabled and first.auto_analyze_latest
    assert first.last_sync_status is SyncStatus.NEVER

    repository.update_settings(db_session, first, chesscom_username="Player", auto_sync_enabled=False)
    repository.mark_sync_started(db_session, first)
    assert first.last_sync_status is SyncStatus.RUNNING
    repository.mark_sync_completed(db_session, first, initial=True)
    assert first.initial_sync_completed and first.last_sync_status is SyncStatus.COMPLETED
    repository.mark_sync_failed(db_session, first, "safe error")
    assert first.last_sync_status is SyncStatus.FAILED and first.last_sync_error == "safe error"
