from datetime import datetime, timedelta, timezone

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.dependencies import get_analysis_queue
from app.queues.base import AnalysisEnqueueResult
from app.queues.errors import PermanentAnalysisTaskError
from app.models import AnalysisStatus, Color, Game, GamePhase, GameResult, MoveAnalysis, MoveClassification


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def add_game(
    session: Session,
    identifier: str,
    *,
    day: int = 0,
    status: AnalysisStatus = AnalysisStatus.COMPLETED,
    result: GameResult = GameResult.WIN,
    color: Color = Color.WHITE,
    opening: str = "Sicilian Defense",
) -> Game:
    game = Game(
        external_id=identifier,
        played_at=NOW + timedelta(days=day),
        white_username="User" if color is Color.WHITE else "White Opponent",
        black_username="Black Opponent" if color is Color.WHITE else "User",
        white_rating=1500,
        black_rating=1510,
        user_color=color,
        result=result,
        opening_code="B20",
        opening_name=opening,
        time_control="600",
        pgn="1. e4 e5",
        analysis_status=status,
    )
    session.add(game)
    session.flush()
    return game


def add_move(session: Session, game: Game, ply: int, *, user: bool, loss: int, classification, phase=GamePhase.OPENING, before=10, after=-10) -> None:
    session.add(MoveAnalysis(
        game_id=game.id,
        ply=ply,
        move_number=(ply + 1) // 2,
        player_color=Color.WHITE if ply % 2 else Color.BLACK,
        is_user_move=user,
        fen_before="fen",
        played_move_uci="e2e4",
        played_move_san="e4",
        best_move_uci="d2d4",
        best_move_san="d4",
        evaluation_before_cp=before,
        evaluation_after_cp=after,
        centipawn_loss=loss,
        classification=classification,
        phase=phase,
        principal_variation="d4 d5",
    ))
    session.flush()


def seed(api_app):
    session = api_app.state.testing_session_factory()
    first = add_game(session, "first", day=1, result=GameResult.LOSS, color=Color.BLACK)
    second = add_game(session, "second", day=2, status=AnalysisStatus.PENDING, opening="French Defense")
    add_move(session, first, 2, user=False, loss=9999, classification=MoveClassification.BLUNDER)
    add_move(session, first, 1, user=True, loss=100, classification=MoveClassification.MISTAKE)
    session.commit()
    ids = (first.id, second.id)
    session.close()
    return ids


def test_games_empty_filters_pagination_sort_and_shape(api_app, api_client) -> None:
    assert api_client.get("/api/games").json()["items"] == []
    first_id, second_id = seed(api_app)
    newest = api_client.get("/api/games?limit=1&sort=newest").json()
    assert newest["items"][0]["id"] == second_id
    assert newest["returned_count"] == 1 and newest["total"] == 2
    assert "pgn" not in newest["items"][0] and "moves" not in newest["items"][0]
    oldest = api_client.get("/api/games?sort=oldest&offset=0").json()
    assert [item["id"] for item in oldest["items"]] == [first_id, second_id]
    assert api_client.get("/api/games?result=loss").json()["total"] == 1
    assert api_client.get("/api/games?analysis_status=pending").json()["total"] == 1
    assert api_client.get("/api/games?opening=french").json()["items"][0]["id"] == second_id
    assert api_client.get("/api/games?sort=most_blunders").status_code == 200
    assert api_client.get("/api/games?sort=highest_cp_loss").status_code == 200
    for query in ("limit=0", "offset=-1", "sort=unsafe", "result=unknown"):
        assert api_client.get(f"/api/games?{query}").status_code == 422


