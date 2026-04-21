"""Integration tests for the pipeline endpoints (POST /trigger, GET /runs...)."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

pymongo = pytest.importorskip("pymongo")
fastapi = pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from src.api.main import build_app
from src.pipeline.storage.mongo_writer import MongoWriter


TEST_DB_NAME = "hospital_test_t10_pipeline"


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


def test_list_runs_empty_when_no_runs(client: TestClient):
    response = client.get("/api/v1/pipeline/runs")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_list_runs_returns_stored_runs_newest_first(
    client: TestClient, mongo_writer: MongoWriter
):
    now = datetime.now(timezone.utc)
    # Insert via the writer's existing API
    older_id = mongo_writer.start_pipeline_run(trigger_type="manual")
    mongo_writer.finish_pipeline_run(
        older_id, status="success",
        stats={"records_processed": 100, "records_rejected": 5, "images_processed": 0},
    )
    newer_id = mongo_writer.start_pipeline_run(trigger_type="manual")
    mongo_writer.finish_pipeline_run(
        newer_id, status="failed",
        error_message="something broke",
    )

    response = client.get("/api/v1/pipeline/runs")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    # Newest first
    assert items[0]["status"] == "failed"
    assert items[1]["status"] == "success"
    assert items[1]["records_processed"] == 100


def test_pipeline_status_returns_last_run(
    client: TestClient, mongo_writer: MongoWriter
):
    run_id = mongo_writer.start_pipeline_run(trigger_type="watcher")
    mongo_writer.finish_pipeline_run(
        run_id, status="success",
        stats={"records_processed": 42, "records_rejected": 0, "images_processed": 0},
    )

    response = client.get("/api/v1/pipeline/status")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["records_processed"] == 42


def test_pipeline_status_returns_404_when_no_runs(client: TestClient):
    response = client.get("/api/v1/pipeline/status")
    assert response.status_code == 404
