def test_settings_get_patch_and_validation(api_client) -> None:
    initial = api_client.get("/api/settings")
    assert initial.status_code == 200
    assert initial.json()["chesscom_username"] is None
    assert initial.json()["last_sync_status"] == "never"

    patched = api_client.patch(
        "/api/settings",
        json={"chesscom_username": "  Player  ", "auto_sync_enabled": False, "auto_analyze_latest": False},
    )
    assert patched.status_code == 200
    assert patched.json()["chesscom_username"] == "Player"
    assert patched.json()["auto_sync_enabled"] is False
    assert api_client.patch("/api/settings", json={"chesscom_username": " "}).status_code == 422
    assert api_client.patch("/api/settings", json={"unknown": True}).status_code == 422
