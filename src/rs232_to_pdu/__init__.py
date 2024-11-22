"""
rs232-to-pdu
Copyright (C) 2024 InkBridge Networks (legal@inkbridge.io)

rs232-to-pdu © 2024 by InkBridge is licensed under CC BY-NC 4.0. To view a copy
of this license, visit https://creativecommons.org/licenses/by-nc/4.0/

This file contains the initialization process for the project.
"""

import logging
import logging.handlers
import os
import pathlib
import sys

import yaml


class ReprFormatter(logging.Formatter):
    """
    Custom formatter to escape all characters to string representation
    """

    def format(self, record):
        record.msg = repr(record.msg)
        return super().format(record)


def handler_file(dest):  # pylint: disable=missing-function-docstring
    return logging.FileHandler(dest)


def handler_syslog(dest):  # pylint: disable=missing-function-docstring
    return logging.handlers.SysLogHandler(facility=dest['facility'])


def handler_stream(dest):  # pylint: disable=missing-function-docstring
    if dest == 'stdout':
        return logging.StreamHandler(sys.stdout)
    raise ValueError('Unsupported stream')


logging_types = {
    'file': handler_file,
    'syslog': handler_syslog,
    'stream': handler_stream
}


def setup_logging(destination_type, destination) -> None:
    """
    Sets up some default loggers and configs

    Expected to be run at start of application

    Args:
        None

    Returns:
        None
    """
    if destination_type not in logging_types:
        raise ValueError('Invalid destination type')

    repr_formatter = ReprFormatter(
        '%(asctime)s - %(name)s - %(levelname)s : At Line %(lineno)s of '
        '%(module)s :: %(message)s')

    # get appropriate handler
    handler = logging_types[destination_type](destination)
    handler.setFormatter(repr_formatter)
    handler.setLevel(logging.INFO)

    root_logger = logging.getLogger('')
    root_logger.setLevel(logging.INFO)

    project_logger = logging.getLogger(__name__)
    project_logger.setLevel(logging.INFO)
    project_logger.addHandler(handler)


CONFIG_FILE = pathlib.Path('etc', 'rs232-to-pdu', 'config.yaml')
with open(CONFIG_FILE, 'r', encoding='utf-8') as fileopen:
    config = yaml.load(fileopen, Loader=yaml.FullLoader)

if 'log' in config:
    if len(tuple(config['log'].keys())) > 1:
        raise ValueError('Only one log destination can be configured'
                         'simultaneously')

    for i, key in enumerate(config['log']):
        setup_logging(key, config['log'][key])
else:
    # default to stdout
    setup_logging('stream', 'stdout')
