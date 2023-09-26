import os
from copy import deepcopy
import boto3
from typing import Dict, Any, List, Optional
import pathlib
import time
import tempfile
import json
from pcluster.api.controllers.image_operations_controller import describe_image
from pcluster.api.models import DescribeImageResponseContent

from mypy_boto3_logs.client import CloudWatchLogsClient
from aws_pcluster_bootstrap_helpers.utils.logging import setup_logger
from aws_pcluster_bootstrap_helpers.utils.commands import run_bash_verbose

# todo change prefect to ansible
# from prefect import flow, task
# from prefect_shell import shell_run_command

from pcluster import utils

PCLUSTER_VERSION = utils.get_installed_version()

logger = setup_logger("build-ami")

BUILD_IN_PROGRESS = "BUILD_IN_PROGRESS"
BUILD_FAILED = "BUILD_FAILED"
BUILD_COMPLETE = "BUILD_COMPLETE"
DELETE_IN_PROGRESS = "DELETE_IN_PROGRESS"
DELETE_FAILED = "DELETE_FAILED"
DELETE_COMPLETE = "DELETE_COMPLETE"


def parse_image_status(data: DescribeImageResponseContent):
    image_status = data.image_build_status
    logger.info(f"Pcluster build status: {image_status}")
    if image_status == "BUILD_FAILED":
        raise Exception(f"Image build failed: {image_status}")
    elif "FAILED" in image_status:
        raise Exception(f"Image build failed: {image_status}")
    elif image_status == "BUILD_IN_PROGRESS":
        return True
    elif "PROGRESS" in image_status:
        return True
    elif "COMPLETE" not in image_status and "FAIL" not in image_status:
        return True
    elif "COMPLETE" in image_status:
        return False
    elif image_status == "BUILD_COMPLETE":
        return False
    else:
        raise Exception(f"Image status not compatible with bootstrap: {image_status}")


def build_ami_logs(
    data: DescribeImageResponseContent,
    log_client: CloudWatchLogsClient,
    start_time: int = 0,
):
    """

    'imageBuildLogsArn': 'arn:aws:logs:us-east-1:018835827632:log-group:/aws/imagebuilder/ParallelClusterImage-pcluster-3-2-1-wnl8bh-20221019'
    Parameters
    ----------
    data
    log_client
    start_time

    Returns
    -------

    """
    log_stream_name = data.image_build_logs_arn
    if not log_stream_name:
        return 0
    log_stream_name = log_stream_name.split(":").pop()
    log_group = deepcopy(log_stream_name)
    log_group = log_group.split("/")
    log_group.pop()
    log_group = list(filter(lambda x: x, log_group))
    log_group = "/".join(log_group)
    log_stream_name = log_stream_name.split("/").pop()
    start_time = print_logs(
        client=log_client,
        log_stream_name=log_stream_name,
        log_group=log_group,
        start_time=start_time,
    )
    return start_time


def build_in_progress(image_id: str, region="us-east-1"):
    os.environ["AWS_DEFAULT_REGION"] = region
    client = boto3.client("logs")
    start_time = 0

    build_in_process = True
    n = 1
    while build_in_process:
        logger.info(f"Pcluster: {image_id}, Region: {region}, N: {n}")
        build_data = describe_image(image_id=image_id, region=region)
        logger.info(build_data)
        try:
            start_time = build_ami_logs(
                data=build_data, log_client=client, start_time=start_time
            )
        except Exception as e:
            # logs only exist for a certain time
            # if they go away just skip this
            pass
        build_in_process = parse_image_status(build_data)
        print(
            f"Image Build:[{image_id} - {region}] Build in process: {build_in_process}"
        )

        n = n + 1
        # sleep for 10 minutes
        if build_in_process:
            time.sleep(600)
    return


def build_complete(image_id: str, output_file: str, region="us-east-1"):
    try:
        shell_run_command(
            command=f"""pcluster describe-image \\
      --image-id {image_id} \\
      -r {region} > {output_file} \\
    """,
            return_all=True,
        )
    except Exception as e:
        return
    return


def start_build(image_id: str, region: str, config_file: str):
    try:
        run_bash_verbose(
            command=f"""pcluster build-image --image-id {image_id} -r {region} -c {config_file} """,
        )
    except Exception as e:
        return
    return


def build_ami_flow(
    image_id: str,
    output_file: pathlib.Path,
    config_file: pathlib.Path,
    region: str = "us-east-1",
    pcluster_version: str = "3.5.0",
):
    if pcluster_version not in PCLUSTER_VERSION:
        w = f"""Mismatch between specified pcluster version and installed
        Specified: {pcluster_version}, Installed: {PCLUSTER_VERSION}
        """
        raise ValueError(w)
    start_build(image_id, region, str(config_file))
    return True


def watch_ami_build_flow(
    image_id: str,
    output_file: pathlib.Path,
    config_file: pathlib.Path,
    region: str = "us-east-1",
) -> True:
    output_file = str(output_file)
    config_file = str(config_file)
    logger.info(f"Building ami: {image_id} {region}")
    start_build(
        image_id=image_id,
        region=region,
        config_file=config_file,
    )
    logger.info(f"Babysitting ami build: {image_id} {region}")
    build_in_progress(image_id=image_id, region=region)
    logger.info(f"Build complete!: {image_id} {region}")
    build_complete(image_id=image_id, region=region, output_file=output_file)
    logger.info(f"Build complete and data written to : {output_file}")
    return True


def watch_ami_flow(image_id: str, output_file: pathlib.Path, region: str = "us-east-1") -> bool:
    build_in_progress(image_id=image_id, region=region)
    build_complete(image_id=image_id, region=region, output_file=output_file)
    return True


def main(image_id: str, output_file: pathlib.Path, region: str = "us-east-1"):
    output_file = str(output_file)
    flow_state = watch_ami_build_flow(
        image_id=image_id, region=region, output_file=output_file
    )
    return flow_state
