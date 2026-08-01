"""
Production Logging utility for InfraMind AI Windows Agent
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from agent.config.settings import get_settings, AgentSettings


def get_logger(name: str, settings: AgentSettings = get_settings) -> logging.Logger:
    """
    Returns a configured production logger instance with stdout and
    RotatingFileHandler outputs.
    
    :param name: Module logger name.
    :param settings: AgentSettings configuration.
    :return: logging.Logger instance.
    """
    logger = logging.getLogger(name)
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(log_level)

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")

        # Console Stream Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Rotating File Handler
        try:
            log_path = settings.absolute_log_file_path
            file_handler = RotatingFileHandler(
                filename=str(log_path),
                maxBytes=settings.max_log_bytes,
                backupCount=settings.backup_count,
                encoding="utf-8"
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not attach RotatingFileHandler to {settings.log_file_path}: {e}")

    return logger
