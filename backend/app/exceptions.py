import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.analysis_service import GameNotFoundError
from app.services.chesscom_client import (
    ChessComNetworkError,
    ChessComResponseError,
    ChessComUserNotFoundError,
)


logger = logging.getLogger(__name__)


def _response(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": error, "message": message},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(GameNotFoundError)
    async def game_not_found_handler(
        _request: Request,
        exception: GameNotFoundError,
    ) -> JSONResponse:
        return _response(404, "game_not_found", str(exception))

    @app.exception_handler(ChessComUserNotFoundError)
    async def chesscom_user_not_found_handler(
        _request: Request,
        exception: ChessComUserNotFoundError,
    ) -> JSONResponse:
        return _response(404, "chesscom_user_not_found", str(exception))

    @app.exception_handler(ChessComNetworkError)
    async def chesscom_network_handler(
        _request: Request,
        exception: ChessComNetworkError,
    ) -> JSONResponse:
        logger.warning("Chess.com network failure: %s", exception)
        return _response(503, "chesscom_unavailable", str(exception))

    @app.exception_handler(ChessComResponseError)
    async def chesscom_response_handler(
        _request: Request,
        exception: ChessComResponseError,
    ) -> JSONResponse:
        logger.warning("Invalid Chess.com response: %s", exception)
        return _response(502, "chesscom_bad_gateway", str(exception))

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        _request: Request,
        exception: Exception,
    ) -> JSONResponse:
        logger.exception("Unexpected API error", exc_info=exception)
        return _response(500, "internal_server_error", "Unexpected server error")
