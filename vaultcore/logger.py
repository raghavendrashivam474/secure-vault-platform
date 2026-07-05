"""
vaultcore/logger.py

Shared logging service for the Secure Vault Platform.
All platform and module events should be recorded here.
"""

import logging
from pathlib import Path
from datetime import datetime


LOG_DIR:  Path = Path("logs")
LOG_FILE: Path = LOG_DIR / "platform.log"


def initialize_logger() -> logging.Logger:
    """
    Initialize and return the platform logger.

    Creates the log directory if it does not exist.
    Writes to both file and console.

    Returns:
        A configured Logger instance.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("SecureVaultPlatform")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s  [%(levelname)s]  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "[%(levelname)s]  %(message)s"
    ))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Global logger instance
logger = initialize_logger()


def log_info(message: str) -> None:
    """Log an informational message."""
    logger.info(message)


def log_warning(message: str) -> None:
    """Log a warning message."""
    logger.warning(message)


def log_error(message: str) -> None:
    """Log an error message."""
    logger.error(message)


def log_debug(message: str) -> None:
    """Log a debug message."""
    logger.debug(message)


def log_event(event: str, detail: str = "") -> None:
    """
    Log a named platform event.

    Args:
        event:  The event name.
        detail: Optional additional detail.
    """
    message = f"EVENT: {event}"
    if detail:
        message += f" - {detail}"
    logger.info(message)



