# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import ast
from typing import Optional

import boto3
from botocore.utils import InstanceMetadataRegionFetcher

from deadline.unreal_logger import get_logger


logger = get_logger()


def get_secret_manager_client():
    """
    Creates a boto3 client for the AWS SecretsManager service.

    This function figures out the region to use. If the environment variable
    `AWS_REGION_NAME` is set, it will be used. Otherwise, the region will be
    determined by the `botocore.utils.InstanceMetadataRegionFetcher.retrieve_region()`.

    :return: A SecretsManager client
    """

    client_params = {"service_name": "secretsmanager"}

    if "AWS_REGION_NAME" in os.environ and os.environ["AWS_REGION_NAME"] != "":
        client_params["region_name"] = os.environ["AWS_REGION_NAME"]
    else:
        fetcher = InstanceMetadataRegionFetcher()
        client_params["region_name"] = fetcher.retrieve_region()
    logger.info(f"SecretsManager client parameters: {client_params}")

    return boto3.client(**client_params)


def get_secret_from_env(secret_variable_name: str) -> Optional[str]:
    """
    Retrieves a secret from Boto3 SecretsManager using passed environment variable name to get secret name.

    :param secret_variable_name: The name of the environment variable containing the secret id
    :type secret_variable_name: str
    :return: The secret string
    :rtype: Optional[str]
    """
    logger.info(f"Getting perforce secret from environment variable: {secret_variable_name}")

    sm_client = get_secret_manager_client()

    secret_id = os.getenv(secret_variable_name)
    if secret_id in [None, ""]:
        logger.warning(
            f"Cant get perforce secret from empty environment variable {secret_variable_name}"
        )
        return None

    response = sm_client.get_secret_value(SecretId=secret_id)
    if "SecretString" not in response:
        raise KeyError(f"SecretString key not found in response: {response}")

    return response["SecretString"]


def get_perforce_info() -> Optional[dict[str, str]]:
    """
    Retrieves perforce connection parameters from Boto3 SecretsManager
    using AWS_SECRET_P4INFO environment to get secret name.

    :return: The perforce connection parameters
    :rtype: Optional[dict[str, str]]
    """

    secret_env_name = "AWS_SECRET_P4INFO"
    if os.getenv(secret_env_name) in [None, ""]:
        logger.warning(
            f"{secret_env_name} environment variable not found or empty. Cant get perforce info"
        )
        return None

    p4_info_secret = get_secret_from_env(secret_env_name)
    return ast.literal_eval(p4_info_secret) if p4_info_secret else None
