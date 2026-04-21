"""Tests for DataTransformer: enriquecimiento y agregaciones."""
from __future__ import annotations

from datetime import date

import pytest

pyspark = pytest.importorskip("pyspark", reason="PySpark not installed")

from pyspark.sql.types import StringType, StructField, StructType

from src.pipeline.processors.data_transformer import DataTransformer
from src.pipeline.spark_session import get_spark_session


@pytest.fixture(scope="module")
def spark():
    session = get_spark_session(app_name="test-data-transformer", master="local[2]")
    yield session
    session.stop()


@pytest.fixture
def transformer() -> DataTransformer:
    return DataTransformer()


_PATIENT_SCHEMA = StructType([
    StructField("external_id", StringType(), True),
    StructField("name", StringType(), True),
    StructField("birth_date", StringType(), True),
    StructField("gender", StringType(), True),
    StructField("blood_type", StringType(), True),
])

_ADMISSION_SCHEMA = StructType([
    StructField("patient_external_id", StringType(), True),
    StructField("admission_date", StringType(), True),
    StructField("discharge_date", StringType(), True),
    StructField("department", StringType(), True),
    StructField("diagnosis_code", StringType(), True),
    StructField("diagnosis_description", StringType(), True),
    StructField("status", StringType(), True),
])


def _patients(spark, rows):
    return spark.createDataFrame(rows, _PATIENT_SCHEMA)


def _admissions(spark, rows):
    return spark.createDataFrame(rows, _ADMISSION_SCHEMA)


# ---------------------------------------------------------------------------
# enrich_patients: calcula edad desde birth_date
# ---------------------------------------------------------------------------

def test_enrich_patients_adds_age_column(transformer: DataTransformer, spark):
    df = _patients(spark, [("HOSP-000001", "Ana", "1980-05-12", "F", "A+")])
    enriched = transformer.enrich_patients(df, reference_date=date(2026, 4, 21))
    assert "age" in enriched.columns


def test_enrich_patients_age_is_correct_before_birthday(
    transformer: DataTransformer, spark
):
    # Born 1980-05-12, reference 2026-04-21 (BEFORE birthday that year) → 45
    df = _patients(spark, [("HOSP-000001", "Ana", "1980-05-12", "F", "A+")])
    enriched = transformer.enrich_patients(df, reference_date=date(2026, 4, 21))
    assert enriched.collect()[0]["age"] == 45


def test_enrich_patients_age_is_correct_after_birthday(
    transformer: DataTransformer, spark
):
    # Born 1980-05-12, reference 2026-06-01 (AFTER birthday) → 46
    df = _patients(spark, [("HOSP-000001", "Ana", "1980-05-12", "F", "A+")])
    enriched = transformer.enrich_patients(df, reference_date=date(2026, 6, 1))
    assert enriched.collect()[0]["age"] == 46


def test_enrich_patients_age_is_null_when_birth_date_is_null(
    transformer: DataTransformer, spark
):
    df = _patients(spark, [("HOSP-000001", "Ana", None, "F", "A+")])
    enriched = transformer.enrich_patients(df, reference_date=date(2026, 4, 21))
    assert enriched.collect()[0]["age"] is None


def test_enrich_patients_preserves_other_columns(
    transformer: DataTransformer, spark
):
    df = _patients(spark, [("HOSP-000001", "Ana", "1980-05-12", "F", "A+")])
    enriched = transformer.enrich_patients(df, reference_date=date(2026, 4, 21))
    row = enriched.collect()[0]
    assert row["external_id"] == "HOSP-000001"
    assert row["name"] == "Ana"
    assert row["birth_date"] == "1980-05-12"
    assert row["gender"] == "F"
    assert row["blood_type"] == "A+"


def test_enrich_patients_uses_current_date_by_default(
    transformer: DataTransformer, spark
):
    """Without explicit reference_date, age uses current_date and should be non-negative."""
    df = _patients(spark, [("HOSP-000001", "Ana", "1980-05-12", "F", "A+")])
    enriched = transformer.enrich_patients(df)
    age = enriched.collect()[0]["age"]
    assert age is not None and age >= 0


# ---------------------------------------------------------------------------
# enrich_admissions: categoriza diagnosis_code
# ---------------------------------------------------------------------------

def test_enrich_admissions_adds_diagnosis_category_column(
    transformer: DataTransformer, spark
):
    df = _admissions(spark, [
        ("HOSP-000001", "2025-03-10", None, "UCI", "J18.9", "Pneumonia", "admitted"),
    ])
    enriched = transformer.enrich_admissions(df)
    assert "diagnosis_category" in enriched.columns


