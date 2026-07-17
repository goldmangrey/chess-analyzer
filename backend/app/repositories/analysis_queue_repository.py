from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Game


ADVISORY_LOCK_NAMESPACE = 0x43484149


def get_game_for_update(session: Session, game_id: int) -> Game | None:
    return session.scalar(select(Game).where(Game.id == game_id).with_for_update())


def try_acquire_execution_lock(session: Session, game_id: int) -> bool:
    if session.bind and session.bind.dialect.name == "postgresql":
        acquired = session.scalar(text("SELECT pg_try_advisory_lock(:namespace, :game_id)"), {"namespace": ADVISORY_LOCK_NAMESPACE, "game_id": game_id})
        session.commit()
        return bool(acquired)
    return True


def release_execution_lock(session: Session, game_id: int) -> None:
    if session.bind and session.bind.dialect.name == "postgresql":
        session.scalar(text("SELECT pg_advisory_unlock(:namespace, :game_id)"), {"namespace": ADVISORY_LOCK_NAMESPACE, "game_id": game_id})
        session.commit()
