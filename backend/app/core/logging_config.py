"""
Logging Configuration Module

Centralized logging setup for Pravda Market backend
"""

import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """
    Configure application-wide logging

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON format for production log aggregation

    Example:
        setup_logging(level="DEBUG", json_format=False)
    """
    # Create logger
    logger = logging.getLogger("pravda_market")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    # Create formatter
    if json_format:
        # JSON formatter for production (log aggregation)
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "function": "%(funcName)s", "message": "%(message)s"}',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Human-readable formatter for development
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(module)s:%(funcName)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False


def get_logger(name: str = "pravda_market") -> logging.Logger:
    """
    Get configured logger instance

    Args:
        name: Logger name (default: "pravda_market")

    Returns:
        logging.Logger: Configured logger

    Example:
        logger = get_logger()
        logger.info("Application started")
    """
    return logging.getLogger(name)
