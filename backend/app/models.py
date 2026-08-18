from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Color(str, Enum):
    WHITE = "white"
    BLACK = "black"


class GameResult(str, Enum):
    WIN = "win"
    DRAW = "draw"
    LOSS = "loss"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class MoveClassification(str, Enum):
    NORMAL = "normal"
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    BLUNDER = "blunder"


class GamePhase(str, Enum):
    OPENING = "opening"
    MIDDLEGAME = "middlegame"
    ENDGAME = "endgame"


class CriticalMomentType(str, Enum):
    TURNING_POINT = "turning_point"
    BLUNDER = "blunder"
    MISSED_OPPORTUNITY = "missed_opportunity"
    MISSED_MATE = "missed_mate"
    ALLOWED_MATE = "allowed_mate"
    BEST_MOVE = "best_move"


class ErrorType(str, Enum):
    HANGING_PIECE = "hanging_piece"
    MISSED_CAPTURE = "missed_capture"
    MISSED_CHECK = "missed_check"
    MISSED_MATE = "missed_mate"
    ALLOWED_MATE = "allowed_mate"
    KING_SAFETY = "king_safety"
    DEVELOPMENT = "development"
    BAD_EXCHANGE = "bad_exchange"
    PAWN_STRUCTURE = "pawn_structure"
    TACTICAL_PATTERN = "tactical_pattern"
    FORK = "fork"
    PIN = "pin"
    SKEWER = "skewer"
    BACK_RANK = "back_rank"


class ErrorConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SyncStatus(str, Enum):
    NEVER = "never"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def enum_type(enum_class: type[Enum], name: str) -> SqlEnum:
    return SqlEnum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
    )


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    platform: Mapped[str] = mapped_column(
        String(50), default="chess.com", nullable=False
    )
    played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    white_username: Mapped[str] = mapped_column(String(255), nullable=False)
    black_username: Mapped[str] = mapped_column(String(255), nullable=False)
    white_rating: Mapped[int | None] = mapped_column(Integer)
    black_rating: Mapped[int | None] = mapped_column(Integer)
    user_color: Mapped[Color] = mapped_column(
        enum_type(Color, "game_user_color"), nullable=False
    )
    result: Mapped[GameResult] = mapped_column(
        enum_type(GameResult, "game_result"), nullable=False
    )
    time_control: Mapped[str | None] = mapped_column(String(50))
    opening_code: Mapped[str | None] = mapped_column(String(20))
    opening_name: Mapped[str | None] = mapped_column(String(255))
    pgn: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_status: Mapped[AnalysisStatus] = mapped_column(
        enum_type(AnalysisStatus, "game_analysis_status"),
        default=AnalysisStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    move_analyses: Mapped[list["MoveAnalysis"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="MoveAnalysis.ply",
    )


class MoveAnalysis(Base):
    __tablename__ = "move_analysis"
    __table_args__ = (
        CheckConstraint("ply >= 1", name="ck_move_analysis_ply_positive"),
        CheckConstraint(
            "move_number >= 1", name="ck_move_analysis_move_number_positive"
        ),
        CheckConstraint(
            "centipawn_loss >= 0",
            name="ck_move_analysis_centipawn_loss_nonnegative",
        ),
        UniqueConstraint("game_id", "ply", name="uq_move_analysis_game_ply"),
        Index("ix_move_analysis_game_id", "game_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    ply: Mapped[int] = mapped_column(Integer, nullable=False)
    move_number: Mapped[int] = mapped_column(Integer, nullable=False)
    player_color: Mapped[Color] = mapped_column(
        enum_type(Color, "move_player_color"), nullable=False
    )
    is_user_move: Mapped[bool] = mapped_column(Boolean, nullable=False)
    fen_before: Mapped[str] = mapped_column(Text, nullable=False)
    played_move_uci: Mapped[str] = mapped_column(String(10), nullable=False)
    played_move_san: Mapped[str | None] = mapped_column(String(20))
    best_move_uci: Mapped[str | None] = mapped_column(String(10))
    best_move_san: Mapped[str | None] = mapped_column(String(20))
    evaluation_before_cp: Mapped[int | None] = mapped_column(Integer)
    evaluation_after_cp: Mapped[int | None] = mapped_column(Integer)
    centipawn_loss: Mapped[int] = mapped_column(Integer, nullable=False)
    classification: Mapped[MoveClassification] = mapped_column(
        enum_type(MoveClassification, "move_classification"), nullable=False
    )
    phase: Mapped[GamePhase | None] = mapped_column(
        enum_type(GamePhase, "game_phase"), nullable=True
    )
    principal_variation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    game: Mapped[Game] = relationship(back_populates="move_analyses")


class AppSettings(Base):
    __tablename__ = "app_settings"
    __table_args__ = (CheckConstraint("id = 1", name="ck_app_settings_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    chesscom_username: Mapped[str | None] = mapped_column(String(255))
    auto_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_analyze_latest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    initial_sync_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_sync_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_status: Mapped[SyncStatus] = mapped_column(
        enum_type(SyncStatus, "app_settings_sync_status"),
        default=SyncStatus.NEVER,
        nullable=False,
    )
    last_sync_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
