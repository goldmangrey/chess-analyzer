from sqlalchemy import create_engine, text

from app.database import Base
from scripts.adopt_existing_database import inspect_existing_database


def test_adoption_dry_run_accepts_expected_schema_without_modifying_data(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'existing.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO app_settings (id, auto_sync_enabled, auto_analyze_latest, initial_sync_completed, last_sync_status, created_at, updated_at) VALUES (1, 1, 1, 0, 'never', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"))
    assert inspect_existing_database(url)[0]
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM app_settings")) == 1
    engine.dispose()


def test_adoption_refuses_unexpected_schema_and_postgresql(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'bad.db'}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE unexpected (id INTEGER)")
    engine.dispose()
    assert not inspect_existing_database(url)[0]
    assert not inspect_existing_database("postgresql+psycopg://u:p@localhost/db")[0]
