import os

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.database import Base, create_database_engine
from app.repositories.app_settings_repository import get_or_create_settings


@pytest.mark.postgres_integration
def test_optional_postgresql_repository_flow() -> None:
    url = os.getenv("TEST_POSTGRES_DATABASE_URL")
    if not url:
        pytest.skip("TEST_POSTGRES_DATABASE_URL is not configured")
    database_name = make_url(url).database or ""
    if "test" not in database_name.lower():
        pytest.fail("Refusing PostgreSQL integration test outside a test database")
    engine = create_database_engine(url)
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            assert get_or_create_settings(session).id == 1
            session.rollback()
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
