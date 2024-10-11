"""
Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""
import logging
import logging.handlers
import logging.config
from typing import Callable
import sys

class ReprFormatter(logging.Formatter):
    def format(self, record):
        record.msg = repr(record.msg)
        return super().format(record)


def setup_logging() -> None:
    """
    Sets up some default loggers and configs

    Expected to be run at start of application

    Args:
        None

    Returns:
        None
    """
    repr_formatter = ReprFormatter('%(message)s')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(repr_formatter)
    stdout_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.INFO)

    ser2snmp_logger = logging.getLogger('ser2snmp')
    ser2snmp_logger.setLevel(logging.INFO)
    ser2snmp_logger.addHandler(stdout_handler)

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
    logger = logging.getLogger(f'ser2snmp.{name}')
    logger.setLevel(level)
    logger.propagate = propagation
    if log_filter:
        logger.addFilter(log_filter)
    return logger
