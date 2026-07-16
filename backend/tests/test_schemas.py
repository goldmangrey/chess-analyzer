from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models import Color, Game, GameResult
from app.schemas import GameCreate, GameListItem, GameRead, MoveAnalysisCreate


def valid_game_data() -> dict[str, object]:
    return {
        "external_id": "schema-game",
        "white_username": "Yeskendir",
        "black_username": "Opponent",
        "user_color": "white",
        "result": "win",
        "pgn": "1. e4 e5",
    }


def test_orm_game_converts_to_read_schema() -> None:
    now = datetime.now(timezone.utc)
    game = Game(
        id=1,
        **valid_game_data(),
        platform="chess.com",
        analysis_status="pending",
        created_at=now,
        updated_at=now,
        move_analyses=[],
    )

    schema = GameRead.model_validate(game)

    assert schema.id == 1
    assert schema.user_color is Color.WHITE
    assert schema.result is GameResult.WIN
    assert schema.move_analyses == []


def test_game_list_item_does_not_contain_pgn() -> None:
    now = datetime.now(timezone.utc)
    data = {
        **valid_game_data(),
        "id": 1,
        "platform": "chess.com",
        "analysis_status": "pending",
        "created_at": now,
        "updated_at": now,
    }

    item = GameListItem.model_validate(data)

    assert "pgn" not in item.model_dump()


@pytest.mark.parametrize(
    ("field", "value"),
    [("user_color", "green"), ("result", "unknown"), ("analysis_status", "queued")],
)
def test_game_create_rejects_invalid_enums(field: str, value: str) -> None:
    data = valid_game_data()
    data[field] = value

    with pytest.raises(ValidationError):
        GameCreate.model_validate(data)


@pytest.mark.parametrize(
    ("field", "value"),
    [("game_id", 0), ("ply", 0), ("move_number", 0), ("centipawn_loss", -1)],
)
def test_move_create_rejects_invalid_ranges(field: str, value: int) -> None:
    data = {
        "game_id": 1,
        "ply": 1,
        "move_number": 1,
        "player_color": "white",
        "is_user_move": True,
        "fen_before": "fen",
        "played_move_uci": "e2e4",
        "centipawn_loss": 0,
        "classification": "normal",
    }
    data[field] = value

    with pytest.raises(ValidationError):
        MoveAnalysisCreate.model_validate(data)


def test_game_create_rejects_client_supplied_id() -> None:
    with pytest.raises(ValidationError):
        GameCreate.model_validate({**valid_game_data(), "id": 999})
