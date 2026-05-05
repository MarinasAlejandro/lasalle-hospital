"""Glue between the FastAPI router and the actual ETL orchestrator.

The HTTP handler `POST /api/v1/pipeline/trigger` should respond fast (with
the new run id) but the heavy PySpark work has to happen somewhere. This
launcher splits that into two parts:

  * `start_run(trigger_type)` — synchronous: creates the `pipeline_runs`
    document so the API can return the run id immediately
  * `execute(run_id, patients_csv, admissions_csv)` — long-running: runs
    the orchestrator under a fresh SparkSession + MongoWriter, reusing the
    run id so the run history is consistent

`execute` is intended to be scheduled with FastAPI's `BackgroundTasks`. It
catches no exceptions: if the underlying orchestrator marks the run as
failed and re-raises, we let the background task report it (FastAPI will
log the error). The run document in MongoDB always reflects the outcome.
"""
from __future__ import annotations

from pathlib import Path

from bson import ObjectId

from src.pipeline.logging_config import get_logger
from src.pipeline.orchestrator import PipelineOrchestrator
from src.pipeline.spark_session import get_spark_session
from src.pipeline.storage.mongo_writer import get_mongo_writer_from_env

logger = get_logger(__name__)


class PipelineLauncher:
    def start_run(self, trigger_type: str = "manual") -> ObjectId:
        writer = get_mongo_writer_from_env()
        try:
            return writer.start_pipeline_run(trigger_type=trigger_type)
        finally:
            writer.close()

    def execute(
        self,
        run_id: ObjectId,
        patients_csv: Path,
        admissions_csv: Path,
    ) -> None:
        spark = get_spark_session(
            app_name="hospital-api-trigger", master="local[*]"
        )
        writer = get_mongo_writer_from_env()
        try:
            orchestrator = PipelineOrchestrator(spark=spark, mongo_writer=writer)
            orchestrator.run_from_files(
                patients_csv=patients_csv,
                admissions_csv=admissions_csv,
                run_id=run_id,
            )
        except Exception:
            logger.exception("Background pipeline run %s failed", run_id)
            # No re-raising: the run is already marked as failed in MongoDB
            # by the orchestrator. Re-raising in a BackgroundTask would only
            # generate a noisy traceback in uvicorn without changing state.
        finally:
            writer.close()
            # We intentionally don't stop Spark — getOrCreate reuses the
            # session for subsequent triggers within the same API process.
