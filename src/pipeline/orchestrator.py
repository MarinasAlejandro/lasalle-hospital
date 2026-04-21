"""Coordinate the end-to-end ETL run over a pair of input CSVs.

The orchestrator wires the ingesters, processors and storage layer into a
single atomic pipeline run. Each call:

  1. Opens a `pipeline_run` document in MongoDB (status=running)
  2. Ingests patients and admissions CSVs into PySpark DataFrames
  3. Validates rows, splitting valid from rejected
  4. Cleans and transforms the valid rows (age, diagnosis_category)
  5. Writes enriched patients with embedded admissions to MongoDB
  6. Persists rejected rows with their reason for auditability
  7. Closes the run with status=success/failed and aggregated stats

Failures at any stage mark the run as failed (CB-5) before re-raising, so
the run history always reflects what happened.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bson import ObjectId
from pyspark.sql import DataFrame, SparkSession

from src.pipeline.ingesters.csv_ingester import CSVIngester
from src.pipeline.logging_config import get_logger
from src.pipeline.processors.data_cleaner import DataCleaner
from src.pipeline.processors.data_transformer import DataTransformer
from src.pipeline.processors.data_validator import DataValidator
from src.pipeline.storage.mongo_writer import MongoWriter

logger = get_logger(__name__)


@dataclass(frozen=True)
class PipelineRunResult:
    run_id: ObjectId
    status: str
    records_processed: int
    records_rejected: int


class PipelineOrchestrator:
    def __init__(
        self,
        spark: SparkSession,
        mongo_writer: MongoWriter,
        ingester: CSVIngester | None = None,
        validator: DataValidator | None = None,
        cleaner: DataCleaner | None = None,
        transformer: DataTransformer | None = None,
    ) -> None:
        self._spark = spark
        self._writer = mongo_writer
        self._ingester = ingester or CSVIngester(spark)
        self._validator = validator or DataValidator()
        self._cleaner = cleaner or DataCleaner()
        self._transformer = transformer or DataTransformer()

    def run_from_files(
        self,
        patients_csv: Path,
        admissions_csv: Path,
        trigger_type: str = "manual",
    ) -> PipelineRunResult:
        run_id = self._writer.start_pipeline_run(trigger_type=trigger_type)
        try:
            patients_clean, patients_rejected = self._process_patients(patients_csv)
            admissions_clean, admissions_rejected = self._process_admissions(
                admissions_csv
            )

            patients_records = [row.asDict() for row in patients_clean.collect()]
            admissions_records = [row.asDict() for row in admissions_clean.collect()]

            self._writer.bulk_upsert_patients_with_admissions(
                patients=patients_records,
                admissions=admissions_records,
            )

            rejected = self._collect_rejected(
                patients_rejected, source="patients.csv"
            ) + self._collect_rejected(admissions_rejected, source="admissions.csv")
            self._writer.write_rejected(rejected, run_id)

            stats = {
                "records_processed": len(patients_records) + len(admissions_records),
                "records_rejected": len(rejected),
                "images_processed": 0,  # imagenes las maneja el bootstrap
            }
            self._writer.finish_pipeline_run(run_id, status="success", stats=stats)

            logger.info(
                "Pipeline run %s finished: %d processed, %d rejected",
                run_id,
                stats["records_processed"],
                stats["records_rejected"],
            )
            return PipelineRunResult(
                run_id=run_id,
                status="success",
                records_processed=stats["records_processed"],
                records_rejected=stats["records_rejected"],
            )

        except Exception as exc:
            logger.exception("Pipeline run %s failed", run_id)
            self._writer.finish_pipeline_run(
                run_id,
                status="failed",
                error_message=f"{type(exc).__name__}: {exc}",
            )
            raise

    def _process_patients(
        self, csv_path: Path
    ) -> tuple[DataFrame, DataFrame]:
        raw = self._ingester.read_patients(csv_path)
        validation = self._validator.validate_patients(raw)
        cleaned = self._cleaner.clean_patients(validation.valid)
        enriched = self._transformer.enrich_patients(cleaned)
        return enriched, validation.rejected

    def _process_admissions(
        self, csv_path: Path
    ) -> tuple[DataFrame, DataFrame]:
        raw = self._ingester.read_admissions(csv_path)
        validation = self._validator.validate_admissions(raw)
        cleaned = self._cleaner.clean_admissions(validation.valid)
        enriched = self._transformer.enrich_admissions(cleaned)
        return enriched, validation.rejected

    @staticmethod
    def _collect_rejected(rejected_df: DataFrame, source: str) -> list[dict]:
        out: list[dict] = []
        for row in rejected_df.collect():
            raw_data = {k: v for k, v in row.asDict().items() if k != "rejection_reason"}
            out.append(
                {
                    "source_file": source,
                    "rejection_reason": row["rejection_reason"],
                    "raw_data": raw_data,
                }
            )
        return out
