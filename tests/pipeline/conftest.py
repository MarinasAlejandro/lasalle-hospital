"""Auto-skip integration tests when their backing services are unavailable.

Tests that talk to MinIO or MongoDB should only run when those services are
actually reachable. Otherwise pytest hits raw KeyErrors or connection errors
during collection/setup, which is noisy and confusing for anyone running
`pytest` without having the stack up.

This conftest detects availability once per session and marks the relevant
tests as skipped with a friendly message.
"""
from __future__ import annotations

import os
import socket

import pytest

MINIO_TEST_FILES = {
    "test_minio_client.py",
    "test_image_ingester.py",
}
MONGO_TEST_FILES = {
    "test_mongo_writer.py",
}


def _can_reach_tcp(host_env: str, port_env: str, default_port: int) -> bool:
    host = os.environ.get(host_env) or "localhost"
    try:
        port = int(os.environ.get(port_env, default_port))
    except ValueError:
        return False
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def pytest_collection_modifyitems(config, items):
    minio_up = _can_reach_tcp("MINIO_HOST", "MINIO_PORT", 9000)
    mongo_up = _can_reach_tcp("MONGO_HOST", "MONGO_PORT", 27017)

    skip_minio = pytest.mark.skip(
        reason="MinIO not reachable — run `docker compose up -d minio` or execute tests inside the pipeline container"
    )
    skip_mongo = pytest.mark.skip(
        reason="MongoDB not reachable — run `docker compose up -d mongodb` or execute tests inside the pipeline container"
    )

    for item in items:
        filename = os.path.basename(str(item.fspath))
        if filename in MINIO_TEST_FILES and not minio_up:
            item.add_marker(skip_minio)
        if filename in MONGO_TEST_FILES and not mongo_up:
            item.add_marker(skip_mongo)
