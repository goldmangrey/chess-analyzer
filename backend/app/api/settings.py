from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_database_session
from app.schemas import AppSettingsResponse, AppSettingsUpdateRequest
from app.services.app_settings_service import get_app_settings, update_app_settings


router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=AppSettingsResponse)
def read_settings(session: Session = Depends(get_database_session)) -> AppSettingsResponse:
    response = get_app_settings(session)
    session.commit()
    return response


@router.patch("", response_model=AppSettingsResponse)
def patch_settings(
    request: AppSettingsUpdateRequest,
    session: Session = Depends(get_database_session),
) -> AppSettingsResponse:
    response = update_app_settings(session, request)
    session.commit()
    return response
