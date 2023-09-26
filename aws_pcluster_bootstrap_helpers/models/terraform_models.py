import datetime
from typing import Any, List, Optional
from pydantic import BaseModel
from jinja2 import Template
import json


class TerraformVariable(BaseModel):
    name: str
    default: Optional[Any] = None
    type: Optional[str] = None
    description: Optional[str] = None

    def render_to_terraform_variable(self):
        # Define the Jinja template
        d = self.__dict__
        template_string = """
        variable "{{item['name']}}" {% raw %} { {% endraw %}
            {% if item['type'] is not none %}
                type = "{{ item['type'] }}"
            {% endif %}
            {% if item['description'] is not none %}
                description = "{{ item['description'] }}"
            {% endif %}
            {% if item['default'] is not none %}
                default = "{{ item['default'] }}"
            {% endif %}
        {% raw %} } {% endraw %}
        """
        # Create the Jinja template object
        template = Template(template_string)

        # Render the template with the filtered data
        result = template.render(item=d)
        return result


class AWS(BaseModel):
    region: str = "us-east-1"
    vpc_id: str
    subnet_ids: List[str]


class BaseTags(BaseModel):
    name: str = "slurm"
    namespace: str = "bioanalyze"
    environment: str = "hpc"
    stage: str = "dev"


class PCluster(BaseModel):
    os: str = "ubuntu2004"
    build_ami: bool = False
    pcluster_ami_owner: str = "666813242062"
    pcluster_ami: str = "ami-0c7f8073ad4068592"
    pcluster_version: str = "3.5.0"
    head_node_instance_type: str = "t3a.medium"
    use_head_node_elastic_ip: bool = True


class Jhub(BaseModel):
    use_internal: bool = False
    domain: str
    acm: str


class EFS(BaseModel):
    mount_path: str
    use_existing_efs: bool = False
    efs_id: Optional[str] = None


class PClusterBootstrap(BaseModel):
    mounted_efs: List[EFS] = [EFS(mount_path="/apps"), EFS(mount_path="/scratch")]
    aws: AWS
