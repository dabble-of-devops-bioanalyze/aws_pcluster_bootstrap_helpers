import pydantic
from typing import Optional, List, Any
from enum import Enum

from enum import Enum, IntEnum
from pydantic import BaseModel, ValidationError
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
    MAX_NUMBER_OF_COMPUTE_RESOURCES,
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

logger = setup_logger("configure")


class NetworkConfig(BaseModel):
    vpc_id: str
    subnet_ids: List[str]


class TargetGroupType(str, Enum):
    ip = "ip"
    instance = "instance"


class EFSConfig(BaseModel):
    create_efs: bool = True
    efs_id: Optional[str]
    efs_mount_path: str


class EFSMountConfig(BaseModel):
    efs: List[EFSConfig]


class DNSConfig(BaseModel):
    zone_id: str
    acm_id: str
    target_group_type: Enum
    head_node_elastic_ip: bool = True
    internal_lb: bool = False


class TagsConfig(BaseModel):
    name: str
    namespace: str
    environment: str = "hpc"
    stage: str = "dev"


class PClusterConfigure(BaseModel):
    region: str
