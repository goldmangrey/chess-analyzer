import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


ENVIRONMENT_VARIABLES = (
    "APP_ENV",
    "DATABASE_URL",
    "CHESS_USERNAME",
    "CHESSCOM_USER_AGENT",
    "IMPORT_GAMES_LIMIT",
    "STOCKFISH_PATH",
    "STOCKFISH_MOVE_TIME_MS",
    "STOCKFISH_PV_LENGTH",
    "FRONTEND_ORIGIN",
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
        "chess_username": "Yeskendir",
        "chesscom_user_agent": (
            "ChessAITeacher/1.0 (contact: github.com/username)"
        ),
        "import_games_limit": 10,
        "stockfish_path": "./stockfish/stockfish",
        "stockfish_move_time_ms": 250,
        "stockfish_pv_length": 6,
        "frontend_origin": "http://localhost:3000",
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
