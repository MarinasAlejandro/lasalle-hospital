"""Integration tests for SparkSession factory. Requires PySpark installed."""
import pytest

pyspark = pytest.importorskip("pyspark", reason="PySpark not installed")

from src.pipeline.spark_session import get_spark_session


@pytest.fixture(scope="module")
def spark():
    session = get_spark_session(app_name="test-session", master="local[2]")
    yield session
    session.stop()


def test_spark_session_is_created(spark):
    assert spark is not None
    assert spark.version is not None


def test_spark_session_has_expected_app_name(spark):
    assert spark.sparkContext.appName == "test-session"


def test_spark_session_can_create_dataframe(spark):
    df = spark.createDataFrame([(1, "a"), (2, "b")], ["id", "value"])
    assert df.count() == 2
    assert df.columns == ["id", "value"]


def test_spark_session_reuses_existing_instance(spark):
    another = get_spark_session(app_name="test-session", master="local[2]")
    assert another is spark
