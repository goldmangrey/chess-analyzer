from functools import lru_cache
from enum import Enum
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class AnalysisQueueBackend(str, Enum):
    LOCAL = "local"
    CLOUD_TASKS = "cloud_tasks"


def compose_cloud_sql_database_url(*, host: str, port: int, name: str, user: str, password: str) -> str:
    if not all(value.strip() for value in (host, name, user, password)):
        raise ValueError("Cloud SQL database settings must not be empty")
    credentials = f"{quote(user, safe='')}:{quote(password, safe='')}"
    if host.startswith("/"):
        return f"postgresql+psycopg://{credentials}@/{quote(name, safe='')}?{urlencode({'host': host})}"
    return f"postgresql+psycopg://{credentials}@{host}:{port}/{quote(name, safe='')}"


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
        repr=False,
    )
    database_host: str = Field(default="", validation_alias="DATABASE_HOST")
    database_port: int = Field(default=5432, ge=1, le=65535, validation_alias="DATABASE_PORT")
    database_name: str = Field(default="", validation_alias="DATABASE_NAME")
    database_user: str = Field(default="", validation_alias="DATABASE_USER")
    database_password: str = Field(default="", validation_alias="DATABASE_PASSWORD", repr=False)
    auto_create_schema: bool = Field(default=True, validation_alias="AUTO_CREATE_SCHEMA")
    db_pool_size: int = Field(default=5, ge=1, le=20, validation_alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=5, ge=0, le=20, validation_alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, ge=1, validation_alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=1800, ge=0, validation_alias="DB_POOL_RECYCLE")
    analysis_queue_backend: AnalysisQueueBackend = Field(default=AnalysisQueueBackend.LOCAL, validation_alias="ANALYSIS_QUEUE_BACKEND")
    gcp_project_id: str = Field(default="", validation_alias="GCP_PROJECT_ID")
    gcp_region: str = Field(default="europe-west1", validation_alias="GCP_REGION")
    cloud_tasks_queue: str = Field(default="chess-analysis", validation_alias="CLOUD_TASKS_QUEUE")
    analysis_worker_url: str = Field(default="", validation_alias="ANALYSIS_WORKER_URL")
    cloud_tasks_service_account_email: str = Field(default="", validation_alias="CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL")
    cloud_tasks_oidc_audience: str = Field(default="", validation_alias="CLOUD_TASKS_OIDC_AUDIENCE")
    cloud_tasks_task_deadline_seconds: int = Field(default=1800, ge=60, le=1800, validation_alias="CLOUD_TASKS_TASK_DEADLINE_SECONDS")
    analysis_worker_shared_secret: str = Field(default="", validation_alias="ANALYSIS_WORKER_SHARED_SECRET")
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
    frontend_origins: str = Field(default="", validation_alias="FRONTEND_ORIGINS")

    @field_validator("app_env", "chess_username", "chesscom_user_agent", "frontend_origin")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @model_validator(mode="after")
    def validate_cloud_tasks(self) -> "Settings":
        db_parts = (self.database_host, self.database_name, self.database_user, self.database_password)
        explicit_database_url = "database_url" in self.model_fields_set and bool(self.database_url.strip())
        if any(db_parts) and not explicit_database_url:
            if not all(value.strip() for value in db_parts):
                raise ValueError("DATABASE_HOST, DATABASE_NAME, DATABASE_USER and DATABASE_PASSWORD must be set together")
            self.database_url = compose_cloud_sql_database_url(
                host=self.database_host, port=self.database_port, name=self.database_name,
                user=self.database_user, password=self.database_password,
            )
        if self.analysis_queue_backend is AnalysisQueueBackend.CLOUD_TASKS:
            required = {
                "GCP_PROJECT_ID": self.gcp_project_id,
                "GCP_REGION": self.gcp_region,
                "CLOUD_TASKS_QUEUE": self.cloud_tasks_queue,
                "ANALYSIS_WORKER_URL": self.analysis_worker_url,
                "CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL": self.cloud_tasks_service_account_email,
            }
            missing = [name for name, value in required.items() if not value.strip()]
            if missing:
                raise ValueError(f"Missing Cloud Tasks configuration: {', '.join(missing)}")
        if self.app_env.lower() == "production":
            if self.database_url.startswith("sqlite"):
                raise ValueError("Production requires PostgreSQL")
            if self.auto_create_schema:
                raise ValueError("Production requires AUTO_CREATE_SCHEMA=false")
            if self.analysis_queue_backend is not AnalysisQueueBackend.CLOUD_TASKS:
                raise ValueError("Production requires ANALYSIS_QUEUE_BACKEND=cloud_tasks")
        return self

    @property
    def allowed_frontend_origins(self) -> tuple[str, ...]:
        raw = self.frontend_origins or self.frontend_origin
        origins = tuple(value.strip().rstrip("/") for value in raw.split(",") if value.strip())
        if not origins or "*" in origins:
            raise ValueError("CORS origins must be explicit and cannot contain wildcard")
        return origins

    @property
    def analysis_worker_audience(self) -> str:
        if self.cloud_tasks_oidc_audience.strip():
            return self.cloud_tasks_oidc_audience.strip()
        parsed = urlsplit(self.analysis_worker_url)
        return f"{parsed.scheme}://{parsed.netloc}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
