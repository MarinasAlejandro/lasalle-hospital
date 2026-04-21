"""Read-side access to the hospital MongoDB collections.

Kept separate from `MongoWriter` so read and write surfaces can evolve
independently (CQRS-light). Mongo connection management mirrors the writer.
"""
from __future__ import annotations

import os

from pymongo import DESCENDING, MongoClient


class MongoReader:
    def __init__(self, host: str, port: int, db_name: str) -> None:
        self._client: MongoClient = MongoClient(host=host, port=port)
        self.db = self._client[db_name]

    def close(self) -> None:
        self._client.close()

    # -- Patients -----------------------------------------------------------

    def count_patients(self) -> int:
        return self.db.patients.count_documents({})

    def list_patients(self, limit: int, offset: int) -> list[dict]:
        cursor = (
            self.db.patients.find({}, {"_id": 0})
            .sort("external_id", 1)
            .skip(offset)
            .limit(limit)
        )
        return list(cursor)

    def find_patient(self, external_id: str) -> dict | None:
        return self.db.patients.find_one({"external_id": external_id}, {"_id": 0})

    # -- Admissions ---------------------------------------------------------

    def count_admissions(self) -> int:
        pipeline = [
            {"$project": {"n": {"$size": {"$ifNull": ["$admissions", []]}}}},
            {"$group": {"_id": None, "total": {"$sum": "$n"}}},
        ]
        docs = list(self.db.patients.aggregate(pipeline))
        return docs[0]["total"] if docs else 0

    def list_admissions(self, limit: int, offset: int) -> list[dict]:
        pipeline = [
            {"$unwind": "$admissions"},
            {"$sort": {"external_id": 1, "admissions.admission_date": 1}},
            {"$skip": offset},
            {"$limit": limit},
            {"$replaceRoot": {"newRoot": "$admissions"}},
        ]
        return list(self.db.patients.aggregate(pipeline))

    # -- Radiographies ------------------------------------------------------

    def count_radiographies(self) -> int:
        pipeline = [
            {"$project": {"n": {"$size": {"$ifNull": ["$radiographies", []]}}}},
            {"$group": {"_id": None, "total": {"$sum": "$n"}}},
        ]
        docs = list(self.db.patients.aggregate(pipeline))
        return docs[0]["total"] if docs else 0

    def list_radiographies(self, limit: int, offset: int) -> list[dict]:
        pipeline = [
            {"$unwind": "$radiographies"},
            {"$addFields": {
                "radiographies.patient_external_id": "$external_id",
            }},
            {"$sort": {"radiographies.minio_object_key": 1}},
            {"$skip": offset},
            {"$limit": limit},
            {"$replaceRoot": {"newRoot": "$radiographies"}},
        ]
        return list(self.db.patients.aggregate(pipeline))

    # -- Pipeline runs ------------------------------------------------------

    def list_pipeline_runs(self, limit: int, offset: int) -> list[dict]:
        cursor = (
            self.db.pipeline_runs.find({})
            .sort("started_at", DESCENDING)
            .skip(offset)
            .limit(limit)
        )
        return [_stringify_id(doc) for doc in cursor]

    def latest_pipeline_run(self) -> dict | None:
        doc = self.db.pipeline_runs.find_one(
            {}, sort=[("started_at", DESCENDING)]
        )
        return _stringify_id(doc) if doc else None


def _stringify_id(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def get_mongo_reader_from_env(db_name: str | None = None) -> MongoReader:
    return MongoReader(
        host=os.environ["MONGO_HOST"],
        port=int(os.environ.get("MONGO_PORT", "27017")),
        db_name=db_name or os.environ["MONGO_DB"],
    )
