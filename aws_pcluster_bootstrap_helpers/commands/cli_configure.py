from pcluster.cli.commands.configure.easyconfig import _get_subnets, _get_vpcs_and_subnets, _create_vpc_parameters
import os

from prefect import flow, task
import re

import inquirer

from rich.prompt import Prompt
from rich.panel import Panel

from textual.app import App
from textual.reactive import Reactive
from textual.widget import Widget
from aws_pcluster_bootstrap_helpers.utils.logging import setup_logger

logger = setup_logger('configure')


def get_network_data(region: str = "us-east-1"):
    os.environ['AWS_DEFAULT_REGION'] = region
    network_data = _get_vpcs_and_subnets()
    return network_data


def configure(
    region: str = "us-east-1"
):
    network_data = get_network_data(region)
    vpcs = network_data['vpc_list']
    vpc_subnets = network_data['vpc_subnets']
    vpc_choices = list(map(lambda x: f"{x['id']} {x['name']}", vpcs))
    vpc_choices_options = list(
        map(lambda x: dict(label=f"{x['id']} {x['name']}", data=x), vpcs)
    )
    questions = [
        inquirer.List('vpc_id',
                      message="Choose a VPC",
                      choices=vpc_choices,
                      ),
    ]
    answers = inquirer.prompt(questions)
    vpc_choice = list(filter(lambda x: x['label'] == answers['vpc_id'], vpc_choices_options))[0]
    vpc_id = vpc_choice['data']['id']
    subnets = vpc_subnets[vpc_id]

    subnet_choices = list(map(lambda x: f"{x['id']} {x['name']}", subnets))
    subnet_choices_options = list(
        map(lambda x: dict(label=f"{x['id']} {x['name']}", data=x), subnets)
    )
    questions = [
        inquirer.List('head_subnet',
                      message="Choose a subnet for the head node",
                      choices=subnet_choices,
                      ),
        inquirer.List('compute_subnet',
                      message="Choose a subnet for the compute nodes",
                      choices=subnet_choices,
                      ),
    ]
    answers = inquirer.prompt(questions)
    head_subnet = list(filter(lambda x: x['label'] == answers['head_subnet'], subnet_choices_options))[0]
    compute_subnet = list(filter(lambda x: x['label'] == answers['compute_subnet'], subnet_choices_options))[0]
    head_subnet_id = head_subnet['data']['id']
    compute_subnet_id = compute_subnet['data']['id']

    subnet_ids = [head_subnet_id, compute_subnet_id]
    if head_subnet_id == compute_subnet_id:
        subnet_ids = [head_subnet_id]

    network_data = dict(
        vpc_id=vpc_id,
        subnet_ids=subnet_ids
    )
    print(network_data)
    return network_data