def test_enrich_admissions_classifies_covid_codes(
    transformer: DataTransformer, spark
):
    df = _admissions(spark, [
        ("HOSP-000001", "2025-03-10", None, "UCI", "U07.1", "COVID-19", "admitted"),
        ("HOSP-000002", "2025-03-10", None, "UCI", "U07.2", "COVID-19 suspected", "admitted"),
    ])
    enriched = transformer.enrich_admissions(df)
    categories = [r["diagnosis_category"] for r in enriched.collect()]
    assert categories == ["COVID-19", "COVID-19"]


def test_enrich_admissions_classifies_pneumonia_codes(
    transformer: DataTransformer, spark
):
    df = _admissions(spark, [
        ("HOSP-000001", "2025-03-10", None, "UCI", "J18.9", "Pneumonia, unspecified", "admitted"),
        ("HOSP-000002", "2025-03-10", None, "UCI", "J18.0", "Bronchopneumonia", "admitted"),
        ("HOSP-000003", "2025-03-10", None, "UCI", "J12.1", "Viral pneumonia", "admitted"),
    ])
    enriched = transformer.enrich_admissions(df)
    categories = [r["diagnosis_category"] for r in enriched.collect()]
    assert categories == ["Pneumonia", "Pneumonia", "Pneumonia"]


def test_enrich_admissions_classifies_other_codes(
    transformer: DataTransformer, spark
):
    df = _admissions(spark, [
        ("HOSP-000001", "2025-03-10", None, "UCI", "I21.9", "MI", "admitted"),
        ("HOSP-000002", "2025-03-10", None, "UCI", "S72.9", "Fracture", "admitted"),
        ("HOSP-000003", "2025-03-10", None, "UCI", "K35.80", "Appendicitis", "admitted"),
    ])
    enriched = transformer.enrich_admissions(df)
    categories = {r["diagnosis_category"] for r in enriched.collect()}
    assert categories == {"Other"}


def test_enrich_admissions_handles_null_diagnosis_code(
    transformer: DataTransformer, spark
):
    df = _admissions(spark, [
        ("HOSP-000001", "2025-03-10", None, "UCI", None, None, "admitted"),
    ])
    enriched = transformer.enrich_admissions(df)
    assert enriched.collect()[0]["diagnosis_category"] == "Unknown"


def test_enrich_admissions_preserves_other_columns(
    transformer: DataTransformer, spark
):
    df = _admissions(spark, [
        ("HOSP-000001", "2025-03-10", "2025-03-15", "UCI", "U07.1", "COVID-19", "discharged"),
    ])
    enriched = transformer.enrich_admissions(df)
    row = enriched.collect()[0]
    assert row["patient_external_id"] == "HOSP-000001"
    assert row["department"] == "UCI"
    assert row["status"] == "discharged"


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------

def test_admissions_by_department_counts_correctly(
    transformer: DataTransformer, spark
):
    df = _admissions(spark, [
        ("HOSP-000001", "2025-03-10", None, "UCI", "U07.1", "COVID", "admitted"),
        ("HOSP-000002", "2025-03-11", None, "UCI", "J18.9", "Pneumonia", "admitted"),
        ("HOSP-000003", "2025-03-12", None, "Urgencias", "R50.9", "Fever", "admitted"),
    ])
    agg = transformer.admissions_by_department(df)
    result = {r["department"]: r["count"] for r in agg.collect()}
    assert result == {"UCI": 2, "Urgencias": 1}


def test_admissions_by_month_counts_correctly(transformer: DataTransformer, spark):
    df = _admissions(spark, [
        ("HOSP-000001", "2025-03-10", None, "UCI", "U07.1", "COVID", "admitted"),
        ("HOSP-000002", "2025-03-15", None, "UCI", "J18.9", "Pneumonia", "admitted"),
        ("HOSP-000003", "2025-04-05", None, "UCI", "R50.9", "Fever", "admitted"),
    ])
    agg = transformer.admissions_by_month(df)
    result = {r["month"]: r["count"] for r in agg.collect()}
    assert result == {"2025-03": 2, "2025-04": 1}


def test_admissions_by_diagnosis_category_counts_correctly(
    transformer: DataTransformer, spark
):
    df = _admissions(spark, [
        ("HOSP-000001", "2025-03-10", None, "UCI", "U07.1", "COVID", "admitted"),
        ("HOSP-000002", "2025-03-11", None, "UCI", "J18.9", "Pneumonia", "admitted"),
        ("HOSP-000003", "2025-03-12", None, "UCI", "J18.0", "Pneumonia", "admitted"),
        ("HOSP-000004", "2025-03-13", None, "UCI", "S72.9", "Fracture", "admitted"),
    ])
    agg = transformer.admissions_by_diagnosis_category(df)
    result = {r["diagnosis_category"]: r["count"] for r in agg.collect()}
    assert result == {"COVID-19": 1, "Pneumonia": 2, "Other": 1}
