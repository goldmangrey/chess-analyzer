from collections.abc import Callable, Sequence
import logging
import threading

from app.database import SessionLocal
from app.dependencies import StockfishFactory
from app.services.analysis_service import analyze_game


logger = logging.getLogger(__name__)
_queue_lock = threading.Lock()
_queued_game_ids: set[int] = set()


def reserve_analysis(game_id: int) -> bool:
    """Reserve a game for this process; return False when already queued."""
    with _queue_lock:
        if game_id in _queued_game_ids:
            return False
        _queued_game_ids.add(game_id)
        return True


def release_analysis(game_id: int) -> None:
    with _queue_lock:
        _queued_game_ids.discard(game_id)


def analyze_game_background(
    game_id: int,
    stockfish_factory: StockfishFactory,
    *,
    session_factory=SessionLocal,
    analyzer: Callable = analyze_game,
) -> None:
    session = session_factory()
    try:
        logger.info("Background analysis started for game %s", game_id)
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
        release_analysis(game_id)


def analyze_games_background(
    game_ids: Sequence[int],
    stockfish_factory: StockfishFactory,
    *,
    task: Callable[[int, StockfishFactory], None] = analyze_game_background,
) -> None:
    for game_id in game_ids:
        task(game_id, stockfish_factory)
