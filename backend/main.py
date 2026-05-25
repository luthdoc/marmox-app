from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from core.exception_handler import register_exception_handlers
from core.logging import configure_logging
from core.middleware import RequestLoggingMiddleware
from routers.health import router as health_router
from routers.webhook import router as webhook_router

configure_logging()

app = FastAPI(title="Marmax API", version="0.1.0")

app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)
app.include_router(health_router)
app.include_router(webhook_router)


@app.get("/")
def root() -> dict:
    """Rota raiz — mantida para compatibilidade com smoke tests existentes."""
    return {"status": "ok", "service": "marmax-api"}
