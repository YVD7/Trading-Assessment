"""
Centralized logging configuration.

Two handlers are attached to the root "trading_bot" logger:
  - a rotating file handler (detailed, includes DEBUG-level API request/response
    payloads) writing to logs/trading_bot.log
  - a console handler (INFO and above) so the user gets clean, readable
    output in the terminal without wading through raw JSON payloads.

The file handler is intentionally verbose (it is the audit trail requested in
the task: "logging of API requests, responses, and errors to a log file"),
while the console stays terse so normal usage isn't noisy.
"""

import logging
import logging.handlers
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(verbose_console: bool = False) -> logging.Logger:
    """
    Configure and return the application logger.

    Args:
        verbose_console: if True, DEBUG-level messages are also printed to
            the console (useful for troubleshooting). Default is False so
            normal runs only show INFO+ on screen.

    Returns:
        The configured "trading_bot" logger instance.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if setup_logging() is called more than once
    # (e.g. in tests or interactive sessions).
    if logger.handlers:
        return logger

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Rotating file handler: keeps the log directory from growing unbounded
    # while retaining a useful amount of history (5 x 2MB files).
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose_console else logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
