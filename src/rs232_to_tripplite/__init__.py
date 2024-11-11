"""
This file contains the initialization process for the project.
"""

import logging
import sys


class ReprFormatter(logging.Formatter):
    """
    Custom formatter to escape all characters to string representation
    """

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
    repr_formatter = ReprFormatter(
        '%(asctime)s - %(name)s - %(levelname)s : At Line %(lineno)s of '
        '%(module)s :: %(message)s')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(repr_formatter)
    stdout_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.INFO)

    project_logger = logging.getLogger(__name__)
    project_logger.setLevel(logging.INFO)
    project_logger.addHandler(stdout_handler)


setup_logging()
