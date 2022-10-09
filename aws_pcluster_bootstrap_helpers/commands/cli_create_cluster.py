import os
import pathlib
from prefect import flow, task
from prefect_shell import shell_run_command
import time
import tempfile
import json

from aws_pcluster_bootstrap_helpers.utils.logging import setup_logger

from pcluster import utils

PCLUSTER_VERSION = utils.get_installed_version()

logger = setup_logger("create-cluster")

CREATE_IN_PROGRESS = "CREATE_IN_PROGRESS"
CREATE_FAILED = "CREATE_FAILED"
CREATE_COMPLETE = "CREATE_COMPLETE"
DELETE_IN_PROGRESS = "DELETE_IN_PROGRESS"
DELETE_FAILED = "DELETE_FAILED"
DELETE_COMPLETE = "DELETE_COMPLETE"


def parse_json_status(content, file):
    f = open(file)
    try:
        data = json.load(f)
    except Exception as e:
        logger.warn(f"Error reading in pcluster create file: {file}: {e}")
        raise Exception(e)

    del data["imageConfiguration"]["url"]
    cluster_status = data["clusterStatus"]
    logger.info(f"Pcluster create status: {cluster_status}")
    if "FAILED" in cluster_status:
        raise Exception(f"Cluster create failed: {cluster_status}")
    elif cluster_status == "CREATE_IN_PROGRESS":
        return True
    elif "PROGRESS" in cluster_status:
        return True
    elif "COMPLETE" not in cluster_status and "FAIL" not in cluster_status:
        return True
    elif cluster_status == "CREATE_COMPLETE":
        return False
    else:
        raise Exception(f"Cluster status not compatible with bootstrap: {cluster_status}")


def watch_create_cluster(cluster_name: str, region="us-east-1"):
    create_in_process = True
    n = 1
    while create_in_process:
        with tempfile.NamedTemporaryFile(suffix=".json") as tmpfile:
            logger.info(
                f"Pcluster: {cluster_name}, Region: {region}, N: {1} Data file: {tmpfile.name}"
            )
            contents = shell_run_command(
                command=f"""pcluster \\
                describe-cluster \\
                -n {cluster_name} \\
                -r {region} > {tmpfile.name}""",
                return_all=True,
            )
            create_in_process = parse_json_status(contents, tmpfile.name)
        n = n + 1
        # sleep for 10 minutes
        if create_in_process:
            time.sleep(600)
    return create_in_process


def describe_cluster(cluster_name: str, output_file: str, region="us-east-1"):
    contents = shell_run_command(
        command=f"""pcluster \\
        describe-cluster \\
        -n {cluster_name} \\
        --region {region} > {output_file}""",
        return_all=True,
    )
    create_in_process = parse_json_status(contents, output_file)
    return create_in_process


def create_cluster(cluster_name: str, region: str, config_file: str):
    shell_run_command(
        command=f"""pcluster create-cluster \\
  --rollback-on-failure false \\
  -n {cluster_name} \\
  -r {region} \\
  -c {config_file}
""",
        return_all=True,
    )
    return


@flow
def watch_cluster_create_flow(
    cluster_name: str, config_file: pathlib.Path, region: str = "us-east-1",
):
    create_cluster(cluster_name=cluster_name, region=region, config_file=str(config_file))
    watch_create_cluster(cluster_name=cluster_name, region=region)
    return True


@flow
def create_cluster_flow(
    cluster_name: str,
    config_file: pathlib.Path,
    region: str = "us-east-1",
    pcluster_version: str = "3.2",
):
    if pcluster_version not in PCLUSTER_VERSION:
        w = f"""Mismatch between specified pcluster version and installed
        Specified: {pcluster_version}, Installed: {PCLUSTER_VERSION}
        """
        raise ValueError(w)
    create_cluster(cluster_name=cluster_name, region=region, config_file=str(config_file))
    return True
