import logging
from pathlib import Path
from typing import Union

import os
from colorlog import ColoredFormatter

seperator = "----------------------------------------------------\n"

levels = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


def setup_logger(
    logger_name: str = "[pcluster helpers]",
    log_level: str = os.environ.get("LOG_LEVEL", "INFO"),
    **kwargs,
) -> logging.getLogger:
    """
    _summary_

    Parameters
    ----------
    log_file : Union[str, Path]
        _description_
    log_level : str, optional
        _description_, by default "INFO"
    logger_name : str, optional
        _description_, by default "[Slide-seq Flowcell Alignment Workflow]"

    Returns
    -------
    logging.getLogger
        _description_
    """
    colored_log_format = "%(asctime)s%(reset)s | %(name)s%(reset)s | %(filename)s:%(lineno)d%(reset)s | %(log_color)s%(levelname)-8s%(reset)s | %(message)s"
    file_log_format = "%(asctime)s | %(name)s | %(filename)s:%(lineno)d | %(levelname)-8s | %(message)s"

    color_formatter = ColoredFormatter(
        colored_log_format,
        datefmt=None,
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red",
        },
    )

    logger = logging.getLogger(logger_name)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(color_formatter)

    logger.addHandler(stream_handler)
    logger.setLevel(log_level)

    return logger
