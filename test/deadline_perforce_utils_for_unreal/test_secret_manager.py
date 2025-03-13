# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import ast
import pytest
from typing import Union
from unittest.mock import Mock, patch, MagicMock

from deadline.unreal_perforce_utils import exceptions
from deadline.unreal_perforce_utils import secret_manager


class TestSecretManager:

    @pytest.mark.parametrize(
        "env_vars, fetcher_output, expected_params",
        [
            (
                {"AWS_REGION_NAME": "env-region"},
                "fetcher-region",
                {"service_name": "secretsmanager", "region_name": "env-region"},
            ),
            (
                {"AWS_REGION_NAME": "env-region"},
                None,
                {"service_name": "secretsmanager", "region_name": "env-region"},
            ),
            (
                {},
                "fetcher-region",
                {"service_name": "secretsmanager", "region_name": "fetcher-region"},
            ),
            (
                {},
                None,
                {"service_name": "secretsmanager", "region_name": None},
            ),
            (
                {"AWS_REGION_NAME": ""},
                "fetcher-region",
                {"service_name": "secretsmanager", "region_name": "fetcher-region"},
            ),
            (
                {"AWS_REGION_NAME": ""},
                None,
                {"service_name": "secretsmanager", "region_name": None},
            ),
        ],
    )
    def test_get_secret_manager_client(
        self, env_vars: dict[str, str], fetcher_output: str, expected_params: dict[str, str]
    ):

        # GIVEN & WHEN
        with patch(
            "deadline.unreal_perforce_utils.secret_manager.InstanceMetadataRegionFetcher"
        ) as fetcher_mock:
            with patch.dict(os.environ, env_vars, clear=True):
                with patch("boto3.client") as boto3_client_mock:
                    fetcher_mock.return_value.retrieve_region.return_value = fetcher_output
                    secret_manager.get_secret_manager_client()
                    boto3_client_mock.assert_called_once_with(**expected_params)

    @patch("deadline.unreal_perforce_utils.secret_manager.get_secret_manager_client")
    def test_get_secret(self, get_secret_manager_client_mock: Mock):
        # GIVEN
        expected_result = "{'P4USER': 'aws-user'}"
        mock_client = get_secret_manager_client_mock.return_value
        mock_client.get_secret_value.return_value = {"SecretString": expected_result}

        # WHEN
        result = secret_manager.get_secret("secret-name")

        # THEN
        assert result == expected_result

    @patch("deadline.unreal_perforce_utils.secret_manager.get_secret_manager_client")
    def test_get_secret_failed_to_get_secret(self, get_secret_manager_client_mock: Mock):
        # GIVEN
        mock_client = get_secret_manager_client_mock.return_value
        mock_client.get_secret_value = MagicMock(
            side_effect=secret_manager.ClientError(
                {"Error": {"Code": "ResourceNotFoundException"}}, "get_secret_value"
            ),
        )

        # WHEN & THEN
        with pytest.raises(exceptions.SecretsManagerError):
            secret_manager.get_secret("secret-name")

    @patch("deadline.unreal_perforce_utils.secret_manager.get_secret_manager_client")
    def test_get_secret_failed_to_find_secret_string(self, get_secret_manager_client_mock: Mock):
        mock_client = get_secret_manager_client_mock.return_value
        mock_client.get_secret_value.return_value = {"NotSecretString": "OtherInfo"}

        # WHEN & THEN
        with pytest.raises(KeyError):
            secret_manager.get_secret("secret-name")

    @pytest.mark.parametrize(
        "p4_info_str, allowed_keys",
        [
            ("123,user,port", {}),
            ("cant eval", {}),
            ("123", {}),
            ("{}", {}),
            ("{'P4OTHER': 'other'}", {"P4USER"}),
            ("{'P4OTHER': 'other', 'P4USER': 'aws-user'}", {"P4USER"}),
            ("{'P4OTHER': 'other', 'P4USER': 'aws-user'}", {}),
        ],
    )
    def test_validate_perforce_info_failed(self, p4_info_str: str, allowed_keys: set[str]):
        # GIVEN & WHEN
        with pytest.raises(exceptions.SecretsManagerError):
            secret_manager.validate_perforce_info(p4_info_str, allowed_keys)

    @pytest.mark.parametrize(
        "p4_info_str, allowed_keys",
        [
            ("{'P4USER': 'aws-user'}", {"P4USER"}),
            ("{'P4USER': 'aws-user'}", {"P4USER", "P4PORT"}),
            ("{'P4USER': 'aws-user', 'P4PORT': 'aws-port'}", {"P4USER", "P4PORT"}),
            ("{'P4USER': 'aws-user', 'P4PASSWD': 'aws-pass'}", {"P4USER", "P4PASSWD"}),
            ("{'P4USER': 'aws-user', 'P4PASSWD': 'aws-pass'}", {"P4USER", "P4PASSWD", "P4PORT"}),
            (
                "{'P4USER': 'aws-user', 'P4PASSWD': 'aws-pass', 'P4PORT': 'aws-port'}",
                {"P4USER", "P4PASSWD", "P4PORT"},
            ),
        ],
    )
    def test_validate_perforce_info(self, p4_info_str: str, allowed_keys: set[str]):
        # WHEN
        p4_info = secret_manager.validate_perforce_info(p4_info_str, allowed_keys)

        # THEN
        assert p4_info == ast.literal_eval(p4_info_str)

    @pytest.mark.parametrize(
        "env_vars, get_secret_output, expected_result",
        [
            ({"AWS_SECRET_P4INFO": ""}, None, None),
            ({}, None, None),
            (
                {"AWS_SECRET_P4INFO": "secret"},
                "{'P4PASSWD': 'pass', 'P4USER': 'user', 'P4PORT': 'port'}",
                {"P4PASSWD": "pass", "P4USER": "user", "P4PORT": "port"},
            ),
        ],
    )
    @patch("deadline.unreal_perforce_utils.secret_manager.get_secret")
    def test_get_perforce_info(
        self,
        get_secret_mock: Mock,
        env_vars: dict[str, str],
        get_secret_output: Union[dict[str, str], None],
        expected_result: Union[dict[str, str], None],
    ):
        # GIVEN
        get_secret_mock.return_value = get_secret_output

        # WHEN
        with patch.dict(os.environ, env_vars, clear=True):
            result = secret_manager.get_perforce_info()

        # THEN
        assert result == expected_result
