import os

from app.dependencies import get_chesscom_client, get_database_engine, get_settings_dependency


def test_system_status_ready_without_starting_external_services(
    api_app, api_client, test_engine, tmp_path, monkeypatch
) -> None:
    binary = tmp_path / "stockfish"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o755)
    settings = get_settings_dependency()
    ready_settings = settings.model_copy(update={"stockfish_path": str(binary)})
    api_app.dependency_overrides[get_settings_dependency] = lambda: ready_settings
    api_app.dependency_overrides[get_database_engine] = lambda: test_engine

    monkeypatch.setattr(
        "chess.engine.SimpleEngine.popen_uci",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("engine started")),
    )
    response = api_client.get("/api/system/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["backend"] == "ready"
    assert body["database"]["tables_ready"] is True
    assert body["stockfish"] == {
        "status": "ready",
        "path": str(binary),
        "executable": True,
    }
    assert body["chesscom"]["configured"] is True


def test_missing_or_non_executable_stockfish_is_degraded(
    api_app, api_client, test_engine, tmp_path
) -> None:
    settings = get_settings_dependency()
    api_app.dependency_overrides[get_database_engine] = lambda: test_engine

    for path in (tmp_path / "missing", tmp_path / "not-executable"):
        if path.name == "not-executable":
            path.write_text("binary", encoding="utf-8")
            path.chmod(0o644)
            assert not os.access(path, os.X_OK)
        configured = settings.model_copy(update={"stockfish_path": str(path)})
        api_app.dependency_overrides[get_settings_dependency] = lambda configured=configured: configured
        response = api_client.get("/api/system/status")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"
        assert response.json()["stockfish"]["executable"] is False


def test_system_status_does_not_call_chesscom(api_app, api_client, test_engine) -> None:
    api_app.dependency_overrides[get_database_engine] = lambda: test_engine
    api_app.dependency_overrides[get_chesscom_client] = lambda: (_ for _ in ()).throw(
        AssertionError("Chess.com client created")
    )
    assert api_client.get("/api/system/status").status_code == 200
