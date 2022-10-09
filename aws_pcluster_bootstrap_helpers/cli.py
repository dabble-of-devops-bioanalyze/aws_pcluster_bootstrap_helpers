"""Console script for aws_pcluster_bootstrap_helpers."""
import os

import json
from pcluster.cli.commands.configure.easyconfig import _get_subnets, _get_vpcs_and_subnets, _create_vpc_parameters
from pcluster.cli.commands.configure.utils import (
    get_regions,
)
import pathlib
import typer
import datetime
from pcluster.constants import (
    DEFAULT_MAX_COUNT,
    DEFAULT_MIN_COUNT,
    MAX_NUMBER_OF_COMPUTE_RESOURCES,
    MAX_NUMBER_OF_QUEUES,
    SUPPORTED_SCHEDULERS,
)
from aws_pcluster_bootstrap_helpers.commands import (
    cli_build_ami,
    cli_instance_types,
    cli_create_cluster,
    cli_configure
)
from aws_pcluster_bootstrap_helpers.utils.logging import setup_logger

logger = setup_logger('cli')

cli = typer.Typer()


def region_ctx(region):
    os.environ['AWS_DEFAULT_REGION'] = region


@cli.command("watch-ami")
def watch_ami_build_cli(
    output: pathlib.Path = typer.Option(
        ...,
        help="Path to output of pcluster describe-image",
    ),
    region: str = typer.Option(
        os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    ),
    image_id: str = typer.Option(..., help="""Image ID for build"""),
):
    """
    Watcher for PCluster image builder.
    Given an image_id and region it will wait for the image to build and report back.
    """
    cli_build_ami.watch_ami_build_flow(
        image_id=image_id, output_file=output, region=region
    )


@cli.command("build-and-watch-ami")
def build_and_watch_ami_cli(
    pcluster_version: str = typer.Option(
        "3.2", help="PCluster version used to build the image"
    ),
    output: pathlib.Path = typer.Option(
        ...,
        help="Path to output of pcluster describe-image",
    ),
    config_file: pathlib.Path = typer.Option(
        ..., help="Path to build config for the pcluster ami"
    ),
    region: str = typer.Option(
        os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    ),
    image_id: str = typer.Option(..., help="""Image ID for build"""),
):
    """
    Start to build a pcluster AMI and wait for the build to complete
    """
    cli_build_ami.build_ami_flow(
        image_id=image_id,
        output_file=output,
        region=region,
        config_file=config_file,
        pcluster_version=pcluster_version,
    )


@cli.command('create-and-watch-cluster')
def create_and_watch_cluster(
    pcluster_version: str = typer.Option(
        "3.2", help="PCluster version used to build the image"
    ),
    config_file: pathlib.Path = typer.Option(..., help="Path to pcluster configure file."),
    region: str = typer.Option(
        os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    ),
    cluster_name: str = typer.Option(..., help="""Cluster name"""),
):
    """
    Run:
        `pcluster create-cluster -n cluster_name -r region`.
    Then wait for the cluster to complete.
    """
    cli_create_cluster.watch_cluster_create_flow(
        region=region,
        confile_file=config_file,
        cluster_name=cluster_name,
        pcluster_version=pcluster_version,
    )
    return


@cli.command("instance-types")
def get_instance_types(
    region: str = typer.Option(
        os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    ),
):
    """
    Get all available instance types for your region and write them to a dataframe
    """
    dfs = cli_instance_types.get_instance_types(region=region)
    cli_instance_types.write_instance_types_csvs(gpu_df=dfs['gpu_df'], cpu_df=dfs['cpu_df'])


@cli.command('configure')
def configure(
    region: str = typer.Option('us-east-1', prompt=True),
    name: str = typer.Option("slurm", prompt=False),
    namespace: str = typer.Option(..., prompt=True, help="Typically the company name. Example: my_company"),
    environment: str = typer.Option("hpc", prompt=False, help="Type of deployment. HPC, Kubernetes, etc."),
    stage: str = typer.Option("dev", prompt=False, help="Development env. Example: dev, test, stage, prod."),
    force: bool = typer.Option(True, help="Force overwrite of existing config file.")
):
    """
    Generate the json file used for the rest of the bootstrap
    """
    id = f"{namespace}-{environment}-{stage}-{name}"
    json_file = f"{id}.json"
    os.environ['AWS_DEFAULT_REGION'] = region
    network_data = cli_configure.configure(region=region)
    configure_data = {
        "namespace": namespace,
        "environment": environment,
        "stage": stage,
        "name": name,
        "region": region,
        "terraform_vars": network_data
    }
    logger.info(f"Writing file to : {json_file}")
    logger.info(configure_data)
    with open(json_file, 'w') as fh:
        json.dump(configure_data, fh)
    return


if __name__ == "__main__":
    cli()
