from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_database_session
from app.schemas import PlayerIntelligenceResponse
from app.services.player_intelligence_service import PlayerIntelligenceService


router = APIRouter(prefix="/api/player", tags=["player"])


@router.get("/intelligence", response_model=PlayerIntelligenceResponse)
def get_player_intelligence(
    session: Session = Depends(get_database_session),
    window: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description=(
                "Number of latest completed analyzed games in the current profile; "
                "trends compare that window with the immediately preceding window."
            ),
        ),
    ] = 30,
) -> PlayerIntelligenceResponse:
    intelligence = PlayerIntelligenceService(session).build(window=window)
    return PlayerIntelligenceResponse.model_validate(intelligence)
