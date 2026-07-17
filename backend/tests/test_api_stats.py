from sqlalchemy.orm import Session

from app.models import AnalysisStatus, Color, Game, MoveAnalysis, MoveClassification


def seed_stats(api_app) -> None:
    session: Session = api_app.state.testing_session_factory()
    game = Game(
        external_id="stats",
        white_username="User",
        black_username="Opponent",
        user_color=Color.WHITE,
        result="loss",
        opening_code="B20",
        opening_name="Sicilian",
        pgn="pgn",
        analysis_status=AnalysisStatus.COMPLETED,
    )
    session.add(game)
    session.flush()
    session.add_all([
        MoveAnalysis(
            game_id=game.id, ply=1, move_number=1, player_color=Color.WHITE,
            is_user_move=True, fen_before="fen", played_move_uci="e2e4",
            centipawn_loss=100, classification=MoveClassification.MISTAKE,
        ),
        MoveAnalysis(
            game_id=game.id, ply=2, move_number=1, player_color=Color.BLACK,
            is_user_move=False, fen_before="fen", played_move_uci="e7e5",
            centipawn_loss=9999, classification=MoveClassification.BLUNDER,
        ),
    ])
    session.commit()
    session.close()


def test_empty_stats_nulls_and_query_validation(api_client) -> None:
    summary = api_client.get("/api/stats/summary")
    assert summary.status_code == 200
    assert summary.json()["average_cp_loss"] is None
    dashboard = api_client.get("/api/stats/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["summary"]["total_games"] == 0
    for path in (
        "/api/stats/trends?limit=0",
        "/api/stats/openings?minimum_games=0",
        "/api/stats/openings?limit=51",
        "/api/stats/performance?period_size=0",
        "/api/stats/dashboard?trend_limit=101",
    ):
        assert api_client.get(path).status_code == 422


def test_stats_endpoints_real_metrics_and_opponent_isolation(api_app, api_client) -> None:
    seed_stats(api_app)
    summary = api_client.get("/api/stats/summary").json()
    assert summary["average_cp_loss"] == 100.0
    assert (summary["mistakes_total"], summary["blunders_total"]) == (1, 0)
    assert api_client.get("/api/stats/trends?limit=1").json()["items"][0]["blunders"] == 0
    openings = api_client.get("/api/stats/openings?minimum_games=1&limit=1")
    assert openings.status_code == 200 and openings.json()["items"][0]["opening_code"] == "B20"
    performance = api_client.get("/api/stats/performance?period_size=1")
    assert performance.status_code == 200
    dashboard = api_client.get(
        "/api/stats/dashboard?minimum_opening_games=1&weakest_openings_limit=1"
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["recent_games"][0]["blunders"] == 0
