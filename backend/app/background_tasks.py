from collections.abc import Callable, Sequence
import logging

from app.database import SessionLocal
from app.dependencies import StockfishFactory
from app.services.analysis_service import analyze_game


logger = logging.getLogger(__name__)


def analyze_game_background(
    game_id: int,
    stockfish_factory: StockfishFactory,
    *,
    session_factory=SessionLocal,
    analyzer: Callable = analyze_game,
) -> None:
    session = session_factory()
    try:
        result = analyzer(session, game_id, stockfish_factory)
        logger.info(
            "Background analysis completed for game %s (%s plies)",
            game_id,
            result.moves_analyzed,
        )
    except Exception:
        session.rollback()
        logger.exception("Background analysis failed for game %s", game_id)
    finally:
        session.close()


def analyze_games_background(
    game_ids: Sequence[int],
    stockfish_factory: StockfishFactory,
    *,
    task: Callable[[int, StockfishFactory], None] = analyze_game_background,
) -> None:
    for game_id in game_ids:
        task(game_id, stockfish_factory)