def test_game_detail_personal_metrics_pending_and_missing(api_app, api_client) -> None:
    first_id, second_id = seed(api_app)
    detail = api_client.get(f"/api/games/{first_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["pgn"] == "1. e4 e5"
    assert body["average_cp_loss"] == 100.0
    assert (body["mistakes"], body["blunders"]) == (1, 0)
    assert body["phases"] == {
        "opening": {
            "start_ply": 1,
            "end_ply": 2,
            "user_moves": 1,
            "average_cp_loss": 100.0,
            "inaccuracies": 0,
            "mistakes": 1,
            "blunders": 0,
        }
    }
    assert body["critical_moments"] == []
    pending = api_client.get(f"/api/games/{second_id}").json()
    assert pending["average_cp_loss"] is None
    assert pending["mistakes"] == pending["blunders"] == 0
    assert pending["phases"] == {}
    assert pending["critical_moments"] == []
    assert pending["errors"] == []
    assert api_client.get("/api/games/9999").status_code == 404


def test_game_detail_serializes_ranked_critical_moments(api_app, api_client) -> None:
    session = api_app.state.testing_session_factory()
    game = add_game(session, "critical")
    add_move(
        session,
        game,
        1,
        user=True,
        loss=365,
        classification=MoveClassification.BLUNDER,
        phase=GamePhase.MIDDLEGAME,
        before=25,
        after=-340,
    )
    session.commit()
    game_id = game.id
    session.close()

    response = api_client.get(f"/api/games/{game_id}")

    assert response.status_code == 200
    moment = response.json()["critical_moments"][0]
    assert moment["type"] == "turning_point"
    assert moment["severity"] == "blunder"
    assert moment["phase"] == "middlegame"
    assert moment["evaluation_before_user_pov"] == 25
    assert moment["evaluation_after_user_pov"] == -340
    assert isinstance(moment["importance_score"], float)


def test_game_detail_serializes_error_taxonomy(api_app, api_client) -> None:
    session = api_app.state.testing_session_factory()
    game = add_game(session, "taxonomy")
    game.pgn = '[SetUp "1"]\n[FEN "rnbqkbnr/pppppppp/8/8/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1"]\n\n1. Qh5 *'
    session.flush()
    session.add(MoveAnalysis(
        game_id=game.id,
        ply=1,
        move_number=1,
        player_color=Color.WHITE,
        is_user_move=True,
        fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1",
        played_move_uci="d1h5",
        played_move_san="Qh5",
        evaluation_before_cp=20,
        evaluation_after_cp=-180,
        centipawn_loss=200,
        classification=MoveClassification.MISTAKE,
        phase=GamePhase.OPENING,
    ))
    session.commit()
    game_id = game.id
    session.close()

    response = api_client.get(f"/api/games/{game_id}")

    assert response.status_code == 200
    error = response.json()["errors"][0]
    assert error == {
        "ply": 1,
        "move_number": 1,
        "move_san": "Qh5",
        "phase": "opening",
        "severity": "mistake",
        "primary_type": "development",
        "secondary_types": [],
        "confidence": "medium",
        "centipawn_loss": 200,
        "critical_moment_type": "turning_point",
    }


def test_unified_intelligence_serialization_and_fixed_query_count(api_app, api_client) -> None:
    session = api_app.state.testing_session_factory()
    game = add_game(session, "unified", opening="Caro-Kann Defense")
    game.opening_code = "B13"
    game.pgn = '[SetUp "1"]\n[FEN "rnbqkbnr/pppppppp/8/8/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1"]\n\n1. Qh5 *'
    session.flush()
    session.add(MoveAnalysis(
        game_id=game.id,
        ply=1,
        move_number=1,
        player_color=Color.WHITE,
        is_user_move=True,
        fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1",
        played_move_uci="d1h5",
        played_move_san="Qh5",
        evaluation_before_cp=20,
        evaluation_after_cp=-180,
        centipawn_loss=200,
        classification=MoveClassification.MISTAKE,
        phase=GamePhase.OPENING,
    ))
    session.commit()
    game_id = game.id
    engine = session.get_bind()
    session.close()

    statements: list[str] = []

    def count_query(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", count_query)
    try:
        response = api_client.get(f"/api/games/{game_id}/intelligence")
    finally:
        event.remove(engine, "before_cursor_execute", count_query)

    assert response.status_code == 200
    select_statements = [statement for statement in statements if statement.lstrip().upper().startswith("SELECT")]
    assert len(select_statements) == 2
    payload = response.json()
    assert payload["intelligence_version"] == "1"
    assert payload["analysis"] == {"status": "completed", "intelligence_ready": True}
    assert payload["opening"] == {"eco": "B13", "name": "Caro-Kann Defense"}
    assert payload["summary"] == {
        "average_cp_loss": 200.0,
        "user_moves": 1,
        "inaccuracies": 0,
        "mistakes": 1,
        "blunders": 0,
    }
    assert payload["phases"]["opening"]["user_moves"] == 1
    assert payload["errors"][0]["primary_type"] == "development"
    assert payload["error_breakdown"] == {"development": 1}
    assert "items" not in payload and "pgn" not in payload
    assert api_client.get("/api/games/9999/intelligence").status_code == 404


def test_moves_all_plies_sorted_and_analyze_queued(api_app, api_client, monkeypatch) -> None:
    first_id, second_id = seed(api_app)
    moves = api_client.get(f"/api/games/{first_id}/moves").json()
    assert [item["ply"] for item in moves["items"]] == [1, 2]
    assert [item["is_user_move"] for item in moves["items"]] == [True, False]
    assert moves["items"][0]["classification"] == "mistake"
    assert moves["items"][0]["phase"] == "opening"
    assert moves["items"][0]["principal_variation"] == "d4 d5"
    assert api_client.get(f"/api/games/{second_id}/moves").json()["items"] == []
    assert api_client.get("/api/games/9999/moves").status_code == 404

    queued = []
    class Queue:
        def enqueue_game_analysis(self, *, game_id, force=False):
            if game_id == 9999:
                raise PermanentAnalysisTaskError("missing")
            queued.append(game_id)
            return AnalysisEnqueueResult(game_id, "queued", "test-task")
    api_app.dependency_overrides[get_analysis_queue] = lambda: Queue()
    response = api_client.post(f"/api/games/{first_id}/analyze")
    assert response.status_code == 202
    assert response.json() == {"game_id": first_id, "status": "queued", "task_id": "test-task"}
    assert queued == [first_id]
    assert api_client.post("/api/games/9999/analyze").status_code == 404


def test_analyzing_game_is_not_queued_twice(api_app, api_client, monkeypatch) -> None:
    session = api_app.state.testing_session_factory()
    game = add_game(session, "busy", status=AnalysisStatus.ANALYZING)
    session.commit()
    game_id = game.id
    session.close()
    queued = []
    class Queue:
        def enqueue_game_analysis(self, *, game_id, force=False):
            return AnalysisEnqueueResult(game_id, "already_analyzing")
    api_app.dependency_overrides[get_analysis_queue] = lambda: Queue()

    response = api_client.post(f"/api/games/{game_id}/analyze")

    assert response.status_code == 202
    assert response.json() == {"game_id": game_id, "status": "already_analyzing", "task_id": None}
    assert queued == []
