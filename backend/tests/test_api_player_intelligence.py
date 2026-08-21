from datetime import datetime, timezone
from io import StringIO

import chess
import chess.pgn
import pytest

from app.models import (
    AnalysisStatus,
    Color,
    Game,
    GamePhase,
    GameResult,
    MoveAnalysis,
    MoveClassification,
)
from app.services.error_taxonomy_classifier import ErrorTaxonomyClassifier


def _seed_completed_game(api_app) -> None:
    with api_app.state.testing_session_factory() as session:
        game = Game(
            external_id="api-player-intelligence",
            played_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            white_username="user",
            black_username="opponent",
            user_color=Color.WHITE,
            result=GameResult.WIN,
            pgn="1. e4 *",
            analysis_status=AnalysisStatus.COMPLETED,
        )
        session.add(game)
        session.flush()
        session.add(
            MoveAnalysis(
                game_id=game.id,
                ply=1,
                move_number=1,
                player_color=Color.WHITE,
                is_user_move=True,
                fen_before="start",
                played_move_uci="e2e4",
                evaluation_before_cp=0,
                evaluation_after_cp=-80,
                centipawn_loss=80,
                classification=MoveClassification.INACCURACY,
            )
        )
        session.commit()


def _seed_recurring_development_games(api_app) -> None:
    pgn = '[Result "*"]\n\n1. e4 e5 2. Qh5 *'
    for game_index in (1, 2):
        parsed = chess.pgn.read_game(StringIO(pgn))
        assert parsed is not None
        board = parsed.board()
        with api_app.state.testing_session_factory() as session:
            game = Game(
                external_id=f"recurring-development-{game_index}",
                played_at=datetime(2026, 2, game_index, tzinfo=timezone.utc),
                white_username="user",
                black_username="opponent",
                user_color=Color.WHITE,
                result=GameResult.LOSS,
                pgn=pgn,
                analysis_status=AnalysisStatus.COMPLETED,
            )
            session.add(game)
            session.flush()
            for ply, move in enumerate(parsed.mainline_moves(), 1):
                target = ply == 3
                session.add(
                    MoveAnalysis(
                        game_id=game.id,
                        ply=ply,
                        move_number=(ply + 1) // 2,
                        player_color=Color.WHITE if board.turn else Color.BLACK,
                        is_user_move=board.turn == chess.WHITE,
                        fen_before=board.fen(),
                        played_move_uci=move.uci(),
                        played_move_san=board.san(move),
                        evaluation_before_cp=0,
                        evaluation_after_cp=-200 if target else 0,
                        centipawn_loss=200 if target else 0,
                        classification=(
                            MoveClassification.MISTAKE
                            if target
                            else MoveClassification.NORMAL
                        ),
                        phase=GamePhase.OPENING,
                    )
                )
                board.push(move)
            session.commit()


def test_api_default_window_and_version(api_client, api_app):
    _seed_completed_game(api_app)

    response = api_client.get("/api/player/intelligence")

    assert response.status_code == 200
    body = response.json()
    assert body["intelligence_version"] == "1"
    assert body["window"] == {
        "requested_games": 30,
        "available_analyzed_games": 1,
        "selected_games": 1,
        "total_available_analyzed_games": 1,
    }
    assert body["sample"]["games"] == 1
    assert body["overall"]["average_cp_loss"] == 80.0
    assert body["data_quality"]["games_with_taxonomy_data"] == 0
    assert body["data_quality"]["moves_eligible_for_taxonomy"] == 0
    assert body["recurring_errors"] == []
    assert body["weaknesses"] == []
    assert all(item["confidence"]["level"] == "insufficient" for item in body["strengths"])
    assert set(body["phases"]) == {"opening", "middlegame", "endgame"}
    assert all(item["user_moves"] == 0 for item in body["phases"].values())
    assert body["data_quality"]["moves_with_phase"] == 0
    assert body["data_quality"]["moves_without_phase"] == 1
    assert body["phase_profile"]["strongest_phase"] is None
    assert body["phase_profile"]["weakest_phase"] is None
    assert body["trends"]["recent_games"] == 1
    assert body["trends"]["previous_games"] == 0
    assert body["trends"]["overall"]["average_cp_loss"]["direction"] == "insufficient"
    assert set(body["segments"]["time_controls"]) == {"bullet", "blitz", "rapid", "unknown"}
    assert set(body["segments"]["colors"]) == {"white", "black"}
    assert body["summary"]["status"] == "insufficient"
    assert body["summary"]["overall_direction"] == "insufficient"
    assert body["openings"]["selected_games"] == 1
    assert body["openings"]["games_with_recognized_opening"] == 1
    assert body["openings"]["recognition_coverage_rate"] == 1.0
    assert body["openings"]["top"][0]["name"] == "King's Pawn Game"


