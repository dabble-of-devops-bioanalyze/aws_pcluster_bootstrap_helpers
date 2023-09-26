"""Tasks for interacting with shell commands"""

import logging
import os
import sys
import tempfile
from typing import List, Optional, Union

import typing
import os
from pprint import pprint
from datetime import timedelta
from timeit import default_timer as timer

from pathlib import Path
import glob
import subprocess
import shutil
from subprocess import PIPE, STDOUT, Popen
import signal

from aws_pcluster_bootstrap_helpers.utils.logging import setup_logger, log_durations

logger = setup_logger("commands")


def run_bash_verbose(command: str, env=None) -> int:
    def pre_exec():
        # Restore default signal disposition and invoke setsid
        for sig in ("SIGPIPE", "SIGXFZ", "SIGXFSZ"):
            if hasattr(signal, sig):
                signal.signal(getattr(signal, sig), signal.SIG_DFL)
        os.setsid()

    output_encoding = "utf-8"
    if not env:
        env = os.environ.copy()

    logger.info(f'Launching subprocess "{command}"')

    sub = Popen(
        ["bash", "-c", command],
        stdout=PIPE,
        stderr=STDOUT,
        cwd=os.getcwd(),
        env=env,
        preexec_fn=pre_exec,
    )

    logger.info("Output:")
    for raw_line in iter(sub.stdout.readline, b""):
        line = raw_line.decode(output_encoding).rstrip()
        logger.info(line)

    sub.wait()
    logger.info("Command exited with return code %s", sub.returncode)
    return sub.returncode
