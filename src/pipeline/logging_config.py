"""Centralized logging configuration for the hospital pipeline."""
from __future__ import annotations

import logging
import os
import sys

DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str | None = None, log_format: str | None = None) -> None:
    """Configure the root logger once for the entire pipeline.

    Subsequent calls are no-ops to avoid duplicating handlers.
    """
    root = logging.getLogger()
    if root.handlers:
        return

    resolved_level = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    fmt = log_format or DEFAULT_LOG_FORMAT

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt=DEFAULT_DATE_FORMAT))

    root.addHandler(handler)
    root.setLevel(resolved_level)


def get_logger(name: str) -> logging.Logger:
    """Return a logger that shares the pipeline-wide configuration."""
    setup_logging()
    return logging.getLogger(name)
