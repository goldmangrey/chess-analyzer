import argparse
from collections.abc import Sequence

from sqlalchemy import or_, select

from app.database import get_session_factory
from app.models import Game
from app.services.opening_backfill_service import refresh_game_opening
from app.services.pgn_parser import PgnParseError


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve opening metadata from saved PGNs")
    parser.add_argument("--apply", action="store_true", help="Commit changes; default is dry-run")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--after-id", type=int, default=0)
    parser.add_argument("--all", action="store_true", help="Also revisit games that already have a name")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 500:
        parser.error("--limit must be between 1 and 500")
    if args.after_id < 0:
        parser.error("--after-id must be non-negative")

    session = get_session_factory()()
    changed = unchanged = invalid = 0
    last_id = args.after_id
    try:
        statement = select(Game).where(Game.id > args.after_id)
        if not args.all:
            statement = statement.where(
                or_(Game.opening_name.is_(None), Game.opening_name == "")
            )
        games = session.scalars(statement.order_by(Game.id).limit(args.limit)).all()
        for game in games:
            last_id = game.id
            try:
                was_changed = refresh_game_opening(game)
            except PgnParseError as error:
                invalid += 1
                print(f"game {game.id}: skipped invalid PGN ({error})")
                continue
            if was_changed:
                changed += 1
                print(f"game {game.id}: {game.opening_code or '-'} | {game.opening_name or '-'}")
            else:
                unchanged += 1
        if args.apply:
            session.commit()
        else:
            session.rollback()
    finally:
        session.close()

    mode = "applied" if args.apply else "dry-run"
    print(f"{mode}: changed={changed} unchanged={unchanged} invalid={invalid} last_id={last_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
