# Something is up with the pcluster constants
# from pcluster.constants import MAX_NUMBER_OF_QUEUES, MAX_NUMBER_OF_COMPUTE_RESOURCES_PER_CLUSTER
MAX_NUMBER_OF_QUEUES = 10
MAX_NUMBER_OF_COMPUTE_RESOURCES_PER_QUEUE = 5
MAX_NUMBER_OF_COMPUTE_RESOURCES = 50
MAX_NUMBER_OF_COMPUTE_RESOURCES_PER_CLUSTER = 50

PCLUSTER_AMIS = {

    "3.5.1": {
        "us-east-1": "",
        "us-east-2": "",
        "eu-west-1": "",
        "eu-west-2": "ami-031a47f98f4c6babd",
    }
}
