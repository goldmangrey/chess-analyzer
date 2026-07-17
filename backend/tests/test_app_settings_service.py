import pytest

from app.schemas import AppSettingsUpdateRequest
from app.services.app_settings_service import get_app_settings, update_app_settings


def test_service_defaults_trim_and_toggles(db_session) -> None:
    assert get_app_settings(db_session).chesscom_username is None
    response = update_app_settings(
        db_session,
        AppSettingsUpdateRequest(
            chesscom_username="  Yeskendir  ",
            auto_sync_enabled=False,
            auto_analyze_latest=False,
        ),
    )
    assert response.chesscom_username == "Yeskendir"
    assert not response.auto_sync_enabled and not response.auto_analyze_latest


def test_empty_username_is_rejected() -> None:
    with pytest.raises(ValueError):
        AppSettingsUpdateRequest(chesscom_username="   ")
