"""
Logger Setup
Configures logging to both console and file with colors.
"""

import logging
import sys
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname:8}{self.RESET}"
        return super().format(record)


def setup_logger(name: str) -> logging.Logger:
    """Set up a logger with console + file handlers."""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Ensure sys.stdout uses utf-8 to prevent emoji crash on Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        ColoredFormatter(
            fmt="%(asctime)s  %(levelname)s  %(name)s — %(message)s",
            datefmt="%H:%M:%S"
        )
    )

    # File handler (no colors)
    file_handler = logging.FileHandler(log_dir / "automation.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    )

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger
