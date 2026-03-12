"""
Centralized logger for GUNA-ASTRA.
Writes to console and to /logs directory.
"""

import logging
import os
from datetime import datetime

from config.settings import LOG_DIR, LOG_LEVEL


def setup_logger(name: str) -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(
        LOG_DIR, f"guna_astra_{datetime.now().strftime('%Y%m%d')}.log"
    )

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    if not logger.handlers:
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(AgentFormatter())

        # File handler
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(message)s"))

        logger.addHandler(ch)
        logger.addHandler(fh)

    return logger


class AgentFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        time = self.formatTime(record, "%H:%M:%S")
        return f"{color}[{time}] [{record.name}] {record.getMessage()}{self.RESET}"


def get_logger(name: str) -> logging.Logger:
    return setup_logger(name)
