"""Integration tests for MongoWriter against the running MongoDB service."""
from __future__ import annotations

import os

import pytest

from src.pipeline.storage.mongo_writer import MongoWriter, get_mongo_writer_from_env


TEST_DB_NAME = "hospital_test_t4"


@pytest.fixture
def writer():
    w = MongoWriter(
        host=os.environ["MONGO_HOST"],
        port=int(os.environ.get("MONGO_PORT", "27017")),
        db_name=TEST_DB_NAME,
    )
    _reset_db(w)
    yield w
    _reset_db(w)
    w.close()


def _reset_db(w: MongoWriter) -> None:
    w.db.patients.drop()
    w.db.pipeline_runs.drop()
    w.db.rejected_records.drop()


def test_bulk_upsert_patients_inserts_new_documents(writer: MongoWriter):
    records = [
        {"external_id": "HOSP-000001", "name": "Ana", "age": 40},
        {"external_id": "HOSP-000002", "name": "Bob", "age": 55},
    ]
    stats = writer.bulk_upsert_patients(records)

    assert stats["upserted"] == 2
    assert writer.db.patients.count_documents({}) == 2


def test_bulk_upsert_patients_is_idempotent(writer: MongoWriter):
    records = [
        {"external_id": "HOSP-000001", "name": "Ana", "age": 40},
        {"external_id": "HOSP-000002", "name": "Bob", "age": 55},
    ]
    writer.bulk_upsert_patients(records)
    writer.bulk_upsert_patients(records)
    writer.bulk_upsert_patients(records)

    assert writer.db.patients.count_documents({}) == 2


def test_bulk_upsert_patients_updates_existing_fields(writer: MongoWriter):
    writer.bulk_upsert_patients([{"external_id": "HOSP-000001", "name": "Ana", "age": 40}])
    writer.bulk_upsert_patients([{"external_id": "HOSP-000001", "name": "Ana", "age": 41}])

    doc = writer.db.patients.find_one({"external_id": "HOSP-000001"})
    assert doc["age"] == 41


def test_add_radiography_to_patient_appends_to_array(writer: MongoWriter):
    writer.bulk_upsert_patients([{"external_id": "HOSP-000001", "name": "Ana"}])
    radiography = {"minio_object_key": "radios/HOSP-000001_1.png", "ingested_at": "2026-04-20"}

    added = writer.add_radiography_to_patient("HOSP-000001", radiography)
    assert added is True

    doc = writer.db.patients.find_one({"external_id": "HOSP-000001"})
    assert len(doc["radiographies"]) == 1
    assert doc["radiographies"][0]["minio_object_key"] == "radios/HOSP-000001_1.png"


def test_add_radiography_is_idempotent_on_repeated_calls(writer: MongoWriter):
    """CB-4: re-ingesting the same radiography must not create duplicates."""
    writer.bulk_upsert_patients([{"external_id": "HOSP-000001", "name": "Ana"}])
    radiography = {"minio_object_key": "radios/HOSP-000001_1.png", "ingested_at": "2026-04-20"}

    writer.add_radiography_to_patient("HOSP-000001", radiography)
    writer.add_radiography_to_patient("HOSP-000001", radiography)
    writer.add_radiography_to_patient("HOSP-000001", radiography)

    doc = writer.db.patients.find_one({"external_id": "HOSP-000001"})
    assert len(doc["radiographies"]) == 1


def test_add_radiography_returns_false_for_missing_patient(writer: MongoWriter):
    added = writer.add_radiography_to_patient(
        "HOSP-UNKNOWN",
        {"minio_object_key": "x", "ingested_at": "2026-04-20"},
    )
    assert added is False


def test_ping_returns_true_when_mongodb_is_reachable(writer: MongoWriter):
    assert writer.ping() is True


def test_bulk_upsert_patients_with_admissions_embeds_subdocs(writer: MongoWriter):
    patients = [
        {"external_id": "HOSP-000001", "name": "Ana", "age": 45},
        {"external_id": "HOSP-000002", "name": "Luis", "age": 50},
    ]
    admissions = [
        {"patient_external_id": "HOSP-000001", "admission_date": "2025-03-10",
         "department": "UCI", "status": "admitted"},
        {"patient_external_id": "HOSP-000001", "admission_date": "2025-06-01",
         "department": "Urgencias", "status": "discharged"},
        {"patient_external_id": "HOSP-000002", "admission_date": "2025-04-05",
         "department": "Cardiologia", "status": "admitted"},
    ]

    writer.bulk_upsert_patients_with_admissions(patients, admissions)

    ana = writer.db.patients.find_one({"external_id": "HOSP-000001"})
    assert len(ana["admissions"]) == 2
    luis = writer.db.patients.find_one({"external_id": "HOSP-000002"})
    assert len(luis["admissions"]) == 1


def test_bulk_upsert_patients_with_admissions_is_idempotent(writer: MongoWriter):
    patients = [{"external_id": "HOSP-000001", "name": "Ana"}]
    admissions = [
        {"patient_external_id": "HOSP-000001", "admission_date": "2025-03-10",
         "department": "UCI", "status": "admitted"},
    ]

    writer.bulk_upsert_patients_with_admissions(patients, admissions)
    writer.bulk_upsert_patients_with_admissions(patients, admissions)
    writer.bulk_upsert_patients_with_admissions(patients, admissions)

    assert writer.db.patients.count_documents({}) == 1
    ana = writer.db.patients.find_one({"external_id": "HOSP-000001"})
    assert len(ana["admissions"]) == 1


def test_start_and_finish_pipeline_run(writer: MongoWriter):
    run_id = writer.start_pipeline_run(trigger_type="manual")
    assert run_id is not None

    running_doc = writer.db.pipeline_runs.find_one({"_id": run_id})
    assert running_doc["status"] == "running"
    assert running_doc["trigger_type"] == "manual"

    writer.finish_pipeline_run(
        run_id,
        status="success",
        stats={"records_processed": 1234, "records_rejected": 12, "images_processed": 56},
    )

    finished = writer.db.pipeline_runs.find_one({"_id": run_id})
    assert finished["status"] == "success"
    assert finished["records_processed"] == 1234
    assert finished["records_rejected"] == 12
    assert finished["finished_at"] is not None


def test_write_rejected_stores_records_with_run_id(writer: MongoWriter):
    run_id = writer.start_pipeline_run(trigger_type="manual")
    rejected = [
        {"source_file": "patients.csv", "row_number": 42, "rejection_reason": "null name", "raw_data": {"name": ""}},
        {"source_file": "patients.csv", "row_number": 87, "rejection_reason": "bad date", "raw_data": {"birth_date": "31/02/2020"}},
    ]
    inserted = writer.write_rejected(rejected, run_id)
    assert inserted == 2

    docs = list(writer.db.rejected_records.find({"pipeline_run_id": run_id}))
    assert len(docs) == 2
    assert all(d["pipeline_run_id"] == run_id for d in docs)


def test_bulk_upsert_patients_handles_empty_list(writer: MongoWriter):
    stats = writer.bulk_upsert_patients([])
    assert stats["upserted"] == 0
    assert stats["modified"] == 0


def test_get_mongo_writer_from_env_uses_env_vars():
    assert os.environ["MONGO_HOST"]
    w = get_mongo_writer_from_env(db_name=TEST_DB_NAME)
    assert w is not None
    w.close()
