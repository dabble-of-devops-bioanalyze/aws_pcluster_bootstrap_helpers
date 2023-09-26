import os
import boto3

import questionary
from pcluster.cli.commands.configure.easyconfig import (
    _create_vpc_parameters,
    _choose_network_configuration,
    _get_common_supported_az_for_multi_instance_types,
)
from pcluster.cli.commands.configure.easyconfig import (
    _get_vpcs_and_subnets,
)
from pcluster.constants import (
    DEFAULT_MAX_COUNT,
    DEFAULT_MIN_COUNT,
    MAX_COMPUTE_RESOURCES_PER_QUEUE,
    MAX_NUMBER_OF_COMPUTE_RESOURCES_PER_CLUSTER,
    MAX_NUMBER_OF_QUEUES,
    SUPPORTED_SCHEDULERS,
)
from pcluster.utils import error, get_supported_os_for_scheduler
from pcluster.validators.cluster_validators import NameValidator
from pcluster.aws.aws_api import AWSApi
from pcluster.aws.common import get_region
from pcluster.cli.commands.configure.networking import (
    NetworkConfiguration,
    PublicPrivateNetworkConfig,
    automate_subnet_creation,
    automate_vpc_with_subnet_creation,
)
from questionary import Separator

from aws_pcluster_bootstrap_helpers.utils.logging import setup_logger

# TODO I think there is a bug in the constants
MAX_NUMBER_OF_COMPUTE_RESOURCES_PER_CLUSTER = 50
MAX_NUMBER_OF_QUEUES = 10
MAX_NUMBER_OF_COMPUTE_RESOURCES_PER_QUEUE = 5

logger = setup_logger("configure")
logger.propagate = False


def create_subnets():
    scheduler = "slurm"
    head_node_instance_type = "t3a.2xlarge"
    cluster_size = MAX_NUMBER_OF_COMPUTE_RESOURCES_PER_CLUSTER
    compute_instance_types = []
    network_configuration = PublicPrivateNetworkConfig()
    azs_for_head_node_type = AWSApi.instance().ec2.get_supported_az_for_instance_type(
        head_node_instance_type
    )
    azs_for_compute_types = _get_common_supported_az_for_multi_instance_types(
        compute_instance_types
    )
    common_availability_zones = set(azs_for_head_node_type) & set(azs_for_compute_types)
    vpc_parameters = _create_vpc_parameters(
        scheduler, head_node_instance_type, compute_instance_types, cluster_size
    )


def get_network_data(region: str = "us-east-1"):
    os.environ["AWS_DEFAULT_REGION"] = region
    network_data = _get_vpcs_and_subnets()
    return network_data
