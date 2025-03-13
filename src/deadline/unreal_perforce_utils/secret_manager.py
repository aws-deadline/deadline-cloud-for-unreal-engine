# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import ast
import traceback
from typing import Optional, Any

import boto3
from botocore.exceptions import ClientError
from botocore.utils import InstanceMetadataRegionFetcher

from deadline.unreal_logger import get_logger
from deadline.unreal_perforce_utils import exceptions


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


def get_secret(secret_name: str) -> str:
    """
    Retrieves a secret from Boto3 SecretsManager using passed environment variable name to get secret name.

    :param secret_name: The name (id) of the secret
    :type secret_name: str
    :return: The secret string
    :rtype: str
    """
    logger.info(f"Getting secret by name: {secret_name}")

    sm_client = get_secret_manager_client()
    try:
        response = sm_client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise exceptions.SecretsManagerError(
            f"Failed to get secret from Boto3 SecretsManager by name {secret_name}."
            f"{e} -- {traceback.format_exc()}"
        )

    if "SecretString" not in response:
        raise KeyError(f"SecretString key not found in response: {response}")

    return response["SecretString"]


def validate_perforce_info(perforce_info_str: str, allowed_keys: set[str]) -> dict[str, Any]:
    try:
        perforce_info = ast.literal_eval(perforce_info_str)
        if not isinstance(perforce_info, dict):
            raise ValueError(
                f"Perforce info string content is not a dictionary: {perforce_info_str}"
            )

        actual_keys = set(perforce_info.keys())
        if not actual_keys:
            raise ValueError(
                "Perforce info must not be empty and should contain at least one of "
                f"{allowed_keys}"
            )

        if not actual_keys.issubset(allowed_keys):
            raise ValueError(
                f"Perforce info contains invalid keys. "
                f"Allowed keys: {allowed_keys}. Found: {actual_keys}"
            )

        return perforce_info

    except (ValueError, SyntaxError) as e:
        raise exceptions.SecretsManagerError(
            f"Failed to parse perforce info from Boto3 SecretsManager: {perforce_info_str}."
            f"{e} -- {traceback.format_exc()}"
        )


def get_perforce_info() -> Optional[dict[str, str]]:
    """
    Retrieves perforce connection parameters from Boto3 SecretsManager
    using AWS_SECRET_P4INFO environment to get secret name.

    :return: The perforce connection parameters
    :rtype: Optional[dict[str, str]]
    """

    secret_env_name = "AWS_SECRET_P4INFO"
    secret_env_value = os.getenv(secret_env_name)
    if secret_env_value == "":
        logger.warning(
            f"{secret_env_name} environment variable is empty string ''. Skip get perforce info"
        )
        return None
    if secret_env_value is None:
        logger.warning(f"{secret_env_name} environment variable not found. Skip get perforce info")
        return None

    p4_info_secret = get_secret(secret_env_value)
    return validate_perforce_info(p4_info_secret, allowed_keys={"P4PORT", "P4USER", "P4PASSWD"})
