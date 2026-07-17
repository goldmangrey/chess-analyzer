from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: str = Field(default="development", validation_alias="APP_ENV")

    database_url: str = Field(
        default="sqlite:///./data/chess.db",
        validation_alias="DATABASE_URL",
    )
    chess_username: str = Field(
        default="Yeskendir",
        validation_alias="CHESS_USERNAME",
    )
    chesscom_user_agent: str = Field(
        default="ChessAITeacher/1.0 (contact: github.com/username)",
        validation_alias="CHESSCOM_USER_AGENT",
    )
    import_games_limit: int = Field(
        default=10,
        ge=1,
        le=50,
        validation_alias="IMPORT_GAMES_LIMIT",
    )
    initial_sync_months: int = Field(default=12, ge=1, le=24, validation_alias="INITIAL_SYNC_MONTHS")
    initial_sync_max_games: int = Field(default=500, ge=1, le=2000, validation_alias="INITIAL_SYNC_MAX_GAMES")
    stockfish_path: str = Field(
        default="./stockfish/stockfish",
        validation_alias="STOCKFISH_PATH",
    )
    stockfish_move_time_ms: int = Field(
        default=250,
        ge=200,
        le=300,
        validation_alias="STOCKFISH_MOVE_TIME_MS",
    )
    stockfish_pv_length: int = Field(
        default=6,
        ge=1,
        le=20,
        validation_alias="STOCKFISH_PV_LENGTH",
    )
    frontend_origin: str = Field(
        default="http://localhost:3000",
        validation_alias="FRONTEND_ORIGIN",
    )

    @field_validator("app_env", "chess_username", "chesscom_user_agent", "frontend_origin")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
