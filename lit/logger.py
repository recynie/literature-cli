"""CLI logger adapter for services that expect a Textual-style app object."""

from __future__ import annotations

import logging


class CliLogger:
    """Minimal app-compatible logger used by the service layer."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    def _add_log(self, key: str, message: str):
        logging.debug("[%s] %s", key, message)

    def notify(self, message: str, severity: str = "information"):
        if severity == "error":
            logging.error(message)
        elif severity == "warning":
            logging.warning(message)
        else:
            logging.info(message)

