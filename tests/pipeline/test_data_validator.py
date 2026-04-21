"""Tests for DataValidator: separa filas validas vs rechazadas con motivo."""
from __future__ import annotations

import pytest

pyspark = pytest.importorskip("pyspark", reason="PySpark not installed")

from pyspark.sql.types import StringType, StructField, StructType

from src.pipeline.processors.data_validator import DataValidator
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
    session = get_spark_session(app_name="test-data-validator", master="local[2]")
    yield session
    session.stop()


@pytest.fixture
def validator() -> DataValidator:
    return DataValidator()


def _patient_rows(spark, rows):
    return spark.createDataFrame(rows, _PATIENT_SCHEMA)


def _admission_rows(spark, rows):
    return spark.createDataFrame(rows, _ADMISSION_SCHEMA)


# ---------------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------------

def test_valid_patients_pass_unchanged(validator: DataValidator, spark):
    df = _patient_rows(spark, [
        ("HOSP-000001", "Ana Garcia", "1980-05-12", "F", "A+"),
        ("HOSP-000002", "Luis Perez", "1975-03-22", "M", "O-"),
    ])

    result = validator.validate_patients(df)
    assert result.valid.count() == 2
    assert result.rejected.count() == 0


def test_patient_without_external_id_is_rejected(validator: DataValidator, spark):
    df = _patient_rows(spark, [
        (None, "Ana", "1980-05-12", "F", "A+"),
        ("BAD-FORMAT", "Luis", "1975-03-22", "M", "O-"),
    ])

    result = validator.validate_patients(df)
    assert result.valid.count() == 0
    reasons = {r["rejection_reason"] for r in result.rejected.collect()}
    assert reasons == {"invalid external_id"}


def test_patient_with_empty_name_is_rejected(validator: DataValidator, spark):
    df = _patient_rows(spark, [
        ("HOSP-000001", "", "1980-05-12", "F", "A+"),
        ("HOSP-000002", "   ", "1975-03-22", "M", "O-"),
    ])

    result = validator.validate_patients(df)
    assert result.valid.count() == 0
    assert result.rejected.count() == 2
    reasons = {r["rejection_reason"] for r in result.rejected.collect()}
    assert reasons == {"missing name"}


def test_patient_with_non_iso_birth_date_is_rejected(validator: DataValidator, spark):
    df = _patient_rows(spark, [
        ("HOSP-000001", "Ana", "12/05/1980", "F", "A+"),
        ("HOSP-000002", "Luis", "", "M", "O-"),
    ])

    result = validator.validate_patients(df)
    assert result.valid.count() == 0
    reasons = {r["rejection_reason"] for r in result.rejected.collect()}
    assert reasons == {"invalid birth_date"}


def test_patient_with_unknown_gender_is_rejected(validator: DataValidator, spark):
    df = _patient_rows(spark, [
        ("HOSP-000001", "Ana", "1980-05-12", "X", "A+"),
    ])

    result = validator.validate_patients(df)
    assert result.valid.count() == 0
    assert result.rejected.collect()[0]["rejection_reason"] == "invalid gender"


def test_patient_with_null_gender_is_rejected(validator: DataValidator, spark):
    """Null values must not escape isin-based rules (PySpark gotcha)."""
    df = _patient_rows(spark, [
        ("HOSP-000001", "Ana", "1980-05-12", None, "A+"),
    ])

    result = validator.validate_patients(df)
    assert result.valid.count() == 0
    assert result.rejected.collect()[0]["rejection_reason"] == "invalid gender"


def test_patient_with_null_blood_type_is_rejected(validator: DataValidator, spark):
    df = _patient_rows(spark, [
        ("HOSP-000001", "Ana", "1980-05-12", "F", None),
    ])

    result = validator.validate_patients(df)
    assert result.valid.count() == 0
    assert result.rejected.collect()[0]["rejection_reason"] == "invalid blood_type"


