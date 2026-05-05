"""Fixtures for end-to-end acceptance tests.

These tests assume the full stack is up (`docker compose up`). When a service
is unreachable, the relevant tests are skipped with a clear message instead
of erroring out.
"""
from __future__ import annotations

import os
import socket

import pytest


def _can_reach(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _resolve(env: str, default: str) -> str:
    return os.environ.get(env, default)


@pytest.fixture(scope="session")
def mongo_client():
    host = _resolve("MONGO_HOST", "mongodb")
    # When tests run on the host (not inside docker network), fall back to localhost
    if not _can_reach(host, int(_resolve("MONGO_PORT", "27017"))):
        host = "localhost"
    port = int(_resolve("MONGO_PORT", "27017"))
    if not _can_reach(host, port):
        pytest.skip(f"MongoDB not reachable at {host}:{port}")
    from pymongo import MongoClient
    client = MongoClient(host=host, port=port)
    yield client
    client.close()


@pytest.fixture(scope="session")
def mongo_db(mongo_client):
    name = _resolve("MONGO_DB", "hospital")
    return mongo_client[name]


@pytest.fixture(scope="session")
def minio_client():
    host = _resolve("MINIO_HOST", "minio")
    if not _can_reach(host, int(_resolve("MINIO_PORT", "9000"))):
        host = "localhost"
    port = int(_resolve("MINIO_PORT", "9000"))
    if not _can_reach(host, port):
        pytest.skip(f"MinIO not reachable at {host}:{port}")
    from minio import Minio
    return Minio(
        endpoint=f"{host}:{port}",
        access_key=_resolve("MINIO_ROOT_USER", "minioadmin"),
        secret_key=_resolve("MINIO_ROOT_PASSWORD", "minioadmin123"),
        secure=False,
    )


@pytest.fixture(scope="session")
def api_url():
    """Base URL of the API. Skips if not reachable from where the tests run."""
    candidates = ["api", "localhost", "127.0.0.1"]
    port = int(_resolve("API_PORT", "8000"))
    for host in candidates:
        if _can_reach(host, port):
            return f"http://{host}:{port}"
    pytest.skip(f"API not reachable on port {port}")


@pytest.fixture(scope="session")
def http():
    import httpx
    yield httpx.Client(timeout=10)


@pytest.fixture(scope="session")
def spark_session():
    """A local SparkSession reused across tests that need it."""
    from src.pipeline.spark_session import get_spark_session
    spark = get_spark_session(app_name="test-e2e", master="local[2]")
    yield spark
    spark.stop()
