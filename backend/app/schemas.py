from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import AnalysisStatus, Color, GameResult, MoveClassification


class CreateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MoveAnalysisCreate(CreateSchema):
    game_id: int = Field(ge=1)
    ply: int = Field(ge=1)
    move_number: int = Field(ge=1)
    player_color: Color
    is_user_move: bool
    fen_before: str = Field(min_length=1)
    played_move_uci: str = Field(min_length=1)
    played_move_san: str | None = None
    best_move_uci: str | None = None
    best_move_san: str | None = None
    evaluation_before_cp: int | None = None
    evaluation_after_cp: int | None = None
    centipawn_loss: int = Field(ge=0)
    classification: MoveClassification
    principal_variation: str | None = None


class MoveAnalysisRead(ReadSchema):
    id: int
    game_id: int
    ply: int
    move_number: int
    player_color: Color
    is_user_move: bool
    fen_before: str
    played_move_uci: str
    played_move_san: str | None
    best_move_uci: str | None
    best_move_san: str | None
    evaluation_before_cp: int | None
    evaluation_after_cp: int | None
    centipawn_loss: int
    classification: MoveClassification
    principal_variation: str | None
    created_at: datetime


class GameCreate(CreateSchema):
    external_id: str = Field(min_length=1)
    platform: str = Field(default="chess.com", min_length=1)
    played_at: datetime | None = None
    white_username: str = Field(min_length=1)
    black_username: str = Field(min_length=1)
    white_rating: int | None = None
    black_rating: int | None = None
    user_color: Color
    result: GameResult
    time_control: str | None = None
    opening_code: str | None = None
    opening_name: str | None = None
    pgn: str = Field(min_length=1)
    analysis_status: AnalysisStatus = AnalysisStatus.PENDING
    analyzed_at: datetime | None = None


class GameListItem(ReadSchema):
    id: int
    external_id: str
    platform: str
    played_at: datetime | None = None
    white_username: str
    black_username: str
    white_rating: int | None = None
    black_rating: int | None = None
    user_color: Color
    result: GameResult
    time_control: str | None = None
    opening_code: str | None = None
    opening_name: str | None = None
    analysis_status: AnalysisStatus
    created_at: datetime
    updated_at: datetime
    analyzed_at: datetime | None = None


class GameRead(GameListItem):
    pgn: str
    move_analyses: list[MoveAnalysisRead] = Field(default_factory=list)
