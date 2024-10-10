"""
Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""
import logging
import logging.handlers
import logging.config
from typing import Callable

default_setup = {
    "version": 1,
    "formatters": {
        "stdout": {
            "format": "%(message)s"
        }
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "stdout",
            "stream": "ext://sys.stdout"
        },
    },
    "loggers": {
        "": {
            "level": "DEBUG",
            "handlers": []
        },
        "nwkrad": {
            "level": "DEBUG",
            "handlers": ["stdout"]
        }
    },
    "disable_existing_loggers": False
}

def setup_logging() -> None:
    """
    Sets up some default loggers and configs

    Expected to be run at start of application

    Args:
        None

    Returns:
        None
    """

    # Loads config using (dictionary object
    logging.config.dictConfig(default_setup)

def create_logger(
    name: str,
    level: int = logging.INFO,
    propagation: bool = True,
    log_filter: Callable = None,
) -> logging.Logger:
    """
    Creates a simpel logger

    Args:
        name (str): name of new logger - should be <package>.<module>
        level (int): level of logger
        propagation (bool): whether or not the logger should send log records
                            to its parent
        log_filter (Callable): a function used to filter out messages
    
    Returns:
        the newly create logger object
    """
    logger = logging.getLogger(f'nwkrad.{name}')
    logger.setLevel(level)
    logger.propagate = propagation
    if log_filter:
        logger.addFilter(log_filter)
    return logger
