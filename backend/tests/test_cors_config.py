import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.database import init_db
from app.dependencies import get_database_session, get_settings_dependency
from app.main import create_app


PRODUCTION_ORIGIN = "https://chess-ai-frontend-test.run.app"
ALLOWED_ORIGINS = f"{PRODUCTION_ORIGIN},http://localhost:3000,http://127.0.0.1:3000"


def test_multiple_origins_trimmed_and_local_default():
    assert Settings(_env_file=None).allowed_frontend_origins == ("http://localhost:3000",)
    configured = Settings(_env_file=None, FRONTEND_ORIGINS=" https://one.example/, http://localhost:3000 ")
    assert configured.allowed_frontend_origins == ("https://one.example", "http://localhost:3000")


def test_comma_separated_origins_ignore_whitespace_and_empty_values():
    configured = Settings(
        _env_file=None,
        FRONTEND_ORIGINS=" https://one.example , , http://localhost:3000, ",
    )
    assert configured.allowed_frontend_origins == (
        "https://one.example",
        "http://localhost:3000",
    )


def test_wildcard_rejected():
    with pytest.raises(ValueError):
        _ = Settings(_env_file=None, FRONTEND_ORIGINS="*").allowed_frontend_origins


@pytest.fixture
def cors_client(test_engine):
    settings = Settings(_env_file=None, FRONTEND_ORIGINS=ALLOWED_ORIGINS)
    testing_session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    app = create_app(settings=settings, init_database=lambda: init_db(bind=test_engine))

    def override_database_session():
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_database_session] = override_database_session
    app.dependency_overrides[get_settings_dependency] = lambda: settings
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize(
    "origin",
    [PRODUCTION_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"],
)
def test_configured_origins_are_allowed(cors_client, origin):
    response = cors_client.get("/health", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_unknown_origin_is_not_allowed(cors_client):
    response = cors_client.get("/health", headers={"Origin": "https://unknown.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_localhost_settings_preflight_and_patch_succeed(cors_client):
    origin = "http://localhost:3000"
    preflight = cors_client.options(
        "/api/settings",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin

    patched = cors_client.patch(
        "/api/settings",
        headers={"Origin": origin},
        json={"chesscom_username": "CorsPlayer"},
    )
    assert patched.status_code == 200
    assert patched.json()["chesscom_username"] == "CorsPlayer"
    assert patched.headers["access-control-allow-origin"] == origin
