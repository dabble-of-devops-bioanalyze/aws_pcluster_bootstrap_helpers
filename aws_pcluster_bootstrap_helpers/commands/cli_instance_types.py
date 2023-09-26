import os
import numpy as np
from typing import List, Any, Dict, Optional
import questionary

from pcluster.aws.aws_api import AWSApi
import pandas as pd

from pcluster import utils
from datasize import DataSize
from questionary.prompts import common
from questionary.prompts.common import Choice, InquirerControl, Separator
from questionary.question import Question

from aws_pcluster_bootstrap_helpers.utils.logging import setup_logger

PCLUSTER_VERSION = utils.get_installed_version()
logger = setup_logger("configure-queues")

# from pcluster.constants import MAX_NUMBER_OF_QUEUES, MAX_NUMBER_OF_COMPUTE_RESOURCES_PER_CLUSTER
from aws_pcluster_bootstrap_helpers.utils.constants import (
    MAX_NUMBER_OF_QUEUES,
    MAX_NUMBER_OF_COMPUTE_RESOURCES_PER_QUEUE,
    MAX_NUMBER_OF_COMPUTE_RESOURCES,
    MAX_NUMBER_OF_COMPUTE_RESOURCES_PER_CLUSTER,
)

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
    "g2",
    "g3",
    "g3s",
    "g4ad",
    "g4dn",
    "p2",
    "p3",
    "p3dn",
    "p4dn",
    "p4d",
]
exclude_families = ["m5dn"]
exclude_sizes = ["nano", "metal", "micro", "small", "medium"]
include_mems = [16, 32, 60, 128, 192, 356, 512, 768, 1024, 1536]


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
        raise ValueError(
            f"Gpu queues + CPU Queues must be less than {MAX_NUMBER_OF_QUEUES}"
        )
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
    logger.info(f"Getting instance types for region: {region}")
    os.environ["AWS_DEFAULT_REGION"] = region
    instance_types = AWSApi.instance().ec2.list_instance_types()
    instance_records = []
    instance_type_infos = []
    logger.info(
        f"Getting instance type info for {len(instance_types)} in region {region}"
    )
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
    logger.info(f"Generating data frame")
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
        df = df[df["size_in_gibs"] >= mem_upper_limit]
    if mem_lower_limit:
        df = df[df["size_in_gibs"] >= mem_lower_limit]

    if vcpu_upper_limit:
        df = df[df["vcpus"] >= vcpu_upper_limit]
    if vcpu_lower_limit:
        df = df[df["vcpus"] >= vcpu_lower_limit]

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
            queues[f"gpu-{n}"] = t_gpu_df.to_dict("records")

    if len(include_mems):
        cpu_df = cpu_df[cpu_df["size_in_gibs"].isin(include_mems)]

    logger.info("Complete get instance types")
    return dict(gpu_df=gpu_df, cpu_df=cpu_df, all_df=df)


def write_instance_types_csvs(gpu_df: pd.DataFrame, cpu_df: pd.DataFrame):
    logger.info("Writing out gpu and cpu instance types...")
    gpu_df.to_csv("pcluster_gpu_instances.csv", index=False)
    cpu_df.to_csv("pcluster_cpu_instances.csv", index=False)


