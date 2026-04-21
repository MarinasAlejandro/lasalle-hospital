"""Enrich hospital records and compute aggregated metrics.

The transformer works on rows that have already passed validation and cleaning
(T7). Enrichment adds derived fields; aggregations produce summary DataFrames
intended for the API/dashboard layer.

Design notes:
  - `age` is a snapshot at processing time. The raw `birth_date` is kept so
    downstream consumers can recompute if needed.
  - `diagnosis_category` maps ICD-10 codes to the three clinical categories
    aligned with the project's classification goal: COVID-19, Pneumonia,
    Other (anything else). Null codes become "Unknown" so counts remain
    meaningful even before validation catches them upstream.
"""
from __future__ import annotations

from datetime import date

from pyspark.sql import DataFrame, functions as F

from src.pipeline.logging_config import get_logger

logger = get_logger(__name__)

# ICD-10 prefixes grouped by the clinical category we care about.
COVID_ICD10_PREFIXES = ("U07",)
# J12-J18 cover viral and bacterial pneumonias (unspecified, lobar, broncho,
# viral, bacterial, aspiration, and unspecified pneumonia).
PNEUMONIA_ICD10_PREFIXES = ("J12", "J13", "J14", "J15", "J16", "J17", "J18")


class DataTransformer:
    def enrich_patients(
        self, df: DataFrame, reference_date: date | None = None
    ) -> DataFrame:
        """Add an `age` column computed from `birth_date`.

        Passing `reference_date` keeps tests deterministic. Production callers
        typically omit it to use `current_date()`.
        """
        if reference_date is None:
            ref = F.current_date()
        else:
            ref = F.to_date(F.lit(reference_date.isoformat()))

        birth = F.to_date(F.col("birth_date"))
        age = F.when(
            birth.isNull(), F.lit(None)
        ).otherwise(
            F.floor(F.months_between(ref, birth) / F.lit(12)).cast("integer")
        )
        enriched = df.withColumn("age", age)
        logger.info("Enriched %d patients with age", enriched.count())
        return enriched

    def enrich_admissions(self, df: DataFrame) -> DataFrame:
        """Add a `diagnosis_category` column derived from `diagnosis_code`."""
        code = F.col("diagnosis_code")
        covid_pred = self._prefix_match(code, COVID_ICD10_PREFIXES)
        pneumonia_pred = self._prefix_match(code, PNEUMONIA_ICD10_PREFIXES)

        category = (
            F.when(code.isNull(), F.lit("Unknown"))
            .when(covid_pred, F.lit("COVID-19"))
            .when(pneumonia_pred, F.lit("Pneumonia"))
            .otherwise(F.lit("Other"))
        )
        enriched = df.withColumn("diagnosis_category", category)
        logger.info("Enriched %d admissions with diagnosis_category", enriched.count())
        return enriched

    def admissions_by_department(self, df: DataFrame) -> DataFrame:
        return df.groupBy("department").count().orderBy(F.desc("count"))

    def admissions_by_month(self, df: DataFrame) -> DataFrame:
        return (
            df.withColumn(
                "month", F.date_format(F.to_date(F.col("admission_date")), "yyyy-MM")
            )
            .groupBy("month")
            .count()
            .orderBy("month")
        )

    def admissions_by_diagnosis_category(self, df: DataFrame) -> DataFrame:
        enriched = (
            df if "diagnosis_category" in df.columns else self.enrich_admissions(df)
        )
        return enriched.groupBy("diagnosis_category").count().orderBy(F.desc("count"))

    @staticmethod
    def _prefix_match(column, prefixes: tuple[str, ...]):
        """Build a boolean expression: `column` starts with any of the prefixes."""
        expr = F.lit(False)
        for prefix in prefixes:
            expr = expr | column.startswith(prefix)
        return expr
