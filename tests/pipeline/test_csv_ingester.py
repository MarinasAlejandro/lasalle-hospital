"""Tests for CSVIngester. Reads CSVs into PySpark DataFrames."""
from __future__ import annotations

from pathlib import Path

import pytest

pyspark = pytest.importorskip("pyspark", reason="PySpark not installed")

from src.pipeline.ingesters.csv_ingester import (
    CSVIngester,
    MissingColumnsError,
    PATIENT_SCHEMA_COLUMNS,
    ADMISSION_SCHEMA_COLUMNS,
)
from src.pipeline.spark_session import get_spark_session


@pytest.fixture(scope="module")
def spark():
    session = get_spark_session(app_name="test-csv-ingester", master="local[2]")
    yield session
    session.stop()


@pytest.fixture
def ingester(spark) -> CSVIngester:
    return CSVIngester(spark)


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    lines = [",".join(header)]
    for row in rows:
        lines.append(",".join(row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_read_patients_returns_dataframe_with_all_columns(
    ingester: CSVIngester, tmp_path: Path
):
    csv_file = tmp_path / "patients.csv"
    _write_csv(
        csv_file,
        ["external_id", "name", "birth_date", "gender", "blood_type"],
        [
            ["HOSP-000001", "Ana Garcia", "1980-05-12", "F", "A+"],
            ["HOSP-000002", "Luis Perez", "1975-03-22", "M", "O-"],
        ],
    )

    df = ingester.read_patients(csv_file)
    assert set(PATIENT_SCHEMA_COLUMNS).issubset(df.columns)
    assert df.count() == 2


def test_read_patients_preserves_all_rows_including_edge_cases(
    ingester: CSVIngester, tmp_path: Path
):
    """Ingester should not filter rows — validation belongs to T7."""
    csv_file = tmp_path / "patients.csv"
    _write_csv(
        csv_file,
        ["external_id", "name", "birth_date", "gender", "blood_type"],
        [
            ["HOSP-000001", "Ana", "1980-05-12", "F", "A+"],
            ["HOSP-000002", "", "1975-03-22", "M", "O-"],
            ["HOSP-000003", "Luis", "", "M", "B+"],
        ],
    )

    df = ingester.read_patients(csv_file)
    assert df.count() == 3


def test_read_patients_accepts_columns_in_different_order(
    ingester: CSVIngester, tmp_path: Path
):
    csv_file = tmp_path / "patients.csv"
    _write_csv(
        csv_file,
        ["blood_type", "gender", "name", "birth_date", "external_id"],
        [["A+", "F", "Ana", "1980-05-12", "HOSP-000001"]],
    )

    df = ingester.read_patients(csv_file)
    row = df.collect()[0]
    assert row["external_id"] == "HOSP-000001"
    assert row["name"] == "Ana"
    assert row["blood_type"] == "A+"


def test_read_patients_raises_when_required_column_missing(
    ingester: CSVIngester, tmp_path: Path
):
    csv_file = tmp_path / "patients.csv"
    _write_csv(
        csv_file,
        ["external_id", "name", "birth_date"],  # missing gender, blood_type
        [["HOSP-000001", "Ana", "1980-05-12"]],
    )

    with pytest.raises(MissingColumnsError) as exc:
        ingester.read_patients(csv_file)
    assert "gender" in str(exc.value)
    assert "blood_type" in str(exc.value)


def test_read_patients_tags_source_file(ingester: CSVIngester, tmp_path: Path):
    csv_file = tmp_path / "patients.csv"
    _write_csv(
        csv_file,
        ["external_id", "name", "birth_date", "gender", "blood_type"],
        [["HOSP-000001", "Ana", "1980-05-12", "F", "A+"]],
    )

    df = ingester.read_patients(csv_file)
    assert "_source_file" in df.columns
    assert df.collect()[0]["_source_file"] == "patients.csv"


def test_read_admissions_returns_dataframe_with_all_columns(
    ingester: CSVIngester, tmp_path: Path
):
    csv_file = tmp_path / "admissions.csv"
    _write_csv(
        csv_file,
        [
            "patient_external_id", "admission_date", "discharge_date",
            "department", "diagnosis_code", "diagnosis_description", "status",
        ],
        [
            ["HOSP-000001", "2025-03-10", "2025-03-15", "UCI", "J18.9",
             "Pneumonia", "discharged"],
        ],
    )

    df = ingester.read_admissions(csv_file)
    assert set(ADMISSION_SCHEMA_COLUMNS).issubset(df.columns)
    assert df.count() == 1


def test_read_admissions_raises_when_required_column_missing(
    ingester: CSVIngester, tmp_path: Path
):
    csv_file = tmp_path / "admissions.csv"
    _write_csv(
        csv_file,
        ["patient_external_id", "admission_date", "department"],
        [["HOSP-000001", "2025-03-10", "UCI"]],
    )

    with pytest.raises(MissingColumnsError):
        ingester.read_admissions(csv_file)


def test_read_patients_handles_empty_csv(ingester: CSVIngester, tmp_path: Path):
    csv_file = tmp_path / "patients.csv"
    _write_csv(
        csv_file,
        ["external_id", "name", "birth_date", "gender", "blood_type"],
        [],
    )

    df = ingester.read_patients(csv_file)
    assert df.count() == 0
    assert set(PATIENT_SCHEMA_COLUMNS).issubset(df.columns)


def test_read_patients_raises_when_file_does_not_exist(
    ingester: CSVIngester, tmp_path: Path
):
    missing = tmp_path / "nope.csv"
    with pytest.raises(FileNotFoundError):
        ingester.read_patients(missing)
