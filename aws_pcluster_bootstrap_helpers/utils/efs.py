import os
import boto3
import questionary

import boto3
from typing import List, Any, Dict, Optional


def get_efs(region: str = "us-east-1") -> List[Dict[str, Any]]:
    efs_client = boto3.client("efs", region_name=region)

    response = efs_client.describe_file_systems()

    file_systems = response["FileSystems"]
    while response.get("NextMarker"):
        response = efs_client.describe_file_systems(Marker=response["NextMarker"])
        file_systems.extend(response["FileSystems"])

    for file_system in file_systems:
        file_system['label'] = f"{file_system['Name']} - {file_system['FileSystemId']}"

    return file_systems
