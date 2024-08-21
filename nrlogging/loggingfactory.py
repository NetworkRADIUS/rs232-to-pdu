import io
import json
import logging
import logging.handlers
import logging.config
import configparser
from typing import Callable
import pathlib


def setup_logging():
    config_file = pathlib.Path("nrlogging", "config.json")
    with open(config_file, "r", encoding='utf-8') as config_read:
        config = json.load(config_read)
    logging.config.dictConfig(config)


def add_handler_to_root_logger(handler: logging.FileHandler) -> None:
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)


def create_logger(
    name: str,
    level: int = logging.INFO,
    propagation: bool = True,
    log_filter: Callable = None,
) -> logging.Logger:
    logger = logging.getLogger(f'nwkrad.{name}')
    logger.setLevel(level)
    logger.propagate = propagation
    if log_filter:
        logger.addFilter(log_filter)
    return logger


def create_rotating_file_handler(
    file: str,
    log_format: str,
    max_bytes: 10485760,
    backup_count: int = 10,
    level: int = logging.INFO,
    log_filter: Callable = None,
) -> logging.handlers.RotatingFileHandler:
    file_handler = logging.handlers.RotatingFileHandler(
        file, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(log_format))
    if log_filter:
        file_handler.addFilter(log_filter)
    return file_handler


def create_console_handler(
    stream: io.TextIOWrapper,
    log_format: str,
    level: int = logging.INFO,
    log_filter: Callable = None,
) -> logging.StreamHandler:
    console_handler = logging.StreamHandler(stream)
    console_handler.setFormatter(logging.Formatter(log_format))
    console_handler.setLevel(level)
    if log_filter:
        console_handler.addFilter(log_filter)
    return console_handler
