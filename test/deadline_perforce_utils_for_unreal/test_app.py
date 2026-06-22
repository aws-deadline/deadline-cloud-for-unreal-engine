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

    @pytest.mark.parametrize(
        "existing_root, new_root, expect_flush",
        [
            # Root changed (the customer's bug): server have-list points at the old
            # root, files don't exist at the new root, sync would no-op.
            ("E:/Perforce/ws", "C:/Perforce/ws", True),
            # Root changed only by drive letter, slashes, and trailing slash —
            # still a real move, must flush.
            ("E:\\Perforce\\ws", "C:/Perforce/ws/", True),
            # Same root with cosmetic differences (slashes, casing on Windows,
            # trailing slash) — must NOT flush, or every reuse pays the full
            # re-sync cost.
            ("C:/Perforce/ws", "c:\\Perforce\\ws", False),
            ("C:/Perforce/ws/", "C:/Perforce/ws", False),
            # Existing client has no Root yet (newly fetched, fresh client) — don't
            # flush, there's nothing to be stale.
            ("", "C:/Perforce/ws", False),
        ],
    )
    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceClient")
    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    @patch("deadline.unreal_perforce_utils.app._resolve_workspace_name")
    def test_create_workspace_flushes_have_list_when_root_changes(
        self,
        resolve_mock: Mock,
        connection_cls_mock: Mock,
        client_cls_mock: Mock,
        existing_root: str,
        new_root: str,
        expect_flush: bool,
    ):
        # GIVEN a reused workspace whose server-side Root may or may not match the new Root
        resolve_mock.return_value = app._ResolvedWorkspace(name="ws-1", reusing=True)

        connection = connection_cls_mock.return_value
        connection.p4.fetch_client.return_value = {
            "Root": existing_root,
            "View": ["//depot/A/... //ws-1/A/..."],
        }

        template = {
            "Client": "{workspace_name}",
            "Root": new_root,
            "View": ["//depot/A/... //{workspace_name}/A/..."],
        }

        # WHEN create_perforce_workspace_from_template runs with overridden_workspace_root
        # so we control the new Root precisely (bypasses P4_CLIENTS_ROOT_DIRECTORY env).
        with patch.dict(os.environ, {}, clear=True):
            app.create_perforce_workspace_from_template(
                specification_template=template,
                project_name="Project",
                overridden_workspace_root=new_root,
            )

        # THEN the have-list is flushed iff the Root actually changed
        sync_calls = [c for c in connection.p4.run.call_args_list if c.args and c.args[0] == "sync"]
        if expect_flush:
            assert (
                len(sync_calls) == 1
            ), f"expected exactly one `p4 sync` flush call, got {sync_calls}"
            assert sync_calls[0].args == ("sync", "-k", "//...#none")
            assert (
                connection.p4.client == "ws-1"
            ), "must set p4.client before flushing so flush targets the right workspace"
        else:
            assert sync_calls == [], f"must not flush when Root is unchanged, got {sync_calls}"

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceClient")
    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    @patch("deadline.unreal_perforce_utils.app._resolve_workspace_name")
    def test_create_workspace_continues_when_flush_fails(
        self,
        resolve_mock: Mock,
        connection_cls_mock: Mock,
        client_cls_mock: Mock,
    ):
        # GIVEN a reused workspace with a Root change, where the flush command errors
        resolve_mock.return_value = app._ResolvedWorkspace(name="ws-1", reusing=True)

        connection = connection_cls_mock.return_value
        connection.p4.fetch_client.return_value = {"Root": "E:/old", "View": []}
        connection.p4.run.side_effect = RuntimeError("p4 sync failed")

        template = {
            "Client": "{workspace_name}",
            "Root": "C:/new",
            "View": ["//depot/A/... //{workspace_name}/A/..."],
        }

        # WHEN
        with patch.dict(os.environ, {}, clear=True):
            result = app.create_perforce_workspace_from_template(
                specification_template=template,
                project_name="Project",
                overridden_workspace_root="C:/new",
            )

        # THEN workspace creation still completes (don't fail the whole job over
        # a flush hiccup — a downstream force-sync can still recover).
        assert result is client_cls_mock.return_value
        client_cls_mock.return_value.save.assert_called_once()  # type: ignore[attr-defined]

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceClient")
    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    @patch("deadline.unreal_perforce_utils.app._resolve_workspace_name")
    def test_create_workspace_flushes_when_not_reusing_but_server_root_differs(
        self,
        resolve_mock: Mock,
        connection_cls_mock: Mock,
        client_cls_mock: Mock,
    ):
        # GIVEN a workspace that is NOT in the local registry (reusing=False) but
        # already exists on the P4 server with a different Root (e.g. created by
        # an older version before the registry was introduced).
        resolve_mock.return_value = app._ResolvedWorkspace(name="ws-1", reusing=False)

        connection = connection_cls_mock.return_value
        connection.p4.fetch_client.return_value = {
            "Root": "C:/Users/Administrator/Perforce/old_client",
            "View": ["//depot/... //ws-1/..."],
        }

        template = {
            "Client": "{workspace_name}",
            "Root": "C:/P4projects2/ws-1",
            "View": ["//depot/... //{workspace_name}/..."],
        }

        # WHEN P4_CLIENTS_ROOT_DIRECTORY is set (persistent workspace mode)
        with patch.dict(os.environ, {"P4_CLIENTS_ROOT_DIRECTORY": "C:/P4projects2"}, clear=True):
            app.create_perforce_workspace_from_template(
                specification_template=template,
                project_name="Project",
                overridden_workspace_root="C:/P4projects2/ws-1",
            )

        # THEN the have-list is flushed even though reusing=False, because the
        # server-side workspace has a different Root.
        sync_calls = [c for c in connection.p4.run.call_args_list if c.args and c.args[0] == "sync"]
        assert len(sync_calls) == 1
        assert sync_calls[0].args == ("sync", "-k", "//...#none")

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceClient")
    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    @patch("deadline.unreal_perforce_utils.app._resolve_workspace_name")
    def test_initial_workspace_sync_uses_force_for_skeleton_not_for_dependencies(
        self,
        resolve_mock: Mock,
        connection_cls_mock: Mock,
        client_cls_mock: Mock,
        tmp_path,
    ):
        # GIVEN a workspace with a job dependencies descriptor
        resolve_mock.return_value = app._ResolvedWorkspace(name="ws-1", reusing=False)

        connection = connection_cls_mock.return_value
        connection.p4.fetch_client.return_value = {"Root": "", "View": []}

        workspace_mock = client_cls_mock.return_value
        workspace_mock.spec = {"Root": "C:/P4root/ws-1"}
        workspace_mock.where.side_effect = lambda dp: f"C:/P4root/ws-1/{dp.split('//depot/')[-1]}"

        deps_file = tmp_path / "deps.json"
        deps_file.write_text(
            json.dumps(
                {
                    "job_dependencies": [
                        "//depot/Project/Content/file1.uasset",
                        "//depot/Project/Content/file2.uasset",
                    ]
                }
            )
        )

        template = {
            "Client": "{workspace_name}",
            "Root": "C:/P4root/ws-1",
            "View": ["//depot/... //{workspace_name}/..."],
        }

        # WHEN
        with patch.dict(os.environ, {"P4_CLIENTS_ROOT_DIRECTORY": "C:/P4root"}, clear=True):
            app.create_perforce_workspace_from_template(
                specification_template=template,
                project_name="Project",
                overridden_workspace_root="C:/P4root/ws-1",
            )

        # Manually call initial_workspace_sync since create_perforce_workspace_from_template
        # is tested via create_workspace which we can't easily call without full P4 setup
        app.initial_workspace_sync(
            workspace=workspace_mock,
            unreal_project_relative_path="Project/Project.uproject",
            changelist="3",
            job_dependencies_descriptor_path=str(deps_file),
        )

        # THEN skeleton files synced with force=True, deps with force=False
        sync_calls = workspace_mock.sync.call_args_list
        skeleton_calls = [c for c in sync_calls if c.kwargs.get("force") is True]
        dep_calls = [c for c in sync_calls if c.kwargs.get("force") is False]

        assert len(skeleton_calls) == 4  # uproject, Binaries, Config, Plugins
        assert len(dep_calls) == 2  # file1.uasset, file2.uasset

    def test_initial_workspace_sync_emits_dependencies_synced(self, tmp_path, caplog):
        # GIVEN a workspace and a valid dependencies descriptor
        workspace_mock = MagicMock()
        workspace_mock.spec = {"Root": "C:/P4root/ws-1"}
        workspace_mock.where.side_effect = lambda dp: f"C:/P4root/ws-1/{dp.split('//depot/')[-1]}"

        deps_file = tmp_path / "deps.json"
        deps_file.write_text(
            json.dumps(
                {
                    "job_dependencies": [
                        "//depot/Project/Content/file1.uasset",
                    ]
                }
            )
        )

        # WHEN
        app.initial_workspace_sync(
            workspace=workspace_mock,
            unreal_project_relative_path="Project/Project.uproject",
            changelist="3",
            job_dependencies_descriptor_path=str(deps_file),
        )

        # THEN DEPENDENCIES_SYNCED is emitted
        assert "openjd_env: DEPENDENCIES_SYNCED=true" in caplog.text

    def test_initial_workspace_sync_no_signal_without_deps(self, tmp_path, caplog):
        # GIVEN a workspace with no dependencies descriptor
        workspace_mock = MagicMock()
        workspace_mock.spec = {"Root": "C:/P4root/ws-1"}

        # WHEN
        app.initial_workspace_sync(
            workspace=workspace_mock,
            unreal_project_relative_path="Project/Project.uproject",
            changelist="3",
            job_dependencies_descriptor_path=None,
        )

        # THEN DEPENDENCIES_SYNCED is NOT emitted
        assert "DEPENDENCIES_SYNCED" not in caplog.text
