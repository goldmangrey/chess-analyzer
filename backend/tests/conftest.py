from collections.abc import Generator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import create_database_engine, init_db


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
