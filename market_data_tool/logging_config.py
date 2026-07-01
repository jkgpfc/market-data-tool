"""Logging configuration."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """Configure root logging for console and optional file output."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=handlers,
        force=True,
    )
