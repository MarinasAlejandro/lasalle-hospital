"""Bring the hospital stack to a ready-to-use state.

Runs automatically at `docker compose up` via the pipeline service. It does
the work needed to turn a fresh set of containers into a demo-ready system:

  1. Verify that synthetic fixtures are present on disk (committed to the repo)
  2. Upload the example radiographies into the MinIO `radiographies` bucket
  3. Smoke-check connectivity with MongoDB

The step is idempotent: if MinIO already has radiographies, the upload is
skipped so re-running the stack is cheap.
"""
from __future__ import annotations

from pathlib import Path

from src.pipeline.ingesters.image_ingester import ImageIngester
from src.pipeline.logging_config import get_logger
from src.pipeline.storage.minio_client import get_minio_client_from_env
from src.pipeline.storage.mongo_writer import get_mongo_writer_from_env

logger = get_logger(__name__)

DATA_DIR = Path("/app/data/raw")
IMAGES_BUCKET = "radiographies"


def main() -> None:
    logger.info("=== Hospital pipeline bootstrap ===")

    patients_csv = DATA_DIR / "patients.csv"
    admissions_csv = DATA_DIR / "admissions.csv"
    images_dir = DATA_DIR / "images"

    for required in (patients_csv, admissions_csv, images_dir):
        if not required.exists():
            raise SystemExit(
                f"Missing fixture: {required}. The repository must ship "
                f"data/raw/ with the synthetic dataset."
            )

    logger.info(
        "Fixtures detected: %s (%d bytes), %s (%d bytes), %s (%d images)",
        patients_csv.name,
        patients_csv.stat().st_size,
        admissions_csv.name,
        admissions_csv.stat().st_size,
        images_dir,
        sum(1 for _ in images_dir.iterdir()),
    )

    minio = get_minio_client_from_env()
    minio.ensure_bucket(IMAGES_BUCKET)
    existing = minio.list_objects(IMAGES_BUCKET)
    if existing:
        logger.info(
            "MinIO already has %d radiographies in '%s' — skipping upload",
            len(existing),
            IMAGES_BUCKET,
        )
    else:
        ingester = ImageIngester(minio_client=minio, bucket=IMAGES_BUCKET)
        ingested = ingester.ingest_directory(images_dir)
        logger.info(
            "Uploaded %d radiographies to MinIO bucket '%s'",
            len(ingested),
            IMAGES_BUCKET,
        )

    mongo = get_mongo_writer_from_env()
    try:
        mongo._client.admin.command("ping")
        logger.info("MongoDB connection OK (db=%s)", mongo.db.name)
    finally:
        mongo.close()

    logger.info("=== Bootstrap complete. System is ready. ===")


if __name__ == "__main__":
    main()
