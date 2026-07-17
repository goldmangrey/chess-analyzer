import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


ENVIRONMENT_VARIABLES = (
    "APP_ENV",
    "DATABASE_URL",
    "DATABASE_HOST", "DATABASE_PORT", "DATABASE_NAME", "DATABASE_USER", "DATABASE_PASSWORD",
    "AUTO_CREATE_SCHEMA",
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "DB_POOL_TIMEOUT",
    "DB_POOL_RECYCLE",
    "ANALYSIS_QUEUE_BACKEND", "GCP_PROJECT_ID", "GCP_REGION", "CLOUD_TASKS_QUEUE",
    "ANALYSIS_WORKER_URL", "CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL", "CLOUD_TASKS_OIDC_AUDIENCE",
    "CLOUD_TASKS_TASK_DEADLINE_SECONDS", "ANALYSIS_WORKER_SHARED_SECRET",
    "SCHEDULED_SYNC_ENABLED", "SCHEDULED_SYNC_SHARED_SECRET",
    "CHESS_USERNAME",
    "CHESSCOM_USER_AGENT",
    "IMPORT_GAMES_LIMIT",
    "INITIAL_SYNC_MONTHS",
    "INITIAL_SYNC_MAX_GAMES",
    "STOCKFISH_PATH",
    "STOCKFISH_MOVE_TIME_MS",
    "STOCKFISH_PV_LENGTH",
    "FRONTEND_ORIGIN",
    "FRONTEND_ORIGINS",
)


@pytest.fixture(autouse=True)
def isolated_settings_environment(monkeypatch: pytest.MonkeyPatch):
    for variable in ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(variable, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_default_values() -> None:
    settings = make_settings()

    assert settings.model_dump() == {
        "app_env": "development",
        "database_url": "sqlite:///./data/chess.db",
        "database_host": "",
        "database_port": 5432,
        "database_name": "",
        "database_user": "",
        "database_password": "",
        "auto_create_schema": True,
        "db_pool_size": 5,
        "db_max_overflow": 5,
        "db_pool_timeout": 30,
        "db_pool_recycle": 1800,
        "analysis_queue_backend": "local",
        "gcp_project_id": "",
        "gcp_region": "europe-west1",
        "cloud_tasks_queue": "chess-analysis",
        "analysis_worker_url": "",
        "cloud_tasks_service_account_email": "",
        "cloud_tasks_oidc_audience": "",
        "cloud_tasks_task_deadline_seconds": 1800,
        "analysis_worker_shared_secret": "",
        "scheduled_sync_enabled": False,
        "scheduled_sync_shared_secret": "",
        "chess_username": "Yeskendir",
        "chesscom_user_agent": (
            "ChessAITeacher/1.0 (contact: github.com/username)"
        ),
        "import_games_limit": 10,
        "initial_sync_months": 12,
        "initial_sync_max_games": 500,
        "stockfish_path": "./stockfish/stockfish",
        "stockfish_move_time_ms": 250,
        "stockfish_pv_length": 6,
        "frontend_origin": "http://localhost:3000",
        "frontend_origins": "",
    }


def test_reads_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///custom.db")
    monkeypatch.setenv("CHESS_USERNAME", "Player")
    monkeypatch.setenv("CHESSCOM_USER_AGENT", "CustomAgent/1.0")
    monkeypatch.setenv("IMPORT_GAMES_LIMIT", "25")
    monkeypatch.setenv("STOCKFISH_PATH", "/missing/stockfish")
    monkeypatch.setenv("STOCKFISH_MOVE_TIME_MS", "275")
    monkeypatch.setenv("STOCKFISH_PV_LENGTH", "12")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://127.0.0.1:3000")

    settings = make_settings()

    assert settings.database_url == "sqlite:///custom.db"
    assert settings.chess_username == "Player"
    assert settings.chesscom_user_agent == "CustomAgent/1.0"
    assert settings.import_games_limit == 25
    assert settings.stockfish_path == "/missing/stockfish"
    assert settings.stockfish_move_time_ms == 275
    assert settings.stockfish_pv_length == 12
    assert settings.frontend_origin == "http://127.0.0.1:3000"


def test_empty_chesscom_user_agent_is_rejected() -> None:
    with pytest.raises(ValidationError, match="value must not be empty"):
        make_settings(CHESSCOM_USER_AGENT="   ")


@pytest.mark.parametrize("value", [0, 51])
def test_invalid_import_games_limit_is_rejected(value: int) -> None:
    with pytest.raises(ValidationError):
        make_settings(IMPORT_GAMES_LIMIT=value)


@pytest.mark.parametrize("value", [1, 50])
def test_import_games_limit_boundaries_are_allowed(value: int) -> None:
    assert make_settings(IMPORT_GAMES_LIMIT=value).import_games_limit == value


@pytest.mark.parametrize("value", [199, 301])
def test_invalid_stockfish_move_time_is_rejected(value: int) -> None:
    with pytest.raises(ValidationError):
        make_settings(STOCKFISH_MOVE_TIME_MS=value)


@pytest.mark.parametrize("value", [200, 300])
def test_stockfish_move_time_boundaries_are_allowed(value: int) -> None:
    settings = make_settings(STOCKFISH_MOVE_TIME_MS=value)
    assert settings.stockfish_move_time_ms == value


@pytest.mark.parametrize("value", [0, 21])
def test_invalid_stockfish_pv_length_is_rejected(value: int) -> None:
    with pytest.raises(ValidationError):
        make_settings(STOCKFISH_PV_LENGTH=value)


def test_empty_frontend_origin_is_rejected() -> None:
    with pytest.raises(ValidationError, match="value must not be empty"):
        make_settings(FRONTEND_ORIGIN=" ")


def test_missing_stockfish_file_is_not_validated() -> None:
    missing_path = "/path/that/does/not/exist/stockfish"
    settings = make_settings(STOCKFISH_PATH=missing_path)

    assert settings.stockfish_path == missing_path


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHESS_USERNAME", "First")
    first = get_settings()
    monkeypatch.setenv("CHESS_USERNAME", "Second")

    assert get_settings() is first
    assert get_settings().chess_username == "First"

    get_settings.cache_clear()
    assert get_settings().chess_username == "Second"
