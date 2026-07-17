import argparse
from collections.abc import Callable, Sequence
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings, get_settings
from app.database import SessionLocal, init_db
from app.services.chesscom_client import ChessComClient, ChessComError
from app.services.game_importer import ImportGamesResult, import_recent_games


def main(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
    session_factory=SessionLocal,
    client_factory: Callable[[str], ChessComClient] | None = None,
    init_database: Callable[[], None] = init_db,
    importer: Callable[..., ImportGamesResult] = import_recent_games,
) -> int:
    active_settings = settings or get_settings()
    parser = argparse.ArgumentParser(description="Import recent Chess.com games")
    parser.add_argument("--username", default=active_settings.chess_username)
    parser.add_argument("--limit", type=int, default=active_settings.import_games_limit)
    args = parser.parse_args(argv)

    session = None
    client = None
    try:
        init_database()
        session = session_factory()
        factory = client_factory or (lambda user_agent: ChessComClient(user_agent))
        client = factory(active_settings.chesscom_user_agent)
        result = importer(session, client, args.username, args.limit)
        session.commit()
    except (ChessComError, SQLAlchemyError, ValueError) as error:
        if session is not None:
            session.rollback()
        print(f"Import failed: {error}", file=sys.stderr)
        return 1
    finally:
        if client is not None:
            client.close()
        if session is not None:
            session.close()

    print(f"Imported: {result.imported}")
    print(f"Duplicates: {result.skipped_duplicates}")
    print(f"Invalid: {result.skipped_invalid}")
    print(f"Examined: {result.examined}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
