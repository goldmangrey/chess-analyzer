import pytest

from app.config import Settings


def test_multiple_origins_trimmed_and_local_default():
    assert Settings(_env_file=None).allowed_frontend_origins == ("http://localhost:3000",)
    configured = Settings(_env_file=None, FRONTEND_ORIGINS=" https://one.example/, http://localhost:3000 ")
    assert configured.allowed_frontend_origins == ("https://one.example", "http://localhost:3000")


def test_wildcard_rejected():
    with pytest.raises(ValueError):
        _ = Settings(_env_file=None, FRONTEND_ORIGINS="*").allowed_frontend_origins
