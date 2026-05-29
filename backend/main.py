from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from core.exception_handler import register_exception_handlers
from core.logging import configure_logging
from core.middleware import RequestLoggingMiddleware
from routers.health import router as health_router
from routers.webhook import router as webhook_router
from services.followup_service import run_followup_job

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: start and stop the background scheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_followup_job,
        trigger="interval",
        hours=1,
        id="followup_job",
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Marmax API", version="0.1.0", lifespan=lifespan)

app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)
app.include_router(health_router)
app.include_router(webhook_router)


@app.get("/")
def root() -> dict:
    """Rota raiz — mantida para compatibilidade com smoke tests existentes."""
    return {"status": "ok", "service": "marmax-api"}
