import os
import boto3

import questionary
from pcluster.cli.commands.configure.easyconfig import (
    _get_vpcs_and_subnets,
)
from questionary import Separator

from aws_pcluster_bootstrap_helpers.utils.logging import setup_logger

logger = setup_logger("configure")


def get_network_data(region: str = "us-east-1"):
    os.environ["AWS_DEFAULT_REGION"] = region
    network_data = _get_vpcs_and_subnets()
    return network_data


def configure_storage(region: str = "us-east-1"):
    os.environ['AWS_DEFAULT_REGION'] = region
    create_apps = questionary.confirm("Create new storage for /apps?").ask()
    create_scratch = questionary.confirm("Create new storage for /scratch?").ask()

    if create_apps and create_scratch:
        return dict(create_apps=True, create_scratch=True)

    apps_search = questionary.text(
        """Please enter a search pattern for existing apps EFS systems.
        None will list all EFS file systems."""
    ).ask()
    client = boto3.client('efs')
    efs_response = client.describe_file_systems()
    efs = efs_response['FileSystems']
    all_efs = efs
    next_marker = efs_response.get('NextMarket', None)
    while next_marker:
        efs_response = client.describe_file_systems(Marker=next_marker)
        next_marker = efs_response.get('NextMarket', None)
        efs = efs_response['FileSystems']
        map(lambda x: all_efs.append(x), efs)

    return


def configure(region: str = "us-east-1"):
    network_data = get_network_data(region)
    vpcs = network_data["vpc_list"]
    vpc_subnets = network_data["vpc_subnets"]
    vpc_choices = list(map(lambda x: f"{x['id']} {x['name']}", vpcs))
    vpc_choices_options = list(
        map(lambda x: dict(label=f"{x['id']} {x['name']}", data=x), vpcs)
    )
    vpc_name = questionary.select("Which VPC?", choices=vpc_choices).ask()
    vpc_choice = list(filter(lambda x: x["label"] == vpc_name, vpc_choices_options))[0]
    vpc_id = vpc_choice["data"]["id"]
    subnets = vpc_subnets[vpc_id]

    subnet_choices = list(map(lambda x: f"{x['id']} {x['name']}", subnets))
    subnet_choices_options = list(
        map(lambda x: dict(label=f"{x['id']} {x['name']}", data=x), subnets)
    )
    head_subnet = questionary.select(
        "Choose a subnet for the head node", choices=subnet_choices
    ).ask()
    compute_subnet = questionary.select(
        "Choose a subnet for the compute node", choices=subnet_choices
    ).ask()
    head_subnet = list(
        filter(lambda x: x["label"] == head_subnet, subnet_choices_options)
    )[0]
    compute_subnet = list(
        filter(lambda x: x["label"] == compute_subnet, subnet_choices_options)
    )[0]
    head_subnet_id = head_subnet["data"]["id"]
    compute_subnet_id = compute_subnet["data"]["id"]

    subnet_ids = [head_subnet_id, compute_subnet_id]
    if head_subnet_id == compute_subnet_id:
        subnet_ids = [head_subnet_id]

    selected_network_data = dict(vpc_id=vpc_id, subnet_ids=subnet_ids)
    return selected_network_data
