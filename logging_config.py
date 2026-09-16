"""
G1Saathi — Logging Configuration
Call setup_logging() once at application startup.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_dir: Path | None = None) -> None:
    """
    Configure root logger with console + rotating file handlers.
    Safe to call multiple times — clears duplicate handlers first.

    Args:
        log_level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
        log_dir:   Directory for log files. Pass None to skip file logging.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()

    # Console
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(numeric_level)
    console.setFormatter(fmt)
    root.addHandler(console)

    # Rotating file
    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            log_dir / "g1saathi.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        fh.setLevel(numeric_level)
        fh.setFormatter(fmt)
        root.addHandler(fh)

    # Quieten noisy third-party libraries
    for lib in ("httpcore", "httpx", "urllib3", "chromadb", "sentence_transformers",
                "langchain", "openai", "ollama"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    logging.getLogger(__name__).info("Logging initialised — level=%s", log_level)
