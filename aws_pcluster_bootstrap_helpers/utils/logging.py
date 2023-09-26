import datetime
import logging
import os
from pathlib import Path
from typing import Union

import humanize
from colorlog import ColoredFormatter
from funcy.debug import LabeledContextDecorator, time_formatters, REPR_LEN

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


class log_durations(LabeledContextDecorator):
    """Times each function call or block execution."""

    def __init__(self, print_func, label, unit="auto", threshold=-1, repr_len=REPR_LEN):
        LabeledContextDecorator.__init__(
            self, print_func, label=label, repr_len=repr_len
        )
        if unit not in time_formatters:
            raise ValueError(
                "Unknown time unit: %s. It should be ns, mks, ms, s or auto." % unit
            )
        self.format_time = time_formatters[unit]
        self.threshold = threshold

    def __enter__(self):
        # self.start = timer()
        self.start = datetime.datetime.now()
        self.print_func(
            f"""\n####################################################
# Begin: {self.label}
####################################################\n
            """
        )
        return self

    def __exit__(self, *exc):
        duration = datetime.datetime.now() - self.start
        duration_str = humanize.precisedelta(duration, minimum_unit="seconds")
        self.print_func(
            f"""\n####################################################
# Complete: {self.label}
# Duration: {duration_str}
####################################################\n
            """
        )
