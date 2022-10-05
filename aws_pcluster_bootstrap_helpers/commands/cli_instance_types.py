import os
import numpy as np
from typing import List, Any, Dict, Optional

from pcluster.aws.aws_api import AWSApi
import pandas as pd
from aws_pcluster_bootstrap_helpers.utils.logging import setup_logger

from pcluster import utils
from pcluster.constants import MAX_NUMBER_OF_QUEUES, MAX_NUMBER_OF_COMPUTE_RESOURCES
from datasize import DataSize

PCLUSTER_VERSION = utils.get_installed_version()
logger = setup_logger("configure-queues")

include_families = [
    "t3a",
    "m5a",
    "m5d",
    "m6i",
    "m6a",
    "c4",
    "c5",
    "c6",
    "r4",
    "r5",
    "r5a",
    "r5ad",
    "r5b",
    "r5d",
    "r5dn",
    "r5n",
    "r6a",
    "r6i",
    "r6id",
    # gpu types
    "g3",
    "g3s",
    "g4ad",
    "g4dn",
    "p2",
    "p3",
    "p4d",
]
exclude_families = ["m5dn"]
exclude_sizes = ["nano", "metal", "micro", "small", "medium", "large", "xlarge"]
include_mems = [60, 128, 356, 32, 192, 512, 768, 1024, 1536]


def size_in_gib(mib: int) -> int:
    mib_bytes = DataSize(f"{mib}Mi")
    return mib_bytes / mib_bytes.IEC_prefixes["Gi"]


def generate_preferred_families() -> List[Any]:
    return []


def get_instance_types(
    region: str = "us-east-1",
    architecture: str = "x86_64",
    include_families: Optional[List] = include_families,
    exclude_families: Optional[List] = exclude_families,
    include_gpus=True,
    exclude_sizes: Optional[List] = exclude_sizes,
    include_sizes: Optional[List] = None,
    mem_upper_limit: Optional = None,
    mem_lower_limit: Optional = None,
    vcpu_upper_limit: Optional = None,
    vcpu_lower_limit: Optional = None,
    include_mems: Optional[List[Any]] = include_mems,
    n_cpu_queues: int = 6,
    n_gpu_queues: int = 4,
):
    if n_gpu_queues + n_cpu_queues > MAX_NUMBER_OF_QUEUES:
        raise ValueError(f"Gpu queues + CPU Queues must be less than {MAX_NUMBER_OF_QUEUES}")
    if include_families is None:
        include_families = []
    if exclude_families is None:
        exclude_families = []
    if exclude_sizes is None:
        exclude_sizes = []
    if include_sizes is None:
        include_sizes = []
    if include_mems is None:
        include_mems = []

    queues = {}
    os.environ["AWS_DEFAULT_REGION"] = region
    instance_types = AWSApi.instance().ec2.list_instance_types()
    instance_records = []
    instance_type_infos = []
    for instance_type in instance_types:
        info = AWSApi.instance().ec2.get_instance_type_info(instance_type)
        instance_type = info.__dict__["instance_type_data"]
        family = instance_type["InstanceType"].split(".")[0]
        size = instance_type["InstanceType"].split(".")[1]

        size_in_mib = None
        bytes = None
        gibs = None
        arch = instance_type["ProcessorInfo"]["SupportedArchitectures"][0]
        if "MemoryInfo" in instance_type.keys():
            if "SizeInMib" in instance_type["MemoryInfo"].keys():
                size_in_mib = instance_type["MemoryInfo"]["SizeInMib"]
                bytes = DataSize(f"{size_in_mib}Mi")
                gibs = bytes / bytes.IEC_prefixes["Gi"]
                instance_type["MemoryInfo"]["SizeInGib"] = gibs
            elif "SizeInMiB" in instance_type["MemoryInfo"].keys():
                size_in_mib = instance_type["MemoryInfo"]["SizeInMiB"]
                bytes = DataSize(f"{size_in_mib}Mi")
                gibs = bytes / bytes.IEC_prefixes["Gi"]
                instance_type["MemoryInfo"]["SizeInGib"] = gibs
            else:
                raise ValueError(instance_type["MemoryInfo"])

        gpu = False
        if "GpuInfo" in instance_type:
            if "Gpus" in instance_type["GpuInfo"]:
                if len(instance_type["GpuInfo"]["Gpus"]):
                    gpu = True

        try:
            efa = instance_type["NetworkInfo"]["EfaSupported"]
        except Exception as e:
            efa = False
        instance_record = dict(
            family=family,
            arch=arch,
            size=size,
            efa=efa,
            instance_type=instance_type["InstanceType"],
            vcpus=instance_type["VCpuInfo"]["DefaultVCpus"],
            cores=instance_type["VCpuInfo"]["DefaultCores"],
            size_in_mib=size_in_mib,
            size_in_gibs=gibs,
            gpu=gpu,
        )
        instance_records.append(instance_record)

        instance_type_infos.append(instance_type)
    df = pd.DataFrame.from_records(instance_records)
    df = df[df["arch"].str.contains(architecture)]
    families = list(df["family"].unique())
    families_not_found = []
    if len(include_families):
        df = df[df["family"].str.contains("|".join(include_families))]
    if len(exclude_families):
        df = df[~df["family"].isin(exclude_families)]
    if len(exclude_sizes):
        df = df[~df["size"].isin(exclude_sizes)]

    # in us-east-1 this gets to about 48 instance types

    if not include_gpus:
        df = df[~df["gpu"]]

    if mem_upper_limit:
        df = df["size_in_gibs"] >= mem_upper_limit
    if mem_lower_limit:
        df = df["size_in_gibs"] >= mem_lower_limit

    if vcpu_upper_limit:
        df = df["vcpus"] >= vcpu_upper_limit
    if vcpu_lower_limit:
        df = df["vcpus"] >= vcpu_lower_limit

    df = df.sort_values(by=["size_in_gibs", "vcpus", "family"])
    cpu_df = df[~df["gpu"]]
    gpu_df = df[df["gpu"]]

    n_gpu_instance_types = n_gpu_queues * MAX_NUMBER_OF_COMPUTE_RESOURCES
    n_cpu_instance_types = n_cpu_queues * MAX_NUMBER_OF_COMPUTE_RESOURCES
    if gpu_df.shape[0] <= n_gpu_instance_types:
        # include all the gpus
        gpu_dfs = np.array_split(gpu_df, MAX_NUMBER_OF_COMPUTE_RESOURCES)
        for i, t_gpu_df in enumerate(gpu_dfs):
            n = i + 1
            queues[f"gpu-{n}"] = t_gpu_df.to_dict('records')

    if len(include_mems):
        cpu_df = cpu_df[cpu_df['size_in_gibs'].isin(include_mems)]

    logger.info('Writing out gpu and cpu instance types...')
    gpu_df.to_csv('pcluster_gpu_instances.csv', index=False)
    cpu_df.to_csv('pcluster_cpu_instances.csv', index=False)
    return
