"""
logger.py — Structured JSON logging to stdout for the Scheduler Service.

Usage:
    from logger import get_logger
    log = get_logger("tasks.scrape")
    log.info("Scraper triggered", jobs_before=12)
    log.error("HTTP failure", status=503, url="http://scraper:8001/scrape")

All output goes to stdout so Docker / container runtimes can collect it
via their standard logging drivers.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class _JSONFormatter(logging.Formatter):
    """Emit every log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts":      datetime.now(timezone.utc).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
        }
        # Attach any extra keyword args passed to log.info("msg", key=val)
        for key, val in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            ):
                payload[key] = val

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


class StructLogger(logging.LoggerAdapter):
    """Adapter to move arbitrary kwargs into the `extra` dict, so they become LogRecord attributes."""
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        new_kwargs = {}
        # Keys natively supported by Logger._log()
        native_kwargs = {"exc_info", "stack_info", "stacklevel"}
        for k, v in kwargs.items():
            if k in native_kwargs:
                new_kwargs[k] = v
            elif k != "extra":
                # Convert dict to a new dict if it was empty initially, or just mutate
                if not isinstance(extra, dict):
                    extra = dict(extra)
                extra[k] = v
        if extra:
            new_kwargs["extra"] = extra
        return msg, new_kwargs


def get_logger(name: str) -> StructLogger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return StructLogger(logger, {})
