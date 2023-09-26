import os
import boto3

from typing import List, Any, Dict
import questionary

from aws_pcluster_bootstrap_helpers.utils.logging import setup_logger
from aws_pcluster_bootstrap_helpers.utils.network import get_network_data
from aws_pcluster_bootstrap_helpers.utils.efs import get_efs

logger = setup_logger("configure")
logger.propagate = False


def configure_network(region: str = "us-east-1"):
    network_data = get_network_data(region)
    vpcs = network_data["vpc_list"]
    vpc_subnets = network_data["vpc_subnets"]
    vpc_choices = list(map(lambda x: f"{x['id']} {x['name']}", vpcs))
    vpc_choices_options = list(
        map(lambda x: dict(
            label=f"{x['id']} {x['name']}",
            data=x
        ), vpcs)
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


def prompt_efs(all_efs: List[Any], efs_name="apps") -> List[Any]:
    efs_search = questionary.text(
        f"""Please enter a search pattern for the name of the existing {efs_name} EFS systems.
        None will list all EFS file systems.""",
        default=efs_name,
    ).ask()
    if efs_search:
        filtered_efs = []
        for efs in all_efs:
            if efs_search in efs['Name']:
                filtered_efs.append(efs)
    else:
        filtered_efs = all_efs
    # TODO I don't understand why this doesn't render in the terminal
    # but the other does
    filtered_efs_options = list(
        map(lambda x: dict(
            name=f"[{x['FileSystemId']}] {x['Name']}",
            label=f"[{x['FileSystemId']}] {x['Name']}",
            data=x['FileSystemId']
        ), filtered_efs)
    )
    efs_selected = questionary.select(
        "Choose a efs system", choices=filtered_efs_options
    ).ask()
    efs_choice = list(filter(lambda x: x["label"] == efs_selected, filtered_efs_options))[0]
    return efs_choice['data']


def get_all_acms(regions="us-east-1"):
    client = boto3.client('acm')
    response = client.list_certificates(CertificateStatuses=['ISSUED'])
    all_certs = []
    marker = True
    while marker:
        if 'CertificateSummaryList' in response:
            for cert in response['CertificateSummaryList']:
                all_certs.append(cert)
        if 'NextToken' in response:
            marker = response['NextToken']
            response = client.list_certificates(NextToken=marker)
        else:
            marker = False
    return all_certs


def get_all_hosted_zones(region="us-east-1"):
    client = boto3.client('route53')
    response = client.list_hosted_zones()
    all_zones = []
    marker = True
    while marker:
        if 'HostedZones' in response:
            all_zones.extend(response['HostedZones'])
        if 'NextMarker' in response:
            marker = response['NextMarker']
            response = client.list_hosted_zones(Marker=marker)
        else:
            marker = False
    return all_zones


def get_all_domains(region="us-east-1"):
    # this one only works from us-east-1
    default_region = os.environ['AWS_DEFAULT_REGION']
    os.environ['AWS_DEFAULT_REGION'] = "us-east-1"
    client = boto3.client('route53domains')
    response = client.list_domains()
    all_domains = []
    marker = True
    while marker:
        if 'Domains' in response:
            for domain in response['Domains']:
                all_domains.append(domain['DomainName'])
        if 'NextPageMarker' in response:
            marker = response['NextPageMarker']
            response = client.list_domains(Marker=marker)
        else:
            marker = False
    if default_region and isinstance(default_region, str):
        os.environ['AWS_DEFAULT_REGION'] = default_region
    return all_domains


def configure_dns(region="us-east-1"):
    data = dict(
        acm_domain=None,
        route53_zone_id=None,
        domain=None,
    )
    dns = questionary.confirm("Configure DNS for Jupyterhub?").ask()
    if not dns:
        return data

    # ACMs
    all_acms = get_all_acms()
    acm_options = list(
        map(lambda x: dict(
            name=f"{x['DomainName']}",
            label=f"{x['DomainName']}",
            data=x
        ), all_acms)
    )
    acm_selected = questionary.select(
        "Choose an ACM Certificate", choices=acm_options
    ).ask()
    acm_choice = list(filter(lambda x: x["label"] == acm_selected, acm_options))[0]
    acm_id = acm_choice['data']['DomainName']
    data['acm_domain'] = acm_id

    # Domains
    all_domains = get_all_domains(region=region)
    domain_options = all_domains
    domain_selected = questionary.select(
        "Choose a hosted domain", choices=domain_options
    ).ask()
    domain_choice = domain_selected
    data['domain'] = domain_choice

    # Zones
    all_zones = get_all_hosted_zones(region=region)
    zone_options: List[Dict[str, Any]] = list(
        map(lambda x: dict(
            name=f"{x['Name']}",
            label=f"{x['Name']}",
            data=x
        ), all_zones)
    )
    zone_selected = questionary.select(
        "Choose a hosted zone", choices=zone_options
    ).ask()
    zone_choice = list(filter(lambda x: x["label"] == zone_selected, zone_options))[0]
    zone_id = zone_choice['data']['Id'].split('/')[-1]
    data['route53_zone_id'] = zone_id

    return data


def configure_storage(region="us-east-1"):
    create_apps = questionary.confirm("Create new storage for /apps?", default=False).ask()
    create_scratch = questionary.confirm("Create new storage for /scratch?", default=False).ask()

    data = dict(
        apps_efs_id=None,
        scratch_efs_id=None,
        create_apps=False,
        create_scratch=False,
    )
    all_efs = get_efs(region)
    if not create_apps:
        apps_efs_id = prompt_efs(all_efs, efs_name="apps")
        data['apps_efs_id'] = apps_efs_id
        data['create_apps'] = False
    else:
        data['create_apps'] = True
    if not create_scratch:
        scratch_efs_id = prompt_efs(all_efs, efs_name="scratch")
        data['scratch_efs_id'] = scratch_efs_id
        data['create_scratch'] = False
    else:
        data['create_scratch'] = True

    return data


def configure_public_private_ip(region="us-east-1") -> Dict[str, Any]:
    elastic_ip = questionary.confirm("Use elastic ip for head node? (Usually true)").ask()
    use_public_ip_dns = questionary.confirm("Use the head node public IP for the DNS? (Usually true)").ask()

    return dict(
        head_node_elastic_ip=elastic_ip,
        head_node_public_ip_dns=use_public_ip_dns,
    )


def configure(region: str = "us-east-1"):
    selected_network_data = configure_network(region)
    storage = configure_storage(region)
    elastic_ip = configure_public_private_ip(region=region)
    dns = configure_dns(region)
    data = dict(
        network_data=selected_network_data,
        efs=storage,
        dns=dns,
        elastic_ip=elastic_ip,
    )
    return data
