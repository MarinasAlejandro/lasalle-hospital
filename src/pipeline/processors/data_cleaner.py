"""Clean hospital records: trim whitespace, remove duplicates.

The cleaner operates on rows that have already passed validation (T7). It is
intentionally conservative: it never modifies business fields, only normalizes
obvious artefacts (trailing whitespace) and collapses duplicates.
"""
from __future__ import annotations

from pyspark.sql import DataFrame, Window, functions as F

from src.pipeline.logging_config import get_logger

logger = get_logger(__name__)

_DEDUP_ROW_COLUMN = "_dedup_row"


class DataCleaner:
    def clean_patients(self, df: DataFrame) -> DataFrame:
        original_columns = df.columns
        df = df.withColumn("name", F.trim(F.col("name")))
        df = _dedup_first_by(df, ["external_id"], original_columns)
        logger.info("Cleaned patients: %d rows after dedup", df.count())
        return df

    def clean_admissions(self, df: DataFrame) -> DataFrame:
        original_columns = df.columns
        df = df.withColumn("department", F.trim(F.col("department")))
        # A patient can have multiple admissions; dedup only on (patient, date, dept).
        dedup_keys = ["patient_external_id", "admission_date", "department"]
        df = _dedup_first_by(df, dedup_keys, original_columns)
        logger.info("Cleaned admissions: %d rows after dedup", df.count())
        return df


def _dedup_first_by(
    df: DataFrame, keys: list[str], original_columns: list[str]
) -> DataFrame:
    """Keep the first occurrence per key tuple, preserving insertion order."""
    window = Window.partitionBy(*keys).orderBy(F.monotonically_increasing_id())
    return (
        df.withColumn(_DEDUP_ROW_COLUMN, F.row_number().over(window))
        .filter(F.col(_DEDUP_ROW_COLUMN) == 1)
        .select(*original_columns)
    )
