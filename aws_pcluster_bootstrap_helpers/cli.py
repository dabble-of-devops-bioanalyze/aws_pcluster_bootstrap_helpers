"""Console script for aws_pcluster_bootstrap_helpers."""
import os

import pathlib
import typer
from aws_pcluster_bootstrap_helpers.commands import cli_build_ami, cli_instance_types

cli = typer.Typer()


# watch_ami_typer = typer.Typer()
# build_ami_typer = typer.Typer()


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


@cli.command("instance-types")
def cli_get_instance_types(
    region: str = typer.Option(
        os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    ),
):
    cli_instance_types.get_instance_types(region=region)


if __name__ == "__main__":
    cli()
