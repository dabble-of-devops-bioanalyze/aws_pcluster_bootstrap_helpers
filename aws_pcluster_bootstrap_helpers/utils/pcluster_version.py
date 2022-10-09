from pcluster import utils

PCLUSTER_VERSION = utils.get_installed_version()


def check_pcluster_version(pcluster_version: str = "3.2"):
    if pcluster_version not in PCLUSTER_VERSION:
        w = f"""Mismatch between specified pcluster version and installed
        Specified: {pcluster_version}, Installed: {PCLUSTER_VERSION}
        """
        raise ValueError(w)
