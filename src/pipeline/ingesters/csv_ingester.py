"""Read hospital CSV files into PySpark DataFrames.

This layer only handles ingestion (reading + schema validation). It does NOT
filter or reject rows — that belongs to the validation stage (T7). Edge-case
rows (nulls, malformed values) are preserved verbatim so downstream validators
can produce meaningful rejection reasons.
"""
from __future__ import annotations

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

from src.pipeline.logging_config import get_logger

logger = get_logger(__name__)

PATIENT_SCHEMA_COLUMNS: tuple[str, ...] = (
    "external_id",
    "name",
    "birth_date",
    "gender",
    "blood_type",
)

ADMISSION_SCHEMA_COLUMNS: tuple[str, ...] = (
    "patient_external_id",
    "admission_date",
    "discharge_date",
    "department",
    "diagnosis_code",
    "diagnosis_description",
    "status",
)

SOURCE_FILE_COLUMN = "_source_file"


class MissingColumnsError(ValueError):
    """Raised when a CSV is missing one or more required columns."""


class CSVIngester:
    def __init__(self, spark: SparkSession) -> None:
        self._spark = spark

    def read_patients(self, csv_path: Path) -> DataFrame:
        return self._read(csv_path, PATIENT_SCHEMA_COLUMNS, entity="patients")

    def read_admissions(self, csv_path: Path) -> DataFrame:
        return self._read(csv_path, ADMISSION_SCHEMA_COLUMNS, entity="admissions")

    def _read(
        self,
        csv_path: Path,
        required_columns: tuple[str, ...],
        entity: str,
    ) -> DataFrame:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file does not exist: {path}")

        # Read everything as string. Type casting and validation happen later.
        schema = StructType(
            [StructField(col, StringType(), nullable=True) for col in required_columns]
        )

        # Use header to auto-detect column order; missing cols will surface below.
        df = (
            self._spark.read
            .option("header", "true")
            .option("mode", "PERMISSIVE")
            .csv(str(path))
        )

        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            raise MissingColumnsError(
                f"CSV {path.name} is missing required columns: {missing}"
            )

        df = df.select(*required_columns)

        # Enforce the nominal schema so downstream code sees consistent types.
        for field in schema.fields:
            df = df.withColumn(field.name, F.col(field.name).cast(field.dataType))

        df = df.withColumn(SOURCE_FILE_COLUMN, F.lit(path.name))

        logger.info(
            "Ingested %s from %s (%d rows)",
            entity,
            path.name,
            df.count() if logger.isEnabledFor(20) else -1,
        )
        return df
