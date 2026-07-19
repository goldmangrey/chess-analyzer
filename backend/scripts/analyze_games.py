import argparse
from collections.abc import Callable, Sequence
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings, get_settings
from app.database import get_session_factory, init_db
from app.models import AnalysisStatus, Game
from app.repositories.games_repository import (
    get_game_by_id,
    list_games_by_analysis_status,
)
from app.services.analysis_service import (
    AnalysisResult,
    AnalysisServiceError,
    GameNotFoundError,
    analyze_game,
)


def main(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
    session_factory=None,
    init_database: Callable[[], None] = init_db,
    analyzer: Callable[..., AnalysisResult] = analyze_game,
) -> int:
    active_settings = settings or get_settings()
    active_session_factory = session_factory or get_session_factory(active_settings)
    parser = argparse.ArgumentParser(description="Analyze games with local Stockfish")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--pending", action="store_true")
    selection.add_argument("--failed", action="store_true")
    selection.add_argument("--game-id", type=int)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")

    session = None
    completed = failed = 0
    try:
        init_database()
        session = active_session_factory()
        games: list[Game]
        if args.game_id is not None:
            game = get_game_by_id(session, args.game_id)
            games = [game] if game is not None else []
            session.rollback()
            if not games:
                raise GameNotFoundError(f"Game {args.game_id} was not found")
        else:
            status = AnalysisStatus.FAILED if args.failed else AnalysisStatus.PENDING
            games = list_games_by_analysis_status(session, status, limit=args.limit)
            session.rollback()

        for game in games:
            print(f"Analyzing game {game.id}...")
            try:
                result = analyzer(session, game.id)
            except AnalysisServiceError as error:
                failed += 1
                print(f"Failed: {error}", file=sys.stderr)
                if "not found" in str(error).lower() or "not executable" in str(error).lower():
                    print(
                        f"Check STOCKFISH_PATH ({active_settings.stockfish_path})",
                        file=sys.stderr,
                    )
                continue
            completed += 1
            print(f"Completed: {result.moves_analyzed} plies")
    except (AnalysisServiceError, SQLAlchemyError) as error:
        print(f"Analysis failed: {error}", file=sys.stderr)
        return 1
    finally:
        if session is not None:
            session.close()

    print("\nSummary:")
    print(f"Completed: {completed}")
    print(f"Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
