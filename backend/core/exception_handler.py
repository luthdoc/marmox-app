import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra handler global para exceções não tratadas."""

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled exception: %s", exc, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error"},
        )
