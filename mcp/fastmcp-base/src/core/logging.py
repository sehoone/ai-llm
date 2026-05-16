import logging
import sys


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        try:
            from src.core.config import get_settings
            level = getattr(logging, get_settings().log_level.upper(), logging.INFO)
        except Exception:
            level = logging.INFO
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger
