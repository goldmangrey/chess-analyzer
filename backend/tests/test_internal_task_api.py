from app.api import internal_tasks
from app.dependencies import get_stockfish_factory
from app.models import AnalysisStatus, Color, Game, GameResult


def test_worker_executes_and_is_idempotent(api_app, api_client, monkeypatch):
    session=api_app.state.testing_session_factory(); game=Game(external_id="worker", white_username="U", black_username="O", user_color=Color.WHITE, result=GameResult.WIN, pgn="1. e4", analysis_status=AnalysisStatus.ANALYZING); session.add(game); session.commit(); game_id=game.id; session.close()
    calls=[]
    monkeypatch.setattr(internal_tasks, "execute_game_analysis", lambda session, game_id, factory: calls.append(game_id) or object())
    api_app.dependency_overrides[get_stockfish_factory]=lambda: lambda: object()
    response=api_client.post("/internal/tasks/analyze-game", json={"game_id":game_id,"schema_version":1})
    assert response.status_code == 200 and response.json()["status"] == "completed" and calls == [game_id]
    assert api_client.post("/internal/tasks/analyze-game", json={"game_id":game_id,"schema_version":2}).status_code == 422
