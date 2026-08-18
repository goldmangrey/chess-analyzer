from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session

from app.models import GamePhase, MoveAnalysis, MoveClassification
from app.schemas import MoveAnalysisCreate


@dataclass(frozen=True)
class PersonalMoveAggregates:
    move_count: int
    average_cp_loss: float | None
    normal_count: int
    inaccuracies_count: int
    mistakes_count: int
    blunders_count: int
    total_cp_loss: int


@dataclass(frozen=True)
class PhaseMoveAggregates:
    phase: GamePhase
    start_ply: int
    end_ply: int
    user_moves: int
    average_cp_loss: float | None
    inaccuracies: int
    mistakes: int
    blunders: int


def create_move_analysis(
    session: Session,
    data: MoveAnalysisCreate,
) -> MoveAnalysis:
    move = MoveAnalysis(**data.model_dump())
    session.add(move)
    session.flush()
    return move


def list_moves_for_game(session: Session, game_id: int) -> list[MoveAnalysis]:
    statement = (
        select(MoveAnalysis)
        .where(MoveAnalysis.game_id == game_id)
        .order_by(MoveAnalysis.ply.asc())
    )
    return list(session.scalars(statement).all())


def list_user_moves_for_game(session: Session, game_id: int) -> list[MoveAnalysis]:
    statement = (
        select(MoveAnalysis)
        .where(
            MoveAnalysis.game_id == game_id,
            MoveAnalysis.is_user_move.is_(True),
        )
        .order_by(MoveAnalysis.ply.asc())
    )
    return list(session.scalars(statement).all())


def delete_analysis_for_game(session: Session, game_id: int) -> int:
    result = session.execute(
        delete(MoveAnalysis).where(MoveAnalysis.game_id == game_id)
    )
    return int(result.rowcount or 0)


def bulk_replace_move_analysis(
    session: Session,
    game_id: int,
    moves: Sequence[MoveAnalysisCreate],
) -> list[MoveAnalysis]:
    """Replace all moves and flush, leaving commit/rollback to the caller.

    The caller must provide a transaction boundary. If flush fails, rolling back
    that transaction restores the deleted rows and removes partial inserts.
    """
    mismatched = [move.game_id for move in moves if move.game_id != game_id]
    if mismatched:
        raise ValueError("all moves must belong to the requested game_id")

    delete_analysis_for_game(session, game_id)
    replacements = [MoveAnalysis(**move.model_dump()) for move in moves]
    session.add_all(replacements)
    session.flush()
    return replacements


def get_personal_aggregates(
    session: Session,
    game_id: int,
) -> PersonalMoveAggregates:
    statement = select(
        func.count(MoveAnalysis.id),
        func.avg(MoveAnalysis.centipawn_loss),
        func.coalesce(func.sum(MoveAnalysis.centipawn_loss), 0),
        *[
            func.coalesce(
                func.sum(case((MoveAnalysis.classification == classification, 1), else_=0)),
                0,
            )
            for classification in MoveClassification
        ],
    ).where(
        MoveAnalysis.game_id == game_id,
        MoveAnalysis.is_user_move.is_(True),
    )
    row = session.execute(statement).one()
    return PersonalMoveAggregates(
        move_count=int(row[0]),
        average_cp_loss=float(row[1]) if row[1] is not None else None,
        total_cp_loss=int(row[2]),
        normal_count=int(row[3]),
        inaccuracies_count=int(row[4]),
        mistakes_count=int(row[5]),
        blunders_count=int(row[6]),
    )


def get_classification_counts(
    session: Session,
    game_id: int,
    *,
    user_moves_only: bool = True,
) -> dict[str, int]:
    statement = (
        select(MoveAnalysis.classification, func.count(MoveAnalysis.id))
        .where(MoveAnalysis.game_id == game_id)
        .group_by(MoveAnalysis.classification)
    )
    if user_moves_only:
        statement = statement.where(MoveAnalysis.is_user_move.is_(True))

    found = {classification.value: count for classification, count in session.execute(statement)}
    return {classification.value: int(found.get(classification.value, 0)) for classification in MoveClassification}


def get_phase_aggregates(
    session: Session,
    game_id: int,
) -> tuple[PhaseMoveAggregates, ...]:
    is_user = MoveAnalysis.is_user_move.is_(True)
    statement = (
        select(
            MoveAnalysis.phase,
            func.min(MoveAnalysis.ply),
            func.max(MoveAnalysis.ply),
            func.sum(case((is_user, 1), else_=0)),
            func.avg(case((is_user, MoveAnalysis.centipawn_loss))),
            *[
                func.sum(
                    case(
                        (
                            is_user & (MoveAnalysis.classification == classification),
                            1,
                        ),
                        else_=0,
                    )
                )
                for classification in (
                    MoveClassification.INACCURACY,
                    MoveClassification.MISTAKE,
                    MoveClassification.BLUNDER,
                )
            ],
        )
        .where(MoveAnalysis.game_id == game_id, MoveAnalysis.phase.is_not(None))
        .group_by(MoveAnalysis.phase)
        .order_by(func.min(MoveAnalysis.ply))
    )
    return tuple(
        PhaseMoveAggregates(
            phase=GamePhase(row[0]),
            start_ply=int(row[1]),
            end_ply=int(row[2]),
            user_moves=int(row[3]),
            average_cp_loss=float(row[4]) if row[4] is not None else None,
            inaccuracies=int(row[5]),
            mistakes=int(row[6]),
            blunders=int(row[7]),
        )
        for row in session.execute(statement)
    )
