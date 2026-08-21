from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session

from app.models import (
    AnalysisStatus,
    Color,
    Game,
    GamePhase,
    MoveAnalysis,
    MoveClassification,
)


@dataclass(frozen=True)
class PlayerIntelligenceGameRow:
    id: int
    played_at: datetime | None
    user_color: str | None
    result: str | None
    pgn: str
    time_control: str | None
    opening_code: str | None = None
    opening_name: str | None = None
    total_available_analyzed_games: int = 0


@dataclass(frozen=True)
class PlayerIntelligenceMoveRow:
    game_id: int
    ply: int
    move_number: int
    player_color: Color | None
    is_user_move: bool
    fen_before: str
    played_move_uci: str
    played_move_san: str | None
    best_move_uci: str | None
    evaluation_before_cp: int | None
    evaluation_after_cp: int | None
    centipawn_loss: int | None
    classification: MoveClassification | None
    phase: GamePhase | None


def _optional_enum(value, enum_type):
    try:
        return enum_type(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def list_latest_analyzed_games(
    session: Session,
    *,
    limit: int,
) -> tuple[PlayerIntelligenceGameRow, ...]:
    """Return a deterministic bounded window plus its total count in one query."""
    statement = (
        select(
            Game.id,
            Game.played_at,
            cast(Game.user_color, String),
            cast(Game.result, String),
            Game.pgn,
            Game.time_control,
            Game.opening_code,
            Game.opening_name,
            func.count(Game.id).over(),
        )
        .where(Game.analysis_status == AnalysisStatus.COMPLETED)
        .order_by(Game.played_at.desc().nulls_last(), Game.id.desc())
        .limit(limit)
    )
    return tuple(PlayerIntelligenceGameRow(*row) for row in session.execute(statement))


def list_intelligence_moves(
    session: Session,
    game_ids: Sequence[int],
) -> tuple[PlayerIntelligenceMoveRow, ...]:
    """Load all fields needed by the profile in one query for the selected window."""
    if not game_ids:
        return ()
    statement = (
        select(
            MoveAnalysis.game_id,
            MoveAnalysis.ply,
            MoveAnalysis.move_number,
            cast(MoveAnalysis.player_color, String),
            MoveAnalysis.is_user_move,
            MoveAnalysis.fen_before,
            MoveAnalysis.played_move_uci,
            MoveAnalysis.played_move_san,
            MoveAnalysis.best_move_uci,
            MoveAnalysis.evaluation_before_cp,
            MoveAnalysis.evaluation_after_cp,
            MoveAnalysis.centipawn_loss,
            cast(MoveAnalysis.classification, String),
            cast(MoveAnalysis.phase, String),
        )
        .where(MoveAnalysis.game_id.in_(game_ids))
        .order_by(MoveAnalysis.game_id.asc(), MoveAnalysis.ply.asc())
    )
    return tuple(
        PlayerIntelligenceMoveRow(
            game_id=int(row[0]),
            ply=int(row[1]),
            move_number=int(row[2]),
            player_color=_optional_enum(row[3], Color),
            is_user_move=bool(row[4]),
            fen_before=row[5],
            played_move_uci=row[6],
            played_move_san=row[7],
            best_move_uci=row[8],
            evaluation_before_cp=row[9],
            evaluation_after_cp=row[10],
            centipawn_loss=row[11],
            classification=_optional_enum(row[12], MoveClassification),
            phase=_optional_enum(row[13], GamePhase),
        )
        for row in session.execute(statement)
    )
