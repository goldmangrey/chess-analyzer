"""Initial games, move analysis, and application settings schema."""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def string_enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True)


def upgrade() -> None:
    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("played_at", sa.DateTime(timezone=True)),
        sa.Column("white_username", sa.String(255), nullable=False),
        sa.Column("black_username", sa.String(255), nullable=False),
        sa.Column("white_rating", sa.Integer()), sa.Column("black_rating", sa.Integer()),
        sa.Column("user_color", string_enum("game_user_color", "white", "black"), nullable=False),
        sa.Column("result", string_enum("game_result", "win", "draw", "loss"), nullable=False),
        sa.Column("time_control", sa.String(50)), sa.Column("opening_code", sa.String(20)),
        sa.Column("opening_name", sa.String(255)), sa.Column("pgn", sa.Text(), nullable=False),
        sa.Column("analysis_status", string_enum("game_analysis_status", "pending", "analyzing", "completed", "failed"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id", name="pk_games"),
    )
    op.create_index("ix_games_external_id", "games", ["external_id"], unique=True)
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("chesscom_username", sa.String(255)),
        sa.Column("auto_sync_enabled", sa.Boolean(), nullable=False), sa.Column("auto_analyze_latest", sa.Boolean(), nullable=False),
        sa.Column("initial_sync_completed", sa.Boolean(), nullable=False), sa.Column("last_sync_started_at", sa.DateTime(timezone=True)),
        sa.Column("last_sync_completed_at", sa.DateTime(timezone=True)),
        sa.Column("last_sync_status", string_enum("app_settings_sync_status", "never", "running", "completed", "failed"), nullable=False),
        sa.Column("last_sync_error", sa.String(500)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_app_settings_singleton"), sa.PrimaryKeyConstraint("id", name="pk_app_settings"),
    )
    op.create_table(
        "move_analysis",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("ply", sa.Integer(), nullable=False), sa.Column("move_number", sa.Integer(), nullable=False),
        sa.Column("player_color", string_enum("move_player_color", "white", "black"), nullable=False),
        sa.Column("is_user_move", sa.Boolean(), nullable=False), sa.Column("fen_before", sa.Text(), nullable=False),
        sa.Column("played_move_uci", sa.String(10), nullable=False), sa.Column("played_move_san", sa.String(20)),
        sa.Column("best_move_uci", sa.String(10)), sa.Column("best_move_san", sa.String(20)),
        sa.Column("evaluation_before_cp", sa.Integer()), sa.Column("evaluation_after_cp", sa.Integer()),
        sa.Column("centipawn_loss", sa.Integer(), nullable=False),
        sa.Column("classification", string_enum("move_classification", "normal", "inaccuracy", "mistake", "blunder"), nullable=False),
        sa.Column("principal_variation", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("ply >= 1", name="ck_move_analysis_ply_positive"),
        sa.CheckConstraint("move_number >= 1", name="ck_move_analysis_move_number_positive"),
        sa.CheckConstraint("centipawn_loss >= 0", name="ck_move_analysis_centipawn_loss_nonnegative"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], name="fk_move_analysis_game_id_games", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_move_analysis"),
        sa.UniqueConstraint("game_id", "ply", name="uq_move_analysis_game_ply"),
    )
    op.create_index("ix_move_analysis_game_id", "move_analysis", ["game_id"])


def downgrade() -> None:
    op.drop_index("ix_move_analysis_game_id", table_name="move_analysis")
    op.drop_table("move_analysis")
    op.drop_table("app_settings")
    op.drop_index("ix_games_external_id", table_name="games")
    op.drop_table("games")
