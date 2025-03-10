# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os
import socket
import pytest
import getpass
from unittest.mock import MagicMock, Mock, patch, mock_open

from deadline.unreal_perforce_utils import app


class TestUnrealP4UtilsApp:

    @pytest.mark.parametrize(
        "project_name, env",
        [
            ("MockedProject", {}),
            ("", {}),
            (None, {}),
            ("MockedProject", {"DEADLINE_WORKER_ID": "worker-1"}),
            ("", {"DEADLINE_WORKER_ID": "worker-1"}),
            (None, {"DEADLINE_WORKER_ID": "worker-1"}),
        ],
    )
    @patch("getpass.getuser", return_value="j.doe")
    @patch("socket.gethostname", return_value="WORKER-1")
    def test_get_workspace_name(
        self, get_host_name_mock: Mock, getuser_mock: Mock, project_name: str, env: dict[str, str]
    ):
        # GIVEN
        expected = f"{getpass.getuser()}_{socket.gethostname()}_{project_name}"

        # WHEN
        with patch.dict(os.environ, env, clear=True):
            workspace_name = app.get_workspace_name(project_name)

            # THEN
            if "DEADLINE_WORKER_ID" in os.environ:
                assert workspace_name == f"{expected}_{os.environ['DEADLINE_WORKER_ID']}"
            else:
                assert workspace_name == expected

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    def test_get_workspace_specification_template_from_file(
        self, mock_exists: Mock, mock_open_file: Mock
    ):
        # GIVEN
        expected_template = {"Spec": "Value"}

        # GIVEN & WHEN
        with patch("json.load", MagicMock(side_effect=[expected_template])):
            template = app.get_workspace_specification_template_from_file("filename.json")

        # THEN
        assert template == expected_template

    def test_get_workspace_specification_template_from_non_existing_file(self):
        # GIVEN & WHEN
        with pytest.raises(FileNotFoundError) as exc_info:
            app.get_workspace_specification_template_from_file("not_existed_template.json")

        # THEN
        assert exc_info

    @pytest.mark.parametrize(
        "p4_info, openjd_env_output",
        [
            (
                {"P4PORT": "port", "P4USER": "user", "P4PASSWD": "pass"},
                ["openjd_env: P4PORT=port", "openjd_env: P4USER=user", "openjd_env: P4PASSWD=pass"],
            ),
            ({}, []),
        ],
    )
    @patch("deadline.unreal_perforce_utils.secret_manager.get_perforce_info")
    def test_apply_perforce_secrets(
        self, get_perforce_info_mock: Mock, p4_info: dict[str, str], openjd_env_output: list[str]
    ):

        # GIVEN
        get_perforce_info_mock.return_value = p4_info

        # WHEN
        with patch("builtins.print") as print_mock:
            app.apply_perforce_secrets()

        # THEN
        assert len(print_mock.mock_calls) == len(openjd_env_output)
        for i, call in enumerate(print_mock.mock_calls):
            assert call.args[0] == openjd_env_output[i]
