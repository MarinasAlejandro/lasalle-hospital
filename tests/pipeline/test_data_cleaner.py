"""Tests for DataCleaner: dedup, normalizacion de nulos opcionales y formatos."""
from __future__ import annotations

import pytest

pyspark = pytest.importorskip("pyspark", reason="PySpark not installed")

from pyspark.sql.types import StringType, StructField, StructType

from src.pipeline.processors.data_cleaner import DataCleaner
from src.pipeline.spark_session import get_spark_session


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


@pytest.fixture(scope="module")
def spark():
    session = get_spark_session(app_name="test-data-cleaner", master="local[2]")
    yield session
    session.stop()


@pytest.fixture
def cleaner() -> DataCleaner:
    return DataCleaner()


def _patients(spark, rows):
    return spark.createDataFrame(rows, _PATIENT_SCHEMA)


def _admissions(spark, rows):
    return spark.createDataFrame(rows, _ADMISSION_SCHEMA)


def test_clean_patients_removes_exact_duplicates(cleaner: DataCleaner, spark):
    df = _patients(spark, [
        ("HOSP-000001", "Ana", "1980-05-12", "F", "A+"),
        ("HOSP-000001", "Ana", "1980-05-12", "F", "A+"),  # duplicate
        ("HOSP-000002", "Luis", "1975-03-22", "M", "O-"),
    ])

    cleaned = cleaner.clean_patients(df)
    assert cleaned.count() == 2
    ids = [r["external_id"] for r in cleaned.collect()]
    assert sorted(ids) == ["HOSP-000001", "HOSP-000002"]


def test_clean_patients_trims_whitespace_on_name(cleaner: DataCleaner, spark):
    df = _patients(spark, [
        ("HOSP-000001", "  Ana Garcia  ", "1980-05-12", "F", "A+"),
    ])
    cleaned = cleaner.clean_patients(df)
    assert cleaned.collect()[0]["name"] == "Ana Garcia"


def test_clean_patients_keeps_first_occurrence_when_same_external_id(
    cleaner: DataCleaner, spark
):
    df = _patients(spark, [
        ("HOSP-000001", "Ana Original", "1980-05-12", "F", "A+"),
        ("HOSP-000001", "Ana Conflict", "1981-06-13", "F", "B+"),
    ])
    cleaned = cleaner.clean_patients(df)
    assert cleaned.count() == 1
    assert cleaned.collect()[0]["name"] == "Ana Original"


def test_clean_admissions_removes_exact_duplicates(cleaner: DataCleaner, spark):
    df = _admissions(spark, [
        ("HOSP-000001", "2025-03-10", "2025-03-15", "UCI", "J18.9", "Pneumonia", "discharged"),
        ("HOSP-000001", "2025-03-10", "2025-03-15", "UCI", "J18.9", "Pneumonia", "discharged"),
        ("HOSP-000002", "2025-04-01", None, "Urgencias", "R50.9", "Fever", "admitted"),
    ])
    cleaned = cleaner.clean_admissions(df)
    assert cleaned.count() == 2


def test_clean_admissions_trims_whitespace_on_department(cleaner: DataCleaner, spark):
    df = _admissions(spark, [
        ("HOSP-000001", "2025-03-10", None, "  UCI  ", "J18.9", "Pneumonia", "admitted"),
    ])
    cleaned = cleaner.clean_admissions(df)
    assert cleaned.collect()[0]["department"] == "UCI"


def test_clean_patients_preserves_source_file_column(cleaner: DataCleaner, spark):
    cols = ["external_id", "name", "birth_date", "gender", "blood_type", "_source_file"]
    df = spark.createDataFrame(
        [
            ("HOSP-000001", "Ana", "1980-05-12", "F", "A+", "patients.csv"),
            ("HOSP-000001", "Ana", "1980-05-12", "F", "A+", "patients.csv"),
        ],
        cols,
    )
    cleaned = cleaner.clean_patients(df)
    assert cleaned.count() == 1
    assert "_source_file" in cleaned.columns


def test_clean_patients_handles_empty_dataframe(cleaner: DataCleaner, spark):
    df = _patients(spark, [])
    cleaned = cleaner.clean_patients(df)
    assert cleaned.count() == 0
