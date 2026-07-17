from collections.abc import Iterator

from app.dependencies import get_analysis_queue, get_chesscom_client
from app.queues.base import AnalysisEnqueueResult
from app.models import AnalysisStatus, Color, MoveClassification
from app.repositories.games_repository import get_game_by_id, set_analysis_status
from app.repositories.move_analysis_repository import bulk_replace_move_analysis
from app.schemas import MoveAnalysisCreate
from app.services.chesscom_client import ChessComGameRecord


PGN = '''[Event "Local flow"]
[Date "2026.07.17"]
[White "Yeskendir"]
[Black "Opponent"]
[Result "1-0"]
[ECO "C20"]
[Opening "King's Pawn Game"]

1. e4 e5 2. Nf3 Nc6 1-0
'''


class FakeChessComClient:
    def iter_recent_games(self, _username: str) -> Iterator[ChessComGameRecord]:
        yield ChessComGameRecord("https://chess.com/game/flow", "flow", PGN, 1)


def test_local_api_flow_without_network_or_stockfish(api_app, api_client, monkeypatch) -> None:
    api_app.dependency_overrides[get_chesscom_client] = lambda: FakeChessComClient()
    analysis_runs = []

    def fake_analysis(game_ids, _factory) -> None:
        for game_id in game_ids:
            session = api_app.state.testing_session_factory()
            try:
                game = get_game_by_id(session, game_id)
                assert game is not None
                moves = (
                    MoveAnalysisCreate(game_id=game_id, ply=1, move_number=1, player_color=Color.WHITE, is_user_move=True, fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", played_move_uci="e2e4", played_move_san="e4", best_move_uci="e2e4", best_move_san="e4", evaluation_before_cp=20, evaluation_after_cp=15, centipawn_loss=5, classification=MoveClassification.NORMAL, principal_variation="e4 e5"),
                    MoveAnalysisCreate(game_id=game_id, ply=2, move_number=1, player_color=Color.BLACK, is_user_move=False, fen_before="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1", played_move_uci="e7e5", played_move_san="e5", best_move_uci="c7c5", best_move_san="c5", evaluation_before_cp=15, evaluation_after_cp=100, centipawn_loss=85, classification=MoveClassification.INACCURACY, principal_variation="c5 Nf3"),
                    MoveAnalysisCreate(game_id=game_id, ply=3, move_number=2, player_color=Color.WHITE, is_user_move=True, fen_before="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", played_move_uci="g1f3", played_move_san="Nf3", best_move_uci="g1f3", best_move_san="Nf3", evaluation_before_cp=100, evaluation_after_cp=-20, centipawn_loss=120, classification=MoveClassification.MISTAKE, principal_variation="Nf3 Nc6"),
                    MoveAnalysisCreate(game_id=game_id, ply=4, move_number=2, player_color=Color.BLACK, is_user_move=False, fen_before="rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2", played_move_uci="b8c6", played_move_san="Nc6", best_move_uci="g8f6", best_move_san="Nf6", evaluation_before_cp=-20, evaluation_after_cp=500, centipawn_loss=520, classification=MoveClassification.BLUNDER, principal_variation="Nf6"),
                )
                bulk_replace_move_analysis(session, game_id, moves)
                set_analysis_status(session, game, AnalysisStatus.COMPLETED)
                session.commit()
                analysis_runs.append(game_id)
            finally:
                session.close()

    class Queue:
        def enqueue_game_analysis(self, *, game_id, force=False):
            fake_analysis((game_id,), None)
            return AnalysisEnqueueResult(game_id, "queued")
    api_app.dependency_overrides[get_analysis_queue] = lambda: Queue()

    imported = api_client.post("/api/import/chess-com", json={"analyze": True})
    assert imported.status_code == 200
    game_id = imported.json()["imported_game_ids"][0]
    assert analysis_runs == [game_id]
    assert api_client.post("/api/import/chess-com", json={"analyze": False}).json()["imported"] == 0

    dashboard = api_client.get("/api/stats/dashboard").json()
    assert dashboard["summary"]["total_games"] == 1
    assert dashboard["summary"]["average_cp_loss"] == 62.5
    assert dashboard["summary"]["blunders_total"] == 0
    assert api_client.get("/api/games").json()["items"][0]["id"] == game_id
    detail = api_client.get(f"/api/games/{game_id}").json()
    assert detail["analysis_status"] == "completed" and detail["mistakes"] == 1
    moves = api_client.get(f"/api/games/{game_id}/moves").json()["items"]
    assert [move["player_color"] for move in moves] == ["white", "black", "white", "black"]
    assert len(moves) == 4

    fake_analysis((game_id,), None)
    assert len(api_client.get(f"/api/games/{game_id}/moves").json()["items"]) == 4