def test_api_empty_profile_serializes_empty_conclusions(api_client):
    response = api_client.get("/api/player/intelligence")

    assert response.status_code == 200
    body = response.json()
    assert body["recurring_errors"] == []
    assert body["weaknesses"] == []
    assert body["strengths"] == []
    assert body["data_quality"]["moves_with_phase"] == 0
    assert body["data_quality"]["moves_without_phase"] == 0
    assert body["phase_profile"]["first_serious_breakdown"]["eligible_games"] == 0
    assert body["trends"]["recent_games"] == 0
    assert body["trends"]["previous_games"] == 0
    assert all(item["games"] == 0 for item in body["segments"]["time_controls"].values())
    assert body["openings"] == {
        "selected_games": 0,
        "games_with_recognized_opening": 0,
        "games_with_opening_identity": 0,
        "recognition_coverage_rate": None,
        "top": [],
        "by_color": {"white": [], "black": []},
    }
    assert body["summary"] == {
        "status": "insufficient",
        "main_weakness": None,
        "main_strength": None,
        "strongest_phase": None,
        "weakest_phase": None,
        "overall_direction": "insufficient",
        "confidence": {"level": "insufficient", "score": 0.0},
    }


def test_api_custom_window(api_client, api_app):
    _seed_completed_game(api_app)

    response = api_client.get("/api/player/intelligence?window=10")

    assert response.status_code == 200
    assert response.json()["window"]["requested_games"] == 10


def test_window_preserves_selected_alias_and_reports_total_available(api_client, api_app):
    _seed_recurring_development_games(api_app)

    response = api_client.get("/api/player/intelligence?window=1")

    assert response.status_code == 200
    window = response.json()["window"]
    assert window["available_analyzed_games"] == 1
    assert window["selected_games"] == 1
    assert window["total_available_analyzed_games"] == 2


def test_api_returns_runtime_canonical_recurring_taxonomy(api_client, api_app):
    _seed_recurring_development_games(api_app)

    response = api_client.get("/api/player/intelligence?window=10")

    assert response.status_code == 200
    body = response.json()
    assert body["data_quality"]["games_with_taxonomy_data"] == 2
    assert body["data_quality"]["moves_eligible_for_taxonomy"] == 4
    assert body["data_quality"]["moves_with_primary_taxonomy"] == 2
    assert len(body["recurring_errors"]) == 1
    recurring = body["recurring_errors"][0]
    assert recurring["taxonomy"] == "development"
    assert recurring["incidents"] == 2
    assert recurring["games_affected"] == 2
    assert recurring["severity"]["mistakes"] == 2
    assert [item["ply"] for item in recurring["evidence"]] == [3, 3]
    assert len(body["weaknesses"]) == 1
    weakness = body["weaknesses"][0]
    assert weakness["taxonomy"] == "development"
    assert weakness["rank"] == 1
    assert weakness["confidence"]["level"] == "insufficient"
    assert weakness["evidence"] == recurring["evidence"]
    assert body["strengths"]
    opening = body["phases"]["opening"]
    assert opening["user_moves"] == 4
    assert opening["games_with_phase"] == 2
    assert opening["mistakes"] == 2
    breakdown = body["phase_profile"]["first_serious_breakdown"]
    assert breakdown["eligible_games"] == 2
    assert breakdown["games_with_serious_error"] == 2
    assert breakdown["opening"] == 2
    assert breakdown["opening_share"] == 1.0


def test_taxonomy_classifier_failure_is_isolated_from_basic_profile(
    api_client,
    api_app,
    monkeypatch,
):
    _seed_recurring_development_games(api_app)

    def fail(*_args, **_kwargs):
        raise ValueError("legacy taxonomy failure")

    monkeypatch.setattr(ErrorTaxonomyClassifier, "classify_prepared", fail)
    response = api_client.get("/api/player/intelligence")

    assert response.status_code == 200
    assert response.json()["sample"]["games"] == 2
    assert response.json()["data_quality"]["games_with_taxonomy_data"] == 0
    assert response.json()["recurring_errors"] == []


def test_taxonomy_reconstruction_runs_once_per_union_game(
    api_client,
    api_app,
    monkeypatch,
):
    _seed_recurring_development_games(api_app)
    original = ErrorTaxonomyClassifier.classify_prepared
    calls = 0

    def count(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(ErrorTaxonomyClassifier, "classify_prepared", count)
    response = api_client.get("/api/player/intelligence?window=1")

    assert response.status_code == 200
    assert response.json()["sample"]["games"] == 1
    assert response.json()["trends"]["previous_games"] == 1
    assert calls == 2


@pytest.mark.parametrize("window", [0, 101, "invalid"])
def test_api_rejects_invalid_window(api_client, window):
    response = api_client.get(f"/api/player/intelligence?window={window}")

    assert response.status_code == 422
