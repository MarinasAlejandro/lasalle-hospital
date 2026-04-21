"""Ingest chest X-ray PNG images into MinIO with extracted metadata."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.pipeline.logging_config import get_logger
from src.pipeline.storage.minio_client import MinIOClient

logger = get_logger(__name__)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Files are expected to follow `{patient_external_id}_{suffix}.png`
# where patient_external_id is HOSP-NNNNNN.
PATIENT_PREFIX_PATTERN = re.compile(r"^(HOSP-\d{6})_")


@dataclass(frozen=True)
class IngestedImage:
    patient_external_id: str
    original_filename: str
    minio_object_key: str
    file_size_bytes: int
    capture_date: str  # ISO date


class ImageIngester:
    def __init__(self, minio_client: MinIOClient, bucket: str) -> None:
        self._minio = minio_client
        self._bucket = bucket

    def ingest_directory(self, directory: Path) -> list[IngestedImage]:
        """Upload every valid PNG in `directory` to MinIO and return metadata."""
        path = Path(directory)
        if not path.exists():
            raise FileNotFoundError(f"Image directory does not exist: {path}")

        self._minio.ensure_bucket(self._bucket)

        ingested: list[IngestedImage] = []
        for image_path in sorted(path.iterdir()):
            if not image_path.is_file():
                continue

            meta = self._ingest_one(image_path)
            if meta is not None:
                ingested.append(meta)

        logger.info(
            "Ingested %d images from %s into bucket %s",
            len(ingested),
            path,
            self._bucket,
        )
        return ingested

    def _ingest_one(self, image_path: Path) -> IngestedImage | None:
        # Filter by extension and naming convention
        if image_path.suffix.lower() != ".png":
            logger.debug("Skipping non-PNG file: %s", image_path.name)
            return None

        match = PATIENT_PREFIX_PATTERN.match(image_path.name)
        if not match:
            logger.warning(
                "Skipping file with unexpected name pattern: %s (expected HOSP-NNNNNN_*.png)",
                image_path.name,
            )
            return None
        patient_id = match.group(1)

        # Validate PNG signature — CB-2: corrupt images must not crash the run
        try:
            with image_path.open("rb") as f:
                header = f.read(len(PNG_SIGNATURE))
        except OSError as exc:
            logger.error("Could not read %s: %s", image_path.name, exc)
            return None

        if header != PNG_SIGNATURE:
            logger.warning("Skipping corrupt/invalid PNG: %s", image_path.name)
            return None

        # Build object key: {patient}/{ts}_{filename}
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        object_key = f"{patient_id}/{timestamp}_{image_path.name}"
        file_size = image_path.stat().st_size

        try:
            self._minio.upload_file(self._bucket, object_key, image_path)
        except Exception as exc:  # pragma: no cover - depends on MinIO being up
            logger.error("Failed to upload %s: %s", image_path.name, exc)
            return None

        return IngestedImage(
            patient_external_id=patient_id,
            original_filename=image_path.name,
            minio_object_key=object_key,
            file_size_bytes=file_size,
            capture_date=datetime.now(timezone.utc).date().isoformat(),
        )
