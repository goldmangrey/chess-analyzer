"""Add persisted game phase to move analysis.

Revision ID: 0002_add_move_analysis_phase
Revises: 0001_initial_schema
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_move_analysis_phase"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("move_analysis") as batch_op:
        batch_op.add_column(sa.Column("phase", sa.String(20), nullable=True))
        batch_op.create_check_constraint(
            "ck_move_analysis_game_phase",
            "phase IS NULL OR phase IN ('opening', 'middlegame', 'endgame')",
        )


def downgrade() -> None:
    with op.batch_alter_table("move_analysis") as batch_op:
        batch_op.drop_constraint("ck_move_analysis_game_phase", type_="check")
        batch_op.drop_column("phase")
