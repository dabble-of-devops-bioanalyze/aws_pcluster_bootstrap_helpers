import boto3


def get_acms(region: str = "us-east-1"):
    acm_client = boto3.client("acm", region_name=region)

    response = acm_client.list_certificates()

    certificates = response["CertificateSummaryList"]
    while response.get("NextToken"):
        response = acm_client.list_certificates(NextToken=response["NextToken"])
        certificates.extend(response["CertificateSummaryList"])

    return certificates