def test_patient_with_unknown_blood_type_is_rejected(validator: DataValidator, spark):
    df = _patient_rows(spark, [
        ("HOSP-000001", "Ana", "1980-05-12", "F", "XYZ"),
    ])

    result = validator.validate_patients(df)
    assert result.valid.count() == 0
    assert result.rejected.collect()[0]["rejection_reason"] == "invalid blood_type"


def test_patient_validator_separates_mixed_rows(validator: DataValidator, spark):
    df = _patient_rows(spark, [
        ("HOSP-000001", "Ana", "1980-05-12", "F", "A+"),
        ("HOSP-000002", "", "1975-03-22", "M", "O-"),
        ("HOSP-000003", "Luis", "12/05/1980", "M", "B+"),
        ("HOSP-000004", "Marta", "1990-01-01", "F", "AB-"),
    ])

    result = validator.validate_patients(df)
    assert result.valid.count() == 2
    assert result.rejected.count() == 2
    valid_ids = {r["external_id"] for r in result.valid.collect()}
    assert valid_ids == {"HOSP-000001", "HOSP-000004"}


def test_patient_rejection_reason_reports_first_failing_rule(validator: DataValidator, spark):
    # Two errors in the same row — reason should deterministically pick the first
    df = _patient_rows(spark, [
        ("BAD-FORMAT", "", "bad-date", "X", "XYZ"),
    ])
    result = validator.validate_patients(df)
    assert result.rejected.collect()[0]["rejection_reason"] == "invalid external_id"


# ---------------------------------------------------------------------------
# Admissions
# ---------------------------------------------------------------------------

def test_valid_admissions_pass_unchanged(validator: DataValidator, spark):
    df = _admission_rows(spark, [
        ("HOSP-000001", "2025-03-10", "2025-03-15", "UCI", "J18.9", "Pneumonia", "discharged"),
        ("HOSP-000002", "2025-04-01", None, "Urgencias", "R50.9", "Fever", "admitted"),
    ])
    result = validator.validate_admissions(df)
    assert result.valid.count() == 2
    assert result.rejected.count() == 0


def test_admission_with_bad_date_is_rejected(validator: DataValidator, spark):
    df = _admission_rows(spark, [
        ("HOSP-000001", "10/03/2025", None, "UCI", "J18.9", "Pneumonia", "admitted"),
    ])
    result = validator.validate_admissions(df)
    assert result.valid.count() == 0
    assert result.rejected.collect()[0]["rejection_reason"] == "invalid admission_date"


def test_admission_with_unknown_status_is_rejected(validator: DataValidator, spark):
    df = _admission_rows(spark, [
        ("HOSP-000001", "2025-03-10", None, "UCI", "J18.9", "Pneumonia", "unknown"),
    ])
    result = validator.validate_admissions(df)
    assert result.valid.count() == 0
    assert result.rejected.collect()[0]["rejection_reason"] == "invalid status"


def test_admission_with_null_status_is_rejected(validator: DataValidator, spark):
    df = _admission_rows(spark, [
        ("HOSP-000001", "2025-03-10", None, "UCI", "J18.9", "Pneumonia", None),
    ])
    result = validator.validate_admissions(df)
    assert result.valid.count() == 0
    assert result.rejected.collect()[0]["rejection_reason"] == "invalid status"


def test_admission_with_missing_department_is_rejected(validator: DataValidator, spark):
    df = _admission_rows(spark, [
        ("HOSP-000001", "2025-03-10", None, None, "J18.9", "Pneumonia", "admitted"),
    ])
    result = validator.validate_admissions(df)
    assert result.valid.count() == 0
    assert result.rejected.collect()[0]["rejection_reason"] == "missing department"


def test_validator_preserves_source_file_column_when_present(validator: DataValidator, spark):
    cols = ["external_id", "name", "birth_date", "gender", "blood_type", "_source_file"]
    df = spark.createDataFrame(
        [("HOSP-000001", "Ana", "1980-05-12", "F", "A+", "patients.csv")],
        cols,
    )
    result = validator.validate_patients(df)
    assert "_source_file" in result.valid.columns
