# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os
import socket
import pytest
import getpass
import json
import tempfile
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
        "p4_info, openjd_env_output, expected_log_count",
        [
            (
                {"P4PORT": "port", "P4USER": "user", "P4PASSWD": "pass"},
                [
                    "openjd_redacted_env: P4PORT=port",
                    "openjd_redacted_env: P4USER=user",
                    "openjd_redacted_env: P4PASSWD=pass",
                ],
                4,
            ),
            ({}, [], 2),
        ],
    )
    @patch("deadline.unreal_perforce_utils.app.logger")
    @patch("deadline.unreal_perforce_utils.secret_manager.get_perforce_info")
    def test_apply_perforce_secrets(
        self,
        get_perforce_info_mock: Mock,
        mock_logger: Mock,
        p4_info: dict[str, str],
        openjd_env_output: list[str],
        expected_log_count: int,
    ):

        # GIVEN
        get_perforce_info_mock.return_value = p4_info

        # WHEN
        app.apply_perforce_secrets()

        # THEN
        assert len(mock_logger.mock_calls) == expected_log_count
        for expected_output in openjd_env_output:
            assert any(call.args[0] == expected_output for call in mock_logger.mock_calls)

    @patch("deadline.unreal_perforce_utils.app.logger")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_initial_workspace_sync_with_job_dependencies(
        self, mock_file, mock_exists, mock_logger
    ):
        # GIVEN
        mock_workspace = Mock()
        mock_workspace.spec = {"Root": "C:\\workspace"}
        mock_workspace.sync.return_value = None
        job_deps = {"job_dependencies": ["/path/to/dep1", "/path/to/dep2"]}
        mock_file.return_value.read.return_value = json.dumps(job_deps)
        mock_exists.return_value = True

        # WHEN
        with patch("json.load", return_value=job_deps):
            app.initial_workspace_sync(
                workspace=mock_workspace,
                unreal_project_relative_path="Project/Test.uproject",
                job_dependencies_descriptor_path="/path/to/deps.json",
            )

        # THEN
        mock_exists.assert_called_with("/path/to/deps.json")
        assert mock_workspace.sync.call_count == 6

    @patch("deadline.unreal_perforce_utils.app.logger")
    def test_initial_workspace_sync_without_job_dependencies(self, mock_logger):
        # GIVEN
        mock_workspace = Mock()
        mock_workspace.spec = {"Root": "C:\\workspace"}
        mock_workspace.sync.return_value = None

        # WHEN
        app.initial_workspace_sync(
            workspace=mock_workspace, unreal_project_relative_path="Project/Test.uproject"
        )

        # THEN
        assert mock_workspace.sync.call_count == 4

    @patch("deadline.unreal_perforce_utils.app.logger")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_initial_workspace_sync_invalid_job_dependencies_type(
        self, mock_file, mock_exists, mock_logger
    ):
        # GIVEN
        mock_workspace = Mock()
        mock_workspace.spec = {"Root": "C:\\workspace"}
        mock_workspace.sync.return_value = None
        invalid_job_deps = {"job_dependencies": "not_a_list"}  # Invalid: string instead of list
        mock_file.return_value.read.return_value = json.dumps(invalid_job_deps)
        mock_exists.return_value = True

        # WHEN
        with patch("json.load", return_value=invalid_job_deps):
            app.initial_workspace_sync(
                workspace=mock_workspace,
                unreal_project_relative_path="Project/Test.uproject",
                job_dependencies_descriptor_path="/path/to/deps.json",
            )

        # THEN
        assert mock_workspace.sync.call_count == 4

    @patch("deadline.unreal_perforce_utils.app.logger")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_initial_workspace_sync_invalid_dependency_paths(
        self, mock_file, mock_exists, mock_logger
    ):
        # GIVEN
        mock_workspace = Mock()
        mock_workspace.spec = {"Root": "C:\\workspace"}
        mock_workspace.sync.return_value = None
        job_deps = {"job_dependencies": ["/valid/path", "", None, 123]}  # Mixed valid/invalid
        mock_file.return_value.read.return_value = json.dumps(job_deps)
        mock_exists.return_value = True

        # WHEN
        with patch("json.load", return_value=job_deps):
            app.initial_workspace_sync(
                workspace=mock_workspace,
                unreal_project_relative_path="Project/Test.uproject",
                job_dependencies_descriptor_path="/path/to/deps.json",
            )

        # THEN
        assert mock_workspace.sync.call_count == 5

    def test_cli_argument_parsing_logic(self):
        """Test that the CLI argument parsing includes the new parameter."""
        import argparse

        # GIVEN - Simulate the argparser setup from cli.py
        argparser = argparse.ArgumentParser()
        argparser.add_argument("command", choices=["create_workspace", "delete_workspace"])
        argparser.add_argument("-PerforceWorkspaceSpecificationTemplate", type=str, required=True)
        argparser.add_argument("-UnrealProjectName", type=str, required=False)
        argparser.add_argument("-OverriddenWorkspaceRoot", type=str, required=False)
        argparser.add_argument("-PerforceChangelistNumber", type=int, required=False)
        argparser.add_argument("-MrqJobDependenciesDescriptor", type=str, required=False)

        # WHEN
        test_args = [
            "create_workspace",
            "-PerforceWorkspaceSpecificationTemplate",
            "/path/to/template.json",
            "-UnrealProjectName",
            "TestProject",
            "-MrqJobDependenciesDescriptor",
            "/path/to/deps.json",
        ]

        args = argparser.parse_args(test_args)

        # THEN
        assert args.command == "create_workspace"
        assert args.MrqJobDependenciesDescriptor == "/path/to/deps.json"
        assert args.UnrealProjectName == "TestProject"

    def test_job_dependencies_path_transformation(self):
        # Mock workspace
        mock_workspace = Mock()
        mock_workspace.spec = {
            "Root": "D:/projects/JobUser_EC2AMAZ-C1CN5FC_MeerkatDemo_worker-dba213772c2b48e88609f4ede8d24980"
        }
        mock_workspace.where.return_value = "D:/projects/JobUser_EC2AMAZ-C1CN5FC_MeerkatDemo_worker-dba213772c2b48e88609f4ede8d24980/Content/Assets/setKalahari/groundPlane/Textures/SimpleMountain_Color_TEX.uasset@165"
        mock_workspace.sync = Mock()

        # Mock job dependencies file
        job_data = {
            "job_dependencies": [
                "//MeerkatDemoP4/Mainline/Content/Assets/setKalahari/groundPlane/Textures/SimpleMountain_Color_TEX.uasset@165"
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(job_data, f)
            job_deps_path = f.name

        try:
            app.initial_workspace_sync(
                workspace=mock_workspace,
                unreal_project_relative_path="TestProject.uproject",
                job_dependencies_descriptor_path=job_deps_path,
            )

            # Verify workspace.where was called with depot path
            mock_workspace.where.assert_called_with(
                "//MeerkatDemoP4/Mainline/Content/Assets/setKalahari/groundPlane/Textures/SimpleMountain_Color_TEX.uasset@165"
            )

            # Verify sync was called with transformed local path
            sync_calls = [call[0][0] for call in mock_workspace.sync.call_args_list]
            assert (
                "D:/projects/JobUser_EC2AMAZ-C1CN5FC_MeerkatDemo_worker-dba213772c2b48e88609f4ede8d24980/Content/Assets/setKalahari/groundPlane/Textures/SimpleMountain_Color_TEX.uasset@165"
                in sync_calls
            )

        finally:
            os.unlink(job_deps_path)
