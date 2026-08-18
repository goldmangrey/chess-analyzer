from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import AnalysisStatus, Color, Game, MoveAnalysis, MoveClassification
from app.repositories.statistics_repository import OpeningMetricsRow


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


def test_dashboard_serializes_decimal_opening_aggregates_as_json_numbers(
    api_client,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.services.statistics_service.get_opening_metrics",
        lambda *_args, **_kwargs: (
            OpeningMetricsRow(
                "B20", "Sicilian", Decimal("3"), Decimal("0"), Decimal("0"),
                Decimal("3"), Decimal("6"), Decimal("450.0"), Decimal("1"), Decimal("2"),
            ),
        ),
    )

    response = api_client.get(
        "/api/stats/dashboard?minimum_opening_games=1&weakest_openings_limit=1"
    )

    assert response.status_code == 200
    opening = response.json()["weakest_openings"][0]
    assert opening["average_cp_loss"] == 75.0
    assert opening["weakness_score"] == 127.5
    assert isinstance(opening["average_cp_loss"], float)
    assert isinstance(opening["weakness_score"], float)
