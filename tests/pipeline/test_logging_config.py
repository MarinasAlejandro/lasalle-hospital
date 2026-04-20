"""Tests for centralized logging configuration."""
import logging

from src.pipeline.logging_config import (
    DEFAULT_LOG_FORMAT,
    get_logger,
    setup_logging,
)


def test_get_logger_returns_logger_with_given_name():
    logger = get_logger("test.module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test.module"


def test_get_logger_is_usable_without_errors():
    logger = get_logger("test.usability")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")


def test_default_log_format_includes_required_fields():
    assert "%(asctime)s" in DEFAULT_LOG_FORMAT
    assert "%(levelname)s" in DEFAULT_LOG_FORMAT
    assert "%(name)s" in DEFAULT_LOG_FORMAT
    assert "%(message)s" in DEFAULT_LOG_FORMAT


def test_setup_logging_is_idempotent():
    """Calling setup_logging multiple times should not raise."""
    setup_logging()
    setup_logging()
    setup_logging()


def test_get_logger_propagates_messages(caplog):
    """A log call should be captured by pytest's caplog at the expected level."""
    logger = get_logger("test.propagation")
    with caplog.at_level(logging.INFO, logger="test.propagation"):
        logger.info("hospital message")
    assert any("hospital message" in record.message for record in caplog.records)