def prompt_for_instance_types(region="us-east-1"):
    dfs = get_instance_types(region=region)
    cpu_df = dfs["cpu_df"]
    gpu_df = dfs["gpu_df"]
    include_gpus = questionary.confirm("Create queues from GPU Instances?").ask()
    if include_gpus:
        cpu_queues = questionary.select(
            "How many cpu queues?", choices=list(range(1, MAX_NUMBER_OF_QUEUES))
        ).ask()
        gpu_queues = MAX_NUMBER_OF_QUEUES - cpu_queues
    else:
        cpu_queues = 10
        gpu_queues = 0

    n_cpu_instance_types = cpu_queues * MAX_NUMBER_OF_COMPUTE_RESOURCES
    n_gpu_instance_types = gpu_queues * MAX_NUMBER_OF_COMPUTE_RESOURCES

    cpu_queues_data = []
    cpu_labels = (
        cpu_df["instance_type"]
        + " | "
        + cpu_df["size_in_gibs"].map(str)
        + " gib"
        + " | "
        + cpu_df["vcpus"].map(str)
        + " cores"
    )
    cpu_labels = cpu_labels.map(str)
    cpu_labels = list(cpu_labels)

    gpu_labels = (
        gpu_df["instance_type"]
        + " | "
        + gpu_df["size_in_gibs"].map(str)
        + " gib"
        + " | "
        + gpu_df["vcpus"].map(str)
        + " cores"
    )
    gpu_labels = gpu_labels.map(str)
    gpu_labels = list(gpu_labels)

    cpu_min_mems = cpu_df["size_in_gibs"].min()
    cpu_max_mems = cpu_df["size_in_gibs"].max()
    gpu_min_mems = gpu_df["size_in_gibs"].min()
    gpu_max_mems = gpu_df["size_in_gibs"].max()
    cpu_mems = cpu_df["size_in_gibs"].map(str).unique().tolist()
    gpu_mems = gpu_df["size_in_gibs"].unique().tolist()
    cpu_families = cpu_df["family"].unique().tolist()
    gpu_families = gpu_df["family"].unique().tolist()

    logger.info("###################################################")
    logger.info(f"Begin selection for CPU Queues")
    logger.info(f"Choose a maximum of : {n_cpu_instance_types}")
    logger.info("###################################################")
    cpu_min_mem = questionary.select(
        "CPU min memory", choices=cpu_mems, default=cpu_mems[0]
    ).ask()
    cpu_max_mem = questionary.select(
        "CPU max memory", choices=cpu_mems, default=cpu_mems[-1]
    ).ask()
    t_cpu_df = cpu_df[cpu_df["size_in_gibs"] >= float(cpu_min_mem)]
    t_cpu_df = t_cpu_df[t_cpu_df["size_in_gibs"] <= float(cpu_max_mem)]
    families = t_cpu_df["family"].unique().tolist()
    cpu_families = questionary.checkbox(
        "CPU families",
        choices=list(map(lambda x: Choice(x, checked=True), families)),
    ).ask()
    t_cpu_df = t_cpu_df[t_cpu_df["family"].isin(cpu_families)]

    cpu_labels = (
        t_cpu_df["instance_type"]
        + " | "
        + t_cpu_df["size_in_gibs"].map(str)
        + " gib"
        + " | "
        + t_cpu_df["vcpus"].map(str)
        + " cores"
    )
    cpu_labels = cpu_labels.map(str)
    cpu_labels = list(cpu_labels)

    instance_types = questionary.checkbox(
        f"Select instance types: max {n_cpu_instance_types}",
        choices=cpu_labels,
        validate=lambda x: True
        if len(x) > n_cpu_instance_types
        else f"Please choose a maximum of: {n_cpu_instance_types}",
    ).ask()

    queue_rules = [
        # dev
        dict(
            min_mem=16,
            max_mem=96,
            preferred_families=[
                "m5",
                "m5a",
                "m5ad",
                "m5d",
                "m5dn",
                "m5n",
                "m5zn",
                "m6a",
                "m6i",
                "m6id",
                "m5",
                "m5a",
                "m6a",
                "t3a",
            ],
        ),
        # compute optimized
        dict(
            min_mem=96,
            max_mem=488,
            preferred_families=[
                "c1",
                "c3",
                "c4",
                "c5",
                "c5a",
                "c5ad",
                "c5d",
                "c5n",
                "c6a",
                "c6i",
                "c6id",
                "cc2",
                "c5",
                "c5a",
                "c4",
            ],
        ),
        # mem optimized
        dict(
            min_mem=96,
            max_mem=488,
            preferred_families=[
                "r3",
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
            ],
        ),
        dict(
            min_mem=96,
            max_mem=488,
            prefrred_families=[
                "r3",
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
                "c1",
                "c3",
                "c4",
                "c5",
                "c5a",
                "c5ad",
                "c5d",
                "c5n",
                "c6a",
                "c6i",
                "c6id",
                "cc2",
                "c5",
                "c5a",
                "c4",
            ],
        ),
        dict(min_mem=488, max_mem=768),
        dict(min_mem=488, max_mem=None),
    ]
    queues = {}
    for i, queue_rule in enumerate(queue_rules):
        if queue_rule["min_mem"]:
            cpu_queue = cpu_df[cpu_df["size_in_gibs"] >= 16]
        else:
            cpu_queue = cpu_df
        if queue_rule["max_mem"]:
            cpu_queue = cpu_queue[cpu_queue["size_in_gibs"] <= 96]

        if cpu_queue.shape[0] > MAX_NUMBER_OF_COMPUTE_RESOURCES:
            if queue_rule.get("preferred_families", None):
                cpu_queue = cpu_queue[
                    cpu_queue["family"].isin(queue_rule["preferred_families"])
                ]
            else:
                cpu_queue = cpu_queue[cpu_queue["family"].isin(include_families)]

        queues[f"cpu-{i + 1}"] = cpu_queue
        mems = cpu_queue["size_in_gibs"].unique().tolist()
        min_mem = cpu_queue["size_in_gibs"].min()
        max_mem = cpu_queue["size_in_gibs"].max()
        bins = pd.cut(
            cpu_queue["size_in_gibs"].unique(), bins=MAX_NUMBER_OF_COMPUTE_RESOURCES
        )
