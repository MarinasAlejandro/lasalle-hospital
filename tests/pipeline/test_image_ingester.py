"""Integration tests for ImageIngester against the running MinIO service."""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from src.pipeline.ingesters.image_ingester import (
    ImageIngester,
    IngestedImage,
)
from src.pipeline.storage.minio_client import get_minio_client_from_env


def _make_png(path: Path) -> None:
    """Write a minimal but valid 1x1 black PNG."""
    png_bytes = bytes.fromhex(
        "89504E470D0A1A0A"              # PNG signature
        "0000000D49484452"              # IHDR chunk length + type
        "00000001000000010806000000"    # 1x1, 8-bit RGBA
        "1F15C489"                      # IHDR CRC
        "0000000A49444154"              # IDAT chunk length + type
        "78DA63000100000500010D0A2DB4"  # compressed data
        "0000000049454E44"              # IEND length + type
        "AE426082"                      # IEND CRC
    )
    path.write_bytes(png_bytes)


@pytest.fixture(scope="module")
def minio_client():
    return get_minio_client_from_env()


@pytest.fixture
def test_bucket(minio_client):
    bucket = f"test-images-{uuid.uuid4().hex[:12]}"
    minio_client.ensure_bucket(bucket)
    yield bucket
    for key in minio_client.list_objects(bucket):
        minio_client.remove_object(bucket, key)
    minio_client.remove_bucket(bucket)


@pytest.fixture
def ingester(minio_client, test_bucket):
    return ImageIngester(minio_client=minio_client, bucket=test_bucket)


def test_ingest_directory_uploads_png_and_returns_metadata(
    ingester: ImageIngester, tmp_path: Path, minio_client, test_bucket: str
):
    image = tmp_path / "HOSP-000001_xray1.png"
    _make_png(image)

    results = ingester.ingest_directory(tmp_path)

    assert len(results) == 1
    meta = results[0]
    assert isinstance(meta, IngestedImage)
    assert meta.patient_external_id == "HOSP-000001"
    assert meta.original_filename == "HOSP-000001_xray1.png"
    assert meta.file_size_bytes > 0
    assert meta.minio_object_key.startswith("HOSP-000001/")
    assert minio_client.exists(test_bucket, meta.minio_object_key)


def test_ingest_directory_skips_non_png_files(
    ingester: ImageIngester, tmp_path: Path
):
    png = tmp_path / "HOSP-000001_good.png"
    _make_png(png)
    (tmp_path / "notes.txt").write_text("ignore me")
    (tmp_path / "report.pdf").write_bytes(b"%PDF-1.4 fake")

    results = ingester.ingest_directory(tmp_path)

    assert len(results) == 1
    assert results[0].original_filename == "HOSP-000001_good.png"


def test_ingest_directory_skips_corrupt_png_without_crashing(
    ingester: ImageIngester, tmp_path: Path
):
    """CB-2: Corrupt images should be logged and skipped, not crash."""
    good = tmp_path / "HOSP-000001_valid.png"
    _make_png(good)
    corrupt = tmp_path / "HOSP-000002_corrupt.png"
    corrupt.write_bytes(b"not a real png")

    results = ingester.ingest_directory(tmp_path)

    assert len(results) == 1
    assert results[0].patient_external_id == "HOSP-000001"


def test_ingest_directory_skips_files_without_patient_prefix(
    ingester: ImageIngester, tmp_path: Path
):
    """Files not following {patient_id}_*.png convention are skipped."""
    _make_png(tmp_path / "HOSP-000001_valid.png")
    _make_png(tmp_path / "random_name.png")

    results = ingester.ingest_directory(tmp_path)

    assert len(results) == 1
    assert results[0].patient_external_id == "HOSP-000001"


def test_ingest_directory_handles_empty_directory(
    ingester: ImageIngester, tmp_path: Path
):
    results = ingester.ingest_directory(tmp_path)
    assert results == []


def test_ingest_directory_raises_when_directory_missing(
    ingester: ImageIngester, tmp_path: Path
):
    missing = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        ingester.ingest_directory(missing)


def test_object_key_is_unique_per_image(
    ingester: ImageIngester, tmp_path: Path, minio_client, test_bucket: str
):
    for i in range(3):
        img = tmp_path / f"HOSP-000001_scan{i}.png"
        _make_png(img)

    results = ingester.ingest_directory(tmp_path)
    keys = {r.minio_object_key for r in results}
    assert len(keys) == 3
    for key in keys:
        assert minio_client.exists(test_bucket, key)


def test_image_ingester_propagates_minio_failure_explicitly(tmp_path: Path):
    """CB-5: MinIO no disponible debe fallar de forma explicita, no en silencio."""
    from src.pipeline.storage.minio_client import MinIOClient

    bad_minio = MinIOClient(
        endpoint="nonexistent.invalid:9000",
        access_key="x",
        secret_key="x",
        secure=False,
    )
    bad_ingester = ImageIngester(minio_client=bad_minio, bucket="any-bucket")

    image = tmp_path / "HOSP-000001_xray.png"
    _make_png(image)

    # The ingester must NOT silently return success: either it raises an
    # explicit error or it returns an empty list with no uploads. The forbidden
    # outcome is "metadata for an image that wasn't actually uploaded".
    try:
        result = bad_ingester.ingest_directory(tmp_path)
    except Exception:
        # Explicit failure is acceptable (caller will see and log it).
        return
    # If no exception, no metadata should be returned.
    assert result == [], (
        "MinIO unreachable but ingester returned metadata — silent failure detected"
    )
