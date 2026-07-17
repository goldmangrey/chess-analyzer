from collections.abc import Callable
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import games, import_games, stats
from app.config import Settings, get_settings
from app.database import init_db
from app.exceptions import register_exception_handlers


logging.basicConfig(level=logging.INFO)


def create_app(
    *,
    settings: Settings | None = None,
    init_database: Callable[[], None] = init_db,
) -> FastAPI:
    active_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        init_database()
        yield

    application = FastAPI(
        title="Chess AI Teacher API",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[active_settings.frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
    )
    application.include_router(import_games.router)
    application.include_router(games.router)
    application.include_router(stats.router)
    register_exception_handlers(application)

    @application.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
