"""FastAPI application for the hospital system.

`build_app` is the testable factory: it accepts the MongoDB name to use and
optionally a pipeline launcher. The module-level `app` is what uvicorn imports
in production (reads config from environment variables).
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from src.api.models import HealthResponse
from src.api.mongo_reader import MongoReader
from src.api.pipeline_launcher import PipelineLauncher
from src.api.routers import data as data_router
from src.api.routers import pipeline as pipeline_router

API_VERSION = "0.1.0"

# Sentinel that distinguishes "use the production default launcher" from
# "explicitly disable the launcher" (used by tests that don't want to spin
# up Spark in BackgroundTasks).
_USE_DEFAULT_LAUNCHER = object()


def build_app(
    mongo_db_name: str | None = None,
    pipeline_launcher=_USE_DEFAULT_LAUNCHER,
    patients_csv_path: Path | None = None,
    admissions_csv_path: Path | None = None,
) -> FastAPI:
    if pipeline_launcher is _USE_DEFAULT_LAUNCHER:
        pipeline_launcher = PipelineLauncher()

    reader = MongoReader(
        host=os.environ.get("MONGO_HOST", "localhost"),
        port=int(os.environ.get("MONGO_PORT", "27017")),
        db_name=mongo_db_name or os.environ.get("MONGO_DB", "hospital"),
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            reader.close()

    app = FastAPI(
        title="laSalle Hospital API",
        version=API_VERSION,
        description="REST API to consult hospital data and trigger the ETL pipeline.",
        lifespan=lifespan,
    )

    app.state.mongo_reader = reader
    app.state.pipeline_launcher = pipeline_launcher
    app.state.patients_csv_path = patients_csv_path or Path("/app/data/raw/patients.csv")
    app.state.admissions_csv_path = admissions_csv_path or Path("/app/data/raw/admissions.csv")

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=API_VERSION)

    app.include_router(data_router.router)
    app.include_router(pipeline_router.router)

    return app


# ASGI entrypoint for uvicorn: `uvicorn src.api.main:app`
app = build_app()
