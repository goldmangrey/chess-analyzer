from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.database import create_database_engine, init_db
from app.dependencies import get_database_session, get_settings_dependency
from app.main import create_app


@pytest.fixture
def test_engine(tmp_path) -> Generator[Engine, None, None]:
    database_path = tmp_path / "test.db"
    database_engine = create_database_engine(
        f"sqlite+pysqlite:///{database_path}"
    )
    init_db(bind=database_engine)
    try:
        yield database_engine
    finally:
        database_engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    testing_session = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_app(test_engine: Engine):
    settings = Settings(_env_file=None, FRONTEND_ORIGIN="http://localhost:3000")
    testing_session = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )
    application = create_app(
        settings=settings,
        init_database=lambda: init_db(bind=test_engine),
    )

    def override_database_session():
        session = testing_session()
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_database_session] = override_database_session
    application.dependency_overrides[get_settings_dependency] = lambda: settings
    application.state.testing_session_factory = testing_session
    return application


@pytest.fixture
def api_client(api_app) -> Generator[TestClient, None, None]:
    with TestClient(api_app) as client:
        yield client
