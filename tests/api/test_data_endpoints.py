"""Integration tests for the data endpoints (GET /patients, /admissions...)."""
from __future__ import annotations

import os

import pytest

pymongo = pytest.importorskip("pymongo")
fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from src.api.main import build_app
from src.pipeline.storage.mongo_writer import MongoWriter


TEST_DB_NAME = "hospital_test_t10"


@pytest.fixture
def mongo_writer():
    w = MongoWriter(
        host=os.environ["MONGO_HOST"],
        port=int(os.environ.get("MONGO_PORT", "27017")),
        db_name=TEST_DB_NAME,
    )
    w.db.patients.drop()
    w.db.pipeline_runs.drop()
    w.db.rejected_records.drop()
    yield w
    w.db.patients.drop()
    w.db.pipeline_runs.drop()
    w.db.rejected_records.drop()
    w.close()


@pytest.fixture
def client(mongo_writer: MongoWriter) -> TestClient:
    app = build_app(mongo_db_name=TEST_DB_NAME)
    return TestClient(app)


def _seed(writer: MongoWriter, patients: list[dict], admissions: list[dict] | None = None) -> None:
    writer.bulk_upsert_patients_with_admissions(patients, admissions or [])


def test_health_endpoint_returns_ok(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_patients_returns_empty_when_no_data(client: TestClient):
    response = client.get("/api/v1/patients")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_list_patients_returns_stored_patients(
    client: TestClient, mongo_writer: MongoWriter
):
    _seed(mongo_writer, [
        {"external_id": "HOSP-000001", "name": "Ana", "age": 45, "gender": "F"},
        {"external_id": "HOSP-000002", "name": "Luis", "age": 50, "gender": "M"},
    ])

    response = client.get("/api/v1/patients")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    ids = sorted(p["external_id"] for p in body["items"])
    assert ids == ["HOSP-000001", "HOSP-000002"]


def test_list_patients_pagination_respects_limit_and_offset(
    client: TestClient, mongo_writer: MongoWriter
):
    _seed(mongo_writer, [
        {"external_id": f"HOSP-{i:06d}", "name": f"P{i}", "age": 30}
        for i in range(25)
    ])

    response = client.get("/api/v1/patients?limit=10&offset=0")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 10

    response = client.get("/api/v1/patients?limit=10&offset=20")
    assert len(response.json()["items"]) == 5


def test_get_patient_by_external_id_returns_detail(
    client: TestClient, mongo_writer: MongoWriter
):
    _seed(
        mongo_writer,
        [{"external_id": "HOSP-000001", "name": "Ana", "age": 45}],
        [{"patient_external_id": "HOSP-000001", "admission_date": "2025-03-10",
          "department": "UCI", "status": "admitted", "diagnosis_code": "J18.9",
          "diagnosis_category": "Pneumonia"}],
    )

    response = client.get("/api/v1/patients/HOSP-000001")
    assert response.status_code == 200
    patient = response.json()
    assert patient["external_id"] == "HOSP-000001"
    assert patient["name"] == "Ana"
    assert len(patient["admissions"]) == 1


def test_get_patient_returns_404_when_not_found(client: TestClient):
    response = client.get("/api/v1/patients/HOSP-999999")
    assert response.status_code == 404


def test_list_admissions_flattens_across_patients(
    client: TestClient, mongo_writer: MongoWriter
):
    _seed(
        mongo_writer,
        [{"external_id": "HOSP-000001", "name": "Ana"},
         {"external_id": "HOSP-000002", "name": "Luis"}],
        [
            {"patient_external_id": "HOSP-000001", "admission_date": "2025-03-10",
             "department": "UCI", "status": "admitted", "diagnosis_code": "J18.9"},
            {"patient_external_id": "HOSP-000001", "admission_date": "2025-06-01",
             "department": "Urgencias", "status": "discharged", "diagnosis_code": "U07.1"},
            {"patient_external_id": "HOSP-000002", "admission_date": "2025-04-05",
             "department": "Cardiologia", "status": "admitted", "diagnosis_code": "I21.9"},
        ],
    )

    response = client.get("/api/v1/admissions")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3


def test_list_radiographies_flattens_across_patients(
    client: TestClient, mongo_writer: MongoWriter
):
    _seed(
        mongo_writer,
        [
            {"external_id": "HOSP-000001", "name": "Ana",
             "radiographies": [
                 {"minio_object_key": "HOSP-000001/x1.png",
                  "ingested_at": "2026-04-21T12:00:00+00:00"},
             ]},
            {"external_id": "HOSP-000002", "name": "Luis",
             "radiographies": [
                 {"minio_object_key": "HOSP-000002/x1.png",
                  "ingested_at": "2026-04-21T12:00:00+00:00"},
                 {"minio_object_key": "HOSP-000002/x2.png",
                  "ingested_at": "2026-04-21T13:00:00+00:00"},
             ]},
        ],
    )

    response = client.get("/api/v1/radiographies")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
