from collections.abc import Callable
from dataclasses import dataclass
import threading

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AnalysisStatus
from app.repositories.games_repository import get_game_by_id, set_analysis_status
from app.repositories.move_analysis_repository import bulk_replace_move_analysis
from app.services.game_analyzer import analyze_game_moves
from app.services.stockfish_service import StockfishService


ANALYSIS_LOCK = threading.Lock()


class AnalysisServiceError(RuntimeError):
    pass


class GameNotFoundError(AnalysisServiceError):
    pass


@dataclass(frozen=True)
class AnalysisResult:
    game_id: int
    status: AnalysisStatus
    moves_analyzed: int


def create_stockfish_service() -> StockfishService:
    settings = get_settings()
    return StockfishService(
        settings.stockfish_path,
        settings.stockfish_move_time_ms,
        settings.stockfish_pv_length,
    )


def analyze_game(
    session: Session,
    game_id: int,
    stockfish_factory: Callable[[], StockfishService] = create_stockfish_service,
    *,
    analyzer=analyze_game_moves,
) -> AnalysisResult:
    game = get_game_by_id(session, game_id)
    if game is None:
        session.rollback()
        raise GameNotFoundError(f"Game {game_id} was not found")

    set_analysis_status(session, game, AnalysisStatus.ANALYZING)
    session.commit()

    try:
        with ANALYSIS_LOCK:
            with stockfish_factory() as stockfish:
                moves = analyzer(game, stockfish)

        bulk_replace_move_analysis(session, game.id, moves)
        set_analysis_status(session, game, AnalysisStatus.COMPLETED)
        session.commit()
    except Exception as error:
        session.rollback()
        failed_game = get_game_by_id(session, game_id)
        if failed_game is not None:
            set_analysis_status(session, failed_game, AnalysisStatus.FAILED)
            session.commit()
        raise AnalysisServiceError(f"Analysis failed for game {game_id}: {error}") from error

    return AnalysisResult(game.id, AnalysisStatus.COMPLETED, len(moves))
