import argparse
from collections.abc import Sequence

from sqlalchemy import exists, select

from app.database import get_session_factory
from app.models import AnalysisStatus, Game, MoveAnalysis
from app.repositories.move_analysis_repository import list_moves_for_game
from app.services.phase_backfill_service import PhaseBackfillError, assign_game_phases


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assign game phases without rerunning Stockfish")
    parser.add_argument("--apply", action="store_true", help="Commit changes; default is dry-run")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--after-id", type=int, default=0)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 500:
        parser.error("--limit must be between 1 and 500")
    if args.after_id < 0:
        parser.error("--after-id must be non-negative")

    session = get_session_factory()()
    changed_games = changed_moves = invalid = 0
    last_id = args.after_id
    try:
        needs_phase = exists().where(
            MoveAnalysis.game_id == Game.id,
            MoveAnalysis.phase.is_(None),
        )
        games = session.scalars(
            select(Game)
            .where(
                Game.id > args.after_id,
                Game.analysis_status == AnalysisStatus.COMPLETED,
                needs_phase,
            )
            .order_by(Game.id)
            .limit(args.limit)
        ).all()
        for game in games:
            last_id = game.id
            try:
                count = assign_game_phases(game, list_moves_for_game(session, game.id))
            except PhaseBackfillError as error:
                invalid += 1
                print(f"game {game.id}: skipped ({error})")
                continue
            changed_games += bool(count)
            changed_moves += count
            print(f"game {game.id}: assigned {count} phases")
        if args.apply:
            session.commit()
        else:
            session.rollback()
    finally:
        session.close()

    mode = "applied" if args.apply else "dry-run"
    print(
        f"{mode}: games={changed_games} moves={changed_moves} "
        f"invalid={invalid} last_id={last_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
