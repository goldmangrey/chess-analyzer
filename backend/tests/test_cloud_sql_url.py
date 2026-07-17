from sqlalchemy.engine import make_url

from app.config import Settings, compose_cloud_sql_database_url


def test_cloud_sql_socket_url_and_password_encoding():
    url = compose_cloud_sql_database_url(
        host="/cloudsql/project:europe-west1:instance", port=5432,
        name="chess_ai_teacher", user="chess_app", password="p@ss/word: value",
    )
    parsed = make_url(url)
    assert parsed.drivername == "postgresql+psycopg"
    assert parsed.password == "p@ss/word: value"
    assert parsed.query["host"] == "/cloudsql/project:europe-west1:instance"
    assert parsed.host is None


def test_database_url_override_has_priority():
    settings = Settings(
        _env_file=None, DATABASE_URL="postgresql+psycopg://explicit/db",
        DATABASE_HOST="/cloudsql/ignored", DATABASE_NAME="other",
        DATABASE_USER="user", DATABASE_PASSWORD="password",
    )
    assert settings.database_url == "postgresql+psycopg://explicit/db"
