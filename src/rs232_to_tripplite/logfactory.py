"""
Entry point for rs-232 to SNMP converter script

Author: Patrick Guo
Date: 2024-08-13
"""
import logging
import logging.config
import logging.handlers
import sys
from typing import Callable


class ReprFormatter(logging.Formatter):
    """
    Custom formatter to escape all characters to string representation
    """
    def format(self, record):
        record.msg = repr(record.msg)
        return super().format(record)


def get_file_handler(dest): # pylint: disable=missing-function-docstring
    return logging.FileHandler(dest)

def get_syslog_handler(dest): # pylint: disable=missing-function-docstring
    a = logging.handlers.SysLogHandler(facility=dest)
    return a

def get_stdstream_handler(dest): # pylint: disable=missing-function-docstring
    if dest == 'stdout':
        return logging.StreamHandler(sys.stdout)
    raise ValueError('Unsupported stream')

logging_types = {
    'file': get_file_handler,
    'syslog': get_syslog_handler,
    'stream': get_stdstream_handler
}

def setup_logging(destination_type, destination) -> None:
    """
    Setups initial loggers
    Args:
        destination_type: type of destination
        destination: name of destination

    Returns:

    """
    if destination_type not in logging_types:
        raise ValueError('Invalid destination type')

    repr_formatter = ReprFormatter(
        '%(asctime)s - %(name)s - %(levelname)s : '
        'At Line %(lineno)s of %(module)s :: %(message)s'
    )

    # get appropriate handler
    handler = logging_types[destination_type](destination)
    handler.setFormatter(repr_formatter)
    handler.setLevel(logging.INFO)

    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.INFO)

    ser2snmp_logger = logging.getLogger('rs232totripplite')
    ser2snmp_logger.setLevel(logging.INFO)
    ser2snmp_logger.addHandler(handler)


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
    logger = logging.getLogger(f'rs232totripplite.{name}')
    logger.setLevel(level)
    logger.propagate = propagation
    if log_filter:
        logger.addFilter(log_filter)
    return logger
