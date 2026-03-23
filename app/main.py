from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_generation import router as generation_router
from app.api.routes_health import router as health_router
from app.api.routes_interview import router as interview_router
from app.api.routes_matching import router as matching_router
from app.api.routes_parser import router as parser_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.observability.metrics import metrics_middleware
from app.observability.metrics import router as metrics_router
from app.storage.db import init_db


def create_app() -> FastAPI:
    configure_logging(settings.log_level)
    init_db(settings.sqlite_path)

    app = FastAPI(title=settings.app_name)
    app.middleware("http")(metrics_middleware)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(interview_router)
    app.include_router(generation_router)
    app.include_router(matching_router)
    app.include_router(parser_router)
    return app


app = create_app()
