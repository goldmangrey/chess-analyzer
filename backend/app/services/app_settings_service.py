from sqlalchemy.orm import Session

from app.repositories import app_settings_repository
from app.schemas import AppSettingsResponse, AppSettingsUpdateRequest


def normalize_username(username: str) -> str:
    normalized = username.strip()
    if not normalized:
        raise ValueError("Chess.com username must not be empty")
    if len(normalized) > 100:
        raise ValueError("Chess.com username must not exceed 100 characters")
    return normalized


def get_app_settings(session: Session) -> AppSettingsResponse:
    return AppSettingsResponse.model_validate(app_settings_repository.get_or_create_settings(session))


def update_app_settings(session: Session, request: AppSettingsUpdateRequest) -> AppSettingsResponse:
    settings = app_settings_repository.get_or_create_settings(session)
    values = request.model_dump(exclude_unset=True)
    if "chesscom_username" in values:
        values["chesscom_username"] = normalize_username(values["chesscom_username"])
    app_settings_repository.update_settings(session, settings, **values)
    return AppSettingsResponse.model_validate(settings)
