"""
Logging configuration for Postal Warmup Application
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(app=None, name='postal_warmup', log_level=None, log_file=None):
    """
    Configure application logging

    Args:
        app: Flask app instance (optional)
        name: Logger name
        log_level: Logging level (default from config or INFO)
        log_file: Log file path (default from config or ./logs/warmup.log)

    Returns:
        logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    # Get configuration from app if available
    if app:
        log_level = log_level or app.config.get('LOG_LEVEL', 'INFO')
        log_file = log_file or app.config.get('LOG_FILE', './logs/warmup.log')
    else:
        log_level = log_level or os.getenv('LOG_LEVEL', 'INFO')
        log_file = log_file or os.getenv('LOG_FILE', './logs/warmup.log')

    # Set log level
    log_level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    logger.setLevel(log_level_map.get(log_level.upper(), logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (with rotation)
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    logger.info(f"Logger initialized: {name} (Level: {log_level})")

    return logger


def get_logger(name='postal_warmup'):
    """Get logger instance"""
    return logging.getLogger(name)
