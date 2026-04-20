"""Tests for the synthetic hospital data generator."""
import csv
from pathlib import Path

from src.pipeline.scripts.generate_data import (
    PATIENT_COLUMNS,
    ADMISSION_COLUMNS,
    generate_admissions,
    generate_patients,
)


def test_generate_patients_writes_csv_with_expected_columns(tmp_path: Path):
    output = tmp_path / "patients.csv"
    generate_patients(n=10, output_path=output, edge_case_ratio=0.0, seed=42)

    with output.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == list(PATIENT_COLUMNS)


def test_generate_patients_zero_edge_cases_produces_clean_data(tmp_path: Path):
    output = tmp_path / "patients.csv"
    ids = generate_patients(n=50, output_path=output, edge_case_ratio=0.0, seed=42)

    assert len(ids) == 50
    with output.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 50
    for row in rows:
        assert row["external_id"]
        assert row["name"]
        assert row["birth_date"]
        assert row["gender"] in {"M", "F", "Other"}
        assert row["blood_type"] in {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}


def test_generate_patients_with_edge_cases_injects_issues(tmp_path: Path):
    output = tmp_path / "patients.csv"
    generate_patients(n=300, output_path=output, edge_case_ratio=0.3, seed=42)

    with output.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    nulls = sum(1 for r in rows if not r["name"] or not r["birth_date"] or not r["gender"])
    malformed = sum(1 for r in rows if "/" in r["birth_date"])
    dup_ids = len(rows) - len({r["external_id"]: None for r in rows})

    assert nulls > 0, "Edge cases should inject null fields"
    assert malformed > 0, "Edge cases should inject malformed dates"
    assert dup_ids > 0, "Edge cases should inject duplicates"


def test_generate_admissions_writes_csv_with_expected_columns(tmp_path: Path):
    output = tmp_path / "admissions.csv"
    generate_admissions(
        patient_external_ids=["HOSP-000001"],
        n=5,
        output_path=output,
        edge_case_ratio=0.0,
        seed=42,
    )

    with output.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == list(ADMISSION_COLUMNS)


def test_generate_admissions_references_provided_patients(tmp_path: Path):
    patient_ids = [f"HOSP-{i:06d}" for i in range(5)]
    output = tmp_path / "admissions.csv"
    generate_admissions(
        patient_external_ids=patient_ids,
        n=50,
        output_path=output,
        edge_case_ratio=0.0,
        seed=42,
    )

    with output.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 50
    for row in rows:
        assert row["patient_external_id"] in patient_ids


def test_generate_admissions_edge_cases_create_orphans(tmp_path: Path):
    patient_ids = [f"HOSP-{i:06d}" for i in range(5)]
    output = tmp_path / "admissions.csv"
    generate_admissions(
        patient_external_ids=patient_ids,
        n=200,
        output_path=output,
        edge_case_ratio=0.3,
        seed=42,
    )

    with output.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    orphans = sum(1 for r in rows if r["patient_external_id"] not in patient_ids)
    assert orphans > 0, "Edge cases should inject orphan admissions"


def test_generation_is_deterministic_with_same_seed(tmp_path: Path):
    out1 = tmp_path / "p1.csv"
    out2 = tmp_path / "p2.csv"
    generate_patients(n=30, output_path=out1, edge_case_ratio=0.1, seed=123)
    generate_patients(n=30, output_path=out2, edge_case_ratio=0.1, seed=123)

    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")
