#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages
import versioneer

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("HISTORY.md") as history_file:
    history = history_file.read()

with open("requirements.txt", "r") as fh:
    requirements = [line.strip() for line in fh]

test_requirements = []

setup(
    author="Jillian Rowe",
    author_email="jillian@dabbleofdevops.com",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Helpers to bootstrap a AWS PCluster + SLURM + Custom AMIs",
    entry_points={
        "console_scripts": [
            "pcluster-bootstrap-helper=aws_pcluster_bootstrap_helpers.cli:cli",
        ],
    },
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="aws_pcluster_bootstrap_helpers",
    name="aws_pcluster_bootstrap_helpers",
    packages=find_packages(
        include=["aws_pcluster_bootstrap_helpers", "aws_pcluster_bootstrap_helpers.*"]
    ),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/dabble-of-devops-bioanalyze/aws_pcluster_bootstrap_helpers",
    # version="0.5.0",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    zip_safe=False,
)
