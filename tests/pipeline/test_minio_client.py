"""Integration tests for MinIOClient against the running MinIO service."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from src.pipeline.storage.minio_client import MinIOClient, get_minio_client_from_env


@pytest.fixture(scope="module")
def minio_client() -> MinIOClient:
    return get_minio_client_from_env()


@pytest.fixture
def test_bucket(minio_client: MinIOClient) -> str:
    bucket = f"test-bucket-{uuid.uuid4().hex[:12]}"
    minio_client.ensure_bucket(bucket)
    yield bucket
    for key in minio_client.list_objects(bucket):
        minio_client.remove_object(bucket, key)
    minio_client.remove_bucket(bucket)


def test_ensure_bucket_is_idempotent(minio_client: MinIOClient, test_bucket: str):
    minio_client.ensure_bucket(test_bucket)
    minio_client.ensure_bucket(test_bucket)
    assert minio_client.bucket_exists(test_bucket)


def test_upload_bytes_and_exists(minio_client: MinIOClient, test_bucket: str):
    key = "sample.txt"
    minio_client.upload_bytes(test_bucket, key, b"hola hospital", content_type="text/plain")

    assert minio_client.exists(test_bucket, key)
    assert not minio_client.exists(test_bucket, "missing.txt")


def test_upload_file_and_download_file(
    minio_client: MinIOClient, test_bucket: str, tmp_path: Path
):
    source = tmp_path / "source.bin"
    source.write_bytes(b"radiografia_payload")
    minio_client.upload_file(test_bucket, "radios/xray1.bin", source)

    downloaded = tmp_path / "downloaded.bin"
    minio_client.download_file(test_bucket, "radios/xray1.bin", downloaded)
    assert downloaded.read_bytes() == b"radiografia_payload"


def test_list_objects_with_prefix(minio_client: MinIOClient, test_bucket: str):
    minio_client.upload_bytes(test_bucket, "a/1.txt", b"one")
    minio_client.upload_bytes(test_bucket, "a/2.txt", b"two")
    minio_client.upload_bytes(test_bucket, "b/3.txt", b"three")

    under_a = set(minio_client.list_objects(test_bucket, prefix="a/"))
    assert under_a == {"a/1.txt", "a/2.txt"}

    all_objects = set(minio_client.list_objects(test_bucket))
    assert all_objects == {"a/1.txt", "a/2.txt", "b/3.txt"}


def test_remove_object_makes_it_gone(minio_client: MinIOClient, test_bucket: str):
    minio_client.upload_bytes(test_bucket, "to_delete.txt", b"bye")
    assert minio_client.exists(test_bucket, "to_delete.txt")

    minio_client.remove_object(test_bucket, "to_delete.txt")
    assert not minio_client.exists(test_bucket, "to_delete.txt")


def test_get_minio_client_from_env_uses_env_vars():
    assert os.environ["MINIO_HOST"]
    client = get_minio_client_from_env()
    assert client is not None
