# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import pytest
from typing import Union
from unittest.mock import Mock, patch

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

    @pytest.mark.parametrize(
        "var_name, env_vars, found",
        [
            ("AWS_SECRET_P4INFO", {"AWS_SECRET_P4INFO": "secret"}, True),
            ("AWS_SECRET_P4INFO", {"AWS_SECRET_OTHER": "secret"}, False),
            ("AWS_SECRET_P4INFO", {"AWS_SECRET_P4INFO": ""}, False),
            ("", {"AWS_SECRET_P4INFO": "secret"}, False),
            ("AWS_SECRET_OTHER", {"AWS_SECRET_P4INFO": "secret"}, False),
        ],
    )
    @patch("deadline.unreal_perforce_utils.secret_manager.get_secret_manager_client")
    def test_get_secret_from_env(
        self,
        get_secret_manager_client_mock: Mock,
        var_name: str,
        env_vars: dict[str, str],
        found: bool,
    ):
        # GIVEN
        mock_client = get_secret_manager_client_mock.return_value
        mock_client.get_secret_value.return_value = {"SecretString": "{'P4USER': 'aws-user'}"}

        # WHEN
        with patch.dict(os.environ, env_vars, clear=True):
            result = secret_manager.get_secret_from_env(var_name)

        # THEN
        assert (result is not None) == found

    @patch("deadline.unreal_perforce_utils.secret_manager.get_secret_manager_client")
    def test_get_secret_from_env_failed(self, get_secret_manager_client_mock: Mock):
        # GIVEN
        mock_client = get_secret_manager_client_mock.return_value
        mock_client.get_secret_value.return_value = {"NotSecretString": "OtherInfo"}

        # WHEN & THEN
        with patch.dict(os.environ, {"AWS_SECRET_P4INFO": "secret"}, clear=True):
            with pytest.raises(KeyError):
                secret_manager.get_secret_from_env("AWS_SECRET_P4INFO")

    @pytest.mark.parametrize(
        "env_vars, p4_info, expected_result",
        [
            (
                {"AWS_SECRET_P4INFO": "secret"},
                "{'P4PASSWD': 'pass', 'P4USER': 'user', 'P4PORT': 'port'}",
                {"P4PASSWD": "pass", "P4USER": "user", "P4PORT": "port"},
            ),
            (
                {"AWS_SECRET_P4INFO": ""},
                "{'P4PASSWD': 'pass', 'P4USER': 'user', 'P4PORT': 'port'}",
                None,
            ),
            ({"AWS_SECRET_P4INFO": "secret"}, None, None),
        ],
    )
    @patch("deadline.unreal_perforce_utils.secret_manager.get_secret_from_env")
    def test_get_perforce_info(
        self,
        get_perforce_secret_mock: Mock,
        env_vars: dict[str, str],
        p4_info: Union[dict[str, str], None],
        expected_result: Union[dict[str, str], None],
    ):
        # GIVEN
        get_perforce_secret_mock.return_value = p4_info

        # WHEN
        with patch.dict(os.environ, env_vars, clear=True):
            result = secret_manager.get_perforce_info()

        # THEN
        assert result == expected_result
