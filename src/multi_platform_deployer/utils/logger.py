"""Logging utilities for the deployment package."""

import logging
import sys
from typing import Optional

PACKAGE_LOGGER = "multi_platform_deployer"

FILE_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


class ConsoleFormatter(logging.Formatter):
    """Print the message as written, with a prefix only for problems."""

    PREFIXES = {
        logging.DEBUG: "Debug: ",
        logging.WARNING: "Warning: ",
        logging.ERROR: "Error: ",
        logging.CRITICAL: "Error: ",
    }

    def __init__(self) -> None:
        super().__init__("%(prefix)s%(message)s")

    def format(self, record: logging.LogRecord) -> str:
        record.prefix = self.PREFIXES.get(record.levelno, "")
        return super().format(record)


def setup_logger(
    name: str = PACKAGE_LOGGER,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Configure and return a logger.

    The console shows plain messages. A log file, if given, also records the
    time, level and logger name of every message.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(ConsoleFormatter())
        logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = PACKAGE_LOGGER) -> logging.Logger:
    """Get a logger under the package namespace so it shares the package handler."""
    if name != PACKAGE_LOGGER and not name.startswith(f"{PACKAGE_LOGGER}."):
        name = f"{PACKAGE_LOGGER}.{name}"
    return logging.getLogger(name)


__all__ = ["ConsoleFormatter", "get_logger", "setup_logger"]
