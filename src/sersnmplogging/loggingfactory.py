"""
Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""
import json
import logging
import logging.handlers
import logging.config
from typing import Callable
import pathlib


def setup_logging() -> None:
    """
    Sets up some default loggers and configs

    Expected to be run at start of application

    Args:
        None

    Returns:
        None
    """
    config_file = pathlib.Path("sersnmplogging", "config.json")
    with open(config_file, "r", encoding='utf-8') as config_read:
        config = json.load(config_read)

    # Loads config using json (dictionary) object
    logging.config.dictConfig(config)

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
