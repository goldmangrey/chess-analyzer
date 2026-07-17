from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.database import Base
from app.models import Game
from app.repositories import statistics_repository


def test_metadata_has_three_portable_domain_tables_and_named_constraints() -> None:
    assert set(Base.metadata.tables) == {"games", "move_analysis", "app_settings"}
    for table in Base.metadata.tables.values():
        assert table.primary_key.name
        assert all(constraint.name for constraint in table.constraints)


def test_models_and_statistics_queries_compile_for_postgresql() -> None:
    dialect = postgresql.dialect()
    str(select(Game).compile(dialect=dialect))
    str(statistics_repository._personal_metrics_subquery().select().compile(dialect=dialect))
