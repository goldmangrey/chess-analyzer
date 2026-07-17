from fastapi import APIRouter, Depends
from sqlalchemy import Engine

from app.config import Settings
from app.dependencies import (
    get_database_engine,
    get_settings_dependency,
)
from app.schemas import SystemStatusResponse
from app.services.system_status import get_system_status


router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
def system_status(
    settings: Settings = Depends(get_settings_dependency),
    engine: Engine = Depends(get_database_engine),
) -> SystemStatusResponse:
    return get_system_status(settings, engine)
