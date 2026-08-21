from collections.abc import Callable
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    games,
    import_games,
    internal_sync,
    internal_tasks,
    player,
    settings as settings_api,
    stats,
    sync,
    system,
)
from app.config import Settings, get_settings
from app.database import dispose_database_engine, init_db
from app.exceptions import register_exception_handlers


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(
    *,
    settings: Settings | None = None,
    init_database: Callable[[], None] = init_db,
) -> FastAPI:
    active_settings = settings or get_settings()
    if init_database is init_db:
        init_database = lambda: init_db(
            auto_create_schema=active_settings.auto_create_schema,
            settings=active_settings,
        )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        logger.info("Starting Chess AI Teacher API")
        init_database()
        logger.info("Database schema initialized")
        yield
        dispose_database_engine()

    application = FastAPI(
        title="Chess AI Teacher API",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.allowed_frontend_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
    )
    application.include_router(import_games.router)
    application.include_router(games.router)
    application.include_router(player.router)
    application.include_router(stats.router)
    application.include_router(system.router)
    application.include_router(settings_api.router)
    application.include_router(sync.router)
    application.include_router(internal_tasks.router)
    application.include_router(internal_sync.router)
    register_exception_handlers(application)

    @application.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
