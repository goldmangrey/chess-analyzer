from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_docs_openapi_lifespan_and_title() -> None:
    startups = []
    application = create_app(
        settings=Settings(_env_file=None),
        init_database=lambda: startups.append("initialized"),
    )
    with TestClient(application) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/health").status_code == 200
        assert client.get("/docs").status_code == 200
        openapi = client.get("/openapi.json")
        assert openapi.status_code == 200
        assert openapi.json()["info"]["title"] == "Chess AI Teacher API"
    assert startups == ["initialized"]


def test_cors_allows_only_configured_frontend(api_client) -> None:
    allowed = api_client.options(
        "/api/games",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = api_client.options(
        "/api/games",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-origin" not in denied.headers
