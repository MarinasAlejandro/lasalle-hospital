"""Wrapper around pymongo with hospital-specific write operations."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import MongoClient, UpdateOne

from src.pipeline.logging_config import get_logger

logger = get_logger(__name__)


class MongoWriter:
    def __init__(self, host: str, port: int, db_name: str) -> None:
        self._client: MongoClient = MongoClient(host=host, port=port)
        self.db = self._client[db_name]

    def close(self) -> None:
        self._client.close()

    def ping(self) -> bool:
        """Verify the MongoDB server is reachable. Raises on failure."""
        self._client.admin.command("ping")
        return True

    def bulk_upsert_patients(self, records: list[dict]) -> dict[str, int]:
        """Upsert patients by external_id. Safe with empty input."""
        if not records:
            return {"upserted": 0, "modified": 0}

        now = datetime.now(timezone.utc)
        ops = []
        for record in records:
            payload = {**record, "updated_at": now}
            ops.append(
                UpdateOne(
                    {"external_id": record["external_id"]},
                    {
                        "$set": payload,
                        "$setOnInsert": {"created_at": now},
                    },
                    upsert=True,
                )
            )

        result = self.db.patients.bulk_write(ops, ordered=False)
        stats = {
            "upserted": len(result.upserted_ids),
            "modified": result.modified_count,
        }
        logger.info(
            "Patients bulk upsert: %d upserted, %d modified",
            stats["upserted"],
            stats["modified"],
        )
        return stats

    def add_radiography_to_patient(
        self, external_id: str, radiography: dict[str, Any]
    ) -> bool:
        """Add a radiography metadata dict to the patient's array, idempotently.

        Returns True if the patient exists (regardless of whether the entry was
        new or already present), False if no patient with that external_id
        exists. Re-adding the same `minio_object_key` for the same patient is a
        no-op, which is required by CB-4 (running the pipeline twice must not
        create duplicates).
        """
        if self.db.patients.count_documents({"external_id": external_id}, limit=1) == 0:
            return False

        object_key = radiography["minio_object_key"]
        self.db.patients.update_one(
            {
                "external_id": external_id,
                "radiographies.minio_object_key": {"$ne": object_key},
            },
            {
                "$push": {"radiographies": radiography},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )
        return True

    def start_pipeline_run(self, trigger_type: str = "manual") -> ObjectId:
        doc = {
            "trigger_type": trigger_type,
            "started_at": datetime.now(timezone.utc),
            "finished_at": None,
            "status": "running",
            "records_processed": 0,
            "records_rejected": 0,
            "images_processed": 0,
            "error_message": None,
        }
        result = self.db.pipeline_runs.insert_one(doc)
        logger.info("Pipeline run started: %s (trigger=%s)", result.inserted_id, trigger_type)
        return result.inserted_id

    def finish_pipeline_run(
        self,
        run_id: ObjectId,
        status: str,
        stats: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        update: dict[str, Any] = {
            "status": status,
            "finished_at": datetime.now(timezone.utc),
        }
        if stats:
            update.update(stats)
        if error_message is not None:
            update["error_message"] = error_message

        self.db.pipeline_runs.update_one({"_id": run_id}, {"$set": update})
        logger.info("Pipeline run finished: %s status=%s", run_id, status)

    def write_rejected(self, records: list[dict], pipeline_run_id: ObjectId) -> int:
        if not records:
            return 0
        now = datetime.now(timezone.utc)
        payload = [
            {**record, "pipeline_run_id": pipeline_run_id, "created_at": now}
            for record in records
        ]
        result = self.db.rejected_records.insert_many(payload)
        logger.info(
            "Stored %d rejected records for run %s",
            len(result.inserted_ids),
            pipeline_run_id,
        )
        return len(result.inserted_ids)


def get_mongo_writer_from_env(db_name: str | None = None) -> MongoWriter:
    return MongoWriter(
        host=os.environ["MONGO_HOST"],
        port=int(os.environ.get("MONGO_PORT", "27017")),
        db_name=db_name or os.environ["MONGO_DB"],
    )
