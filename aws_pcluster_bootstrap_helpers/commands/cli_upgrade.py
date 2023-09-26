import questionary
import requests
import os
import yaml
from pcluster import utils
from pcluster.api.controllers.cluster_operations_controller import (
    list_clusters,
    describe_cluster,
)
import tempfile

from pcluster.cli.commands.configure.easyconfig import (
    _get_vpcs_and_subnets,
)
from pcluster.utils import load_yaml_dict
from pcluster.schemas.cluster_schema import ClusterSchema
from aws_pcluster_bootstrap_helpers.utils.logging import setup_logger

PCLUSTER_VERSION = utils.get_installed_version()

logger = setup_logger("upgrade")


def upgrade(region="us-east-1"):
    """
    Upgrading a cluster keeps :
    1. Network settings
    2. Bootstrap settings
    3. Optional - queue settings
    """
    os.environ["AWS_DEFAULT_REGION"] = region
    clusters = list_clusters(region=region)
    complete_clusters = list(
        filter(lambda x: x.cluster_status == "CREATE_COMPLETE", clusters.clusters)
    )
    if not len(complete_clusters):
        logger.error(
            f"Unable to find any existing clusters. Please create a new cluster."
        )

    cluster_choices = list(map(lambda x: x.cluster_name, complete_clusters))
    cluster_name = questionary.select(
        "Please select a cluster.", choices=cluster_choices
    ).ask()

    cluster_info = describe_cluster(cluster_name, region=region)

    cluster_config = cluster_info.cluster_configuration.url
    cluster_yaml = requests.get(cluster_config).content.decode("utf-8")
    cluster_data = yaml.safe_load(cluster_yaml)
    network_data = _get_vpcs_and_subnets()
    cluster_config = ClusterSchema(cluster_name="clustername").load(cluster_data)
    head_node_subnet = cluster_config.head_node.networking.subnet_id
    compute_subnet_ids = list(
        map(lambda x: x.networking.subnet_ids, cluster_config.scheduling.queues)
    )
    compute_subnet_ids = [item for sublist in compute_subnet_ids for item in sublist]
    list_set = set(compute_subnet_ids)
    compute_subnet_ids = list(list_set)
    subnets = [head_node_subnet]
    for compute_subnet_id in compute_subnet_ids:
        subnets.append(compute_subnet_id)

    list_set = set(subnets)
    subnets = list(list_set)

    vpc_id = None
    for t_vpc_id in network_data["vpc_subnets"].keys():
        subnets = network_data["vpc_subnets"][t_vpc_id]
        for subnet in subnets:
            if subnet["id"] == head_node_subnet:
                vpc_id = t_vpc_id
                break

    # compute_node_subnets = list(
    #     map(cluster_data['Scheduling'])
    # )

    return
