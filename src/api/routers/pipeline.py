"""Endpoints to consult and trigger the ETL pipeline."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request

from src.api.models import PipelineRun, PipelineRunsPage, PipelineTriggerResponse
from src.pipeline.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


def _reader(request: Request):
    return request.app.state.mongo_reader


@router.get("/runs", response_model=PipelineRunsPage)
def list_runs(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> PipelineRunsPage:
    reader = _reader(request)
    items = reader.list_pipeline_runs(limit=limit, offset=offset)
    total = reader.db.pipeline_runs.count_documents({})
    return PipelineRunsPage(
        total=total,
        limit=limit,
        offset=offset,
        items=[PipelineRun.model_validate(doc) for doc in items],
    )


@router.get("/status", response_model=PipelineRun)
def pipeline_status(request: Request) -> PipelineRun:
    reader = _reader(request)
    doc = reader.latest_pipeline_run()
    if doc is None:
        raise HTTPException(status_code=404, detail="No pipeline runs recorded yet")
    return PipelineRun.model_validate(doc)


@router.post("/trigger", response_model=PipelineTriggerResponse, status_code=202)
def trigger_pipeline(
    request: Request,
    background: BackgroundTasks,
) -> PipelineTriggerResponse:
    """Kick off the ETL in the background and return the new run id.

    The pipeline takes seconds on the demo dataset; returning 202 Accepted and
    running in a background task keeps the HTTP request fast and lets clients
    poll `/pipeline/status` or `/pipeline/runs` for progress.
    """
    launcher = getattr(request.app.state, "pipeline_launcher", None)
    if launcher is None:
        raise HTTPException(
            status_code=503,
            detail="Pipeline launcher is not configured in this deployment",
        )

    patients_csv = Path(request.app.state.patients_csv_path)
    admissions_csv = Path(request.app.state.admissions_csv_path)

    # Start the run synchronously so we can return a real run_id, and execute
    # the heavy processing in the background.
    run_id = launcher.start_run(trigger_type="manual")
    background.add_task(
        launcher.execute, run_id=run_id,
        patients_csv=patients_csv, admissions_csv=admissions_csv,
    )
    logger.info("Triggered pipeline run %s via API", run_id)
    return PipelineTriggerResponse(
        run_id=str(run_id),
        status="accepted",
        message="Pipeline run started in the background",
    )
