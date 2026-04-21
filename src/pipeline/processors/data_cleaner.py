"""Clean hospital records: trim whitespace, remove duplicates.

The cleaner operates on rows that have already passed validation (T7). It is
intentionally conservative: it never modifies business fields, only normalizes
obvious artefacts (trailing whitespace) and collapses duplicates by business
key.

Dedup note: when multiple rows share the same key tuple, which one survives
is not guaranteed. The guarantee is uniqueness of the key, not preservation
of insertion order.
"""
from __future__ import annotations

from pyspark.sql import DataFrame, functions as F

from src.pipeline.logging_config import get_logger

logger = get_logger(__name__)


class DataCleaner:
    def clean_patients(self, df: DataFrame) -> DataFrame:
        cleaned = (
            df.withColumn("name", F.trim(F.col("name")))
              .dropDuplicates(subset=["external_id"])
        )
        logger.info("Cleaned patients: %d rows after dedup", cleaned.count())
        return cleaned

    def clean_admissions(self, df: DataFrame) -> DataFrame:
        # A patient can have multiple admissions; dedup only when the same
        # patient has the same date and department — those are almost certainly
        # duplicates rather than two distinct admissions.
        cleaned = (
            df.withColumn("department", F.trim(F.col("department")))
              .dropDuplicates(
                  subset=["patient_external_id", "admission_date", "department"]
              )
        )
        logger.info("Cleaned admissions: %d rows after dedup", cleaned.count())
        return cleaned
