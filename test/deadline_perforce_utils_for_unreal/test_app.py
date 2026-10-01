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

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceClient")
    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_create_workspace_falls_back_to_home_perforce_when_env_unset(
        self, connection_cls_mock: Mock, client_cls_mock: Mock, caplog
    ):
        # GIVEN P4_CLIENTS_ROOT_DIRECTORY is unset and no override is passed.
        # Keep USERNAME in env (needed by getpass.getuser() on Windows for the
        # workspace name) but clear P4_CLIENTS_ROOT_DIRECTORY specifically.
        connection_cls_mock.return_value.p4.fetch_client.return_value = {
            "Root": "",
            "View": [],
        }
        template = {
            "Client": "{workspace_name}",
            "View": ["//depot/A/... //{workspace_name}/A/..."],
        }

        # WHEN
        import logging

        env_without_p4_root = {
            k: v for k, v in os.environ.items() if k != "P4_CLIENTS_ROOT_DIRECTORY"
        }
        with patch.dict(os.environ, env_without_p4_root, clear=True), caplog.at_level(logging.INFO):
            app.create_perforce_workspace_from_template(
                specification_template=template,
                project_name="Project",
            )

        # THEN the resulting Root is under ~/Perforce and the info message fires
        expected_prefix = os.path.join(os.path.expanduser("~"), "Perforce")
        normalized_root = str(template["Root"]).replace("\\", "/")
        normalized_prefix = expected_prefix.replace("\\", "/")
        assert normalized_root.startswith(
            normalized_prefix
        ), f"Root {template['Root']!r} should start with {expected_prefix!r}"
        assert "P4_CLIENTS_ROOT_DIRECTORY is not set" in caplog.text

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceClient")
    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_create_workspace_no_fallback_log_when_persistent_root_set(
        self, connection_cls_mock: Mock, client_cls_mock: Mock, tmp_path, caplog
    ):
        # GIVEN P4_CLIENTS_ROOT_DIRECTORY is set explicitly
        connection_cls_mock.return_value.p4.fetch_client.return_value = {
            "Root": str(tmp_path / "ws-1"),
            "View": [],
        }
        template = {
            "Client": "{workspace_name}",
            "View": ["//depot/A/... //{workspace_name}/A/..."],
        }

        # WHEN — keep current env (for USERNAME etc.) and add the P4 root
        import logging

        with (
            patch.dict(os.environ, {"P4_CLIENTS_ROOT_DIRECTORY": str(tmp_path)}, clear=False),
            caplog.at_level(logging.INFO),
        ):
            app.create_perforce_workspace_from_template(
                specification_template=template,
                project_name="Project",
            )

        # THEN the fallback message does NOT fire
        assert "P4_CLIENTS_ROOT_DIRECTORY is not set" not in caplog.text

    def test_delete_workspace_skips_when_env_set(self, caplog):
        # GIVEN env var is set (explicit persistent mode)
        import logging

        # WHEN
        with (
            patch.dict(os.environ, {"P4_CLIENTS_ROOT_DIRECTORY": "D:/projects"}, clear=True),
            caplog.at_level(logging.INFO),
        ):
            app.delete_workspace(workspace_name="ws-1")

        # THEN the explicit-env-set message logs
        assert "P4_CLIENTS_ROOT_DIRECTORY is set" in caplog.text
        assert "skipping workspace deletion" in caplog.text

    def test_delete_workspace_skips_when_env_unset(self, caplog):
        # GIVEN env var is unset (fallback persistent mode)
        import logging

        # WHEN
        with patch.dict(os.environ, {}, clear=True), caplog.at_level(logging.INFO):
            app.delete_workspace(workspace_name="ws-1")

        # THEN the fallback-skip message logs, mentioning the ~/Perforce default
        assert "P4_CLIENTS_ROOT_DIRECTORY is not set" in caplog.text
        assert "skipping workspace deletion" in caplog.text
        assert "Perforce" in caplog.text

    # ---- submit_renders -----------------------------------------------------

    def _make_p4_mock_for_submit(
        self, reconcile_returns=None, save_change_cl="42", opened_after_revert=None
    ):
        """Build a P4 mock that simulates a successful reconcile + submit flow."""
        p4_mock = MagicMock()
        p4_mock.run.return_value = []
        # Reconcile returns the list of opened files (truthy) by default;
        # tests can override per-call via side_effect.
        if reconcile_returns is None:
            reconcile_returns = [{"depotFile": "//depot/A/foo.png"}]
        # `p4 opened -c <cl>` is called after revert -a to detect an empty CL.
        # Default: same files reconcile reported (i.e. revert -a stripped nothing).
        if opened_after_revert is None:
            opened_after_revert = reconcile_returns

        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else None
            if cmd == "reconcile":
                return reconcile_returns
            if cmd == "opened":
                return opened_after_revert
            return []

        p4_mock.run.side_effect = run_side_effect
        p4_mock.fetch_change.return_value = {"Change": "new", "Description": ""}
        p4_mock.save_change.return_value = [f"Change {save_change_cl} created."]
        return p4_mock

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_returns_none_when_no_directories(
        self, connection_cls_mock: Mock, caplog
    ):
        # WHEN no output directories are passed
        result = app.submit_renders(
            unreal_project_name="MyProject",
            output_directories=[],
        )

        # THEN we return None and never touch P4 at all
        assert result is None
        connection_cls_mock.assert_not_called()

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_returns_none_when_nothing_changed(
        self, connection_cls_mock: Mock, caplog
    ):
        # GIVEN reconcile finds no changes
        p4_mock = self._make_p4_mock_for_submit(reconcile_returns=[])
        connection_cls_mock.return_value.p4 = p4_mock

        # WHEN
        result = app.submit_renders(
            unreal_project_name="MyProject",
            output_directories=["C:/renders/MyProject"],
            mode="submit",
        )

        # THEN no CL is created, no submit happens, return None
        assert result is None
        run_calls = [c.args for c in p4_mock.run.call_args_list]
        assert any(call[0] == "reconcile" for call in run_calls), "expected reconcile to be called"
        assert not any(
            call[0] == "submit" for call in run_calls
        ), "must not submit when nothing reconciled"
        p4_mock.save_change.assert_not_called()

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_treats_no_files_to_reconcile_as_clean(self, connection_cls_mock: Mock):
        # GIVEN reconcile raises with the "no file(s) to reconcile" message
        # (P4 raises rather than returning [] in this case)
        p4_mock = MagicMock()

        def run_side_effect(*args, **kwargs):
            if args and args[0] == "reconcile":
                raise RuntimeError("/depot/foo/... - no file(s) to reconcile")
            return []

        p4_mock.run.side_effect = run_side_effect
        connection_cls_mock.return_value.p4 = p4_mock

        # WHEN
        result = app.submit_renders(
            unreal_project_name="MyProject",
            output_directories=["C:/renders/MyProject"],
            mode="submit",
        )

        # THEN treated as clean no-op
        assert result is None

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_full_happy_path(self, connection_cls_mock: Mock):
        # GIVEN reconcile finds files and submit succeeds
        p4_mock = self._make_p4_mock_for_submit(save_change_cl="123")
        connection_cls_mock.return_value.p4 = p4_mock

        # WHEN
        with patch.dict(
            os.environ,
            {
                "DEADLINE_FARM_ID": "farm-123",
                "DEADLINE_QUEUE_ID": "queue-456",
                "DEADLINE_JOB_ID": "job-789",
            },
            clear=False,
        ):
            cl_number = app.submit_renders(
                unreal_project_name="MyProject",
                output_directories=["C:/renders/MyProject"],
                description="Custom note from customer",
                mode="submit",
            )

        # THEN we got the CL back and the full sequence ran
        assert cl_number == 123
        run_calls = [c.args for c in p4_mock.run.call_args_list]
        # Reconcile fired, submit fired, in that order; reopen between them
        assert run_calls[0][0] == "reconcile"
        assert run_calls[-1][0] == "submit"
        assert any(c[0] == "reopen" for c in run_calls)

        # The description includes the deadline IDs and the customer's extra note
        saved_change = p4_mock.save_change.call_args[0][0]
        desc = saved_change["Description"]
        assert "farm-123" in desc
        assert "queue-456" in desc
        assert "job-789" in desc
        assert "Custom note from customer" in desc

        # And `Files` was explicitly cleared before save_change — otherwise
        # stale opens in the default CL would ride along into this numbered
        # CL via fetch_change's auto-populate. Belt-and-suspenders against
        # over-shelving foreign files from prior tasks/jobs.
        assert saved_change.get("Files") == []

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_shelve_mode_emits_openjd_env(self, connection_cls_mock: Mock, caplog):
        # GIVEN reconcile finds files and we're in shelve mode
        p4_mock = self._make_p4_mock_for_submit(save_change_cl="555")
        connection_cls_mock.return_value.p4 = p4_mock

        # WHEN
        import logging

        with caplog.at_level(logging.INFO):
            cl_number = app.submit_renders(
                unreal_project_name="MyProject",
                output_directories=["C:/renders/MyProject"],
                mode="shelve",
            )

        # THEN we shelved, didn't submit, and emitted the openjd_env signal
        assert cl_number == 555
        run_calls = [c.args for c in p4_mock.run.call_args_list]
        assert any(c[0] == "shelve" for c in run_calls)
        assert not any(c[0] == "submit" for c in run_calls)
        assert "openjd_env: SHELVED_CL=555" in caplog.text
        # AND we reverted the local opens after shelving. Without this, a
        # downstream `unshelve -c <aggregate>` fails on every file with
        # "already opened for add in change 555" and the aggregate CL ends
        # up empty. `revert -k` drops the local metadata without touching
        # the working files.
        post_shelve_revert = [
            c for c in run_calls if c[0] == "revert" and "-k" in c and "-c" in c and "555" in c
        ]
        assert len(post_shelve_revert) == 1, (
            f"expected exactly one post-shelve `revert -k -c 555 //...`, "
            f"got {post_shelve_revert}"
        )

    @patch("deadline.unreal_perforce_utils.app.time.sleep")
    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_retries_transient_submit_errors(
        self, connection_cls_mock: Mock, sleep_mock: Mock
    ):
        # GIVEN submit fails twice with a transient error then succeeds
        p4_mock = MagicMock()
        p4_mock.fetch_change.return_value = {"Change": "new", "Description": ""}
        p4_mock.save_change.return_value = ["Change 99 created."]

        # Track how many times submit has been called
        submit_call_count = {"n": 0}

        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else None
            if cmd == "reconcile":
                return [{"depotFile": "//depot/foo.png"}]
            if cmd == "opened":
                return [{"depotFile": "//depot/foo.png"}]
            if cmd == "submit":
                submit_call_count["n"] += 1
                if submit_call_count["n"] < 3:
                    raise RuntimeError("file(s) currently locked by another client")
                return []
            return []

        p4_mock.run.side_effect = run_side_effect
        connection_cls_mock.return_value.p4 = p4_mock

        # WHEN
        cl_number = app.submit_renders(
            unreal_project_name="MyProject",
            output_directories=["C:/renders/MyProject"],
            mode="submit",
            max_submit_retries=3,
        )

        # THEN we retried twice and succeeded on the third attempt
        assert cl_number == 99
        assert submit_call_count["n"] == 3
        # sleep was called between attempts (not after the successful one)
        assert sleep_mock.call_count == 2

    @patch("deadline.unreal_perforce_utils.app.time.sleep")
    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_does_not_retry_non_transient_errors(
        self, connection_cls_mock: Mock, sleep_mock: Mock
    ):
        # GIVEN submit fails with a non-transient error (e.g. permission denied)
        p4_mock = MagicMock()
        p4_mock.fetch_change.return_value = {"Change": "new", "Description": ""}
        p4_mock.save_change.return_value = ["Change 7 created."]

        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else None
            if cmd == "reconcile":
                return [{"depotFile": "//depot/foo.png"}]
            if cmd == "opened":
                return [{"depotFile": "//depot/foo.png"}]
            if cmd == "submit":
                raise RuntimeError("permission denied for resource '//depot/...'")
            return []

        p4_mock.run.side_effect = run_side_effect
        connection_cls_mock.return_value.p4 = p4_mock

        # WHEN / THEN — error propagates without retry
        with pytest.raises(RuntimeError, match="permission denied"):
            app.submit_renders(
                unreal_project_name="MyProject",
                output_directories=["C:/renders/MyProject"],
                mode="submit",
                max_submit_retries=3,
            )
        sleep_mock.assert_not_called()

    def test_submit_renders_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="'submit', or 'shelve'"):
            app.submit_renders(
                unreal_project_name="MyProject",
                output_directories=["C:/x"],
                mode="something-else",
            )

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_default_mode_is_noop(self, connection_cls_mock: Mock, caplog):
        # GIVEN no mode is passed (default: empty string = no-op)
        import logging

        with caplog.at_level(logging.INFO):
            result = app.submit_renders(
                unreal_project_name="MyProject",
                output_directories=["C:/renders/MyProject"],
            )

        # THEN we never touch P4 and explain why in the log
        assert result is None
        connection_cls_mock.assert_not_called()
        assert "skipping" in caplog.text.lower()
        assert "Job Attachments still runs" in caplog.text

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_returns_none_when_revert_a_strips_everything(
        self, connection_cls_mock: Mock, caplog
    ):
        # GIVEN reconcile opened files (because the adaptor's `p4 edit` opened
        # the whole MovieRenders dir), but the new render didn't actually change
        # any of them — so `revert -a` strips them all.
        p4_mock = self._make_p4_mock_for_submit(
            reconcile_returns=[{"depotFile": "//depot/A/foo.png"}],
            opened_after_revert=[],  # CL is empty after revert -a
        )
        connection_cls_mock.return_value.p4 = p4_mock

        import logging

        with caplog.at_level(logging.INFO):
            result = app.submit_renders(
                unreal_project_name="MyProject",
                output_directories=["C:/renders/MyProject"],
                mode="submit",
            )

        # THEN we return None (matches the no-reconcile path), the empty CL
        # is deleted, and submit is never called.
        assert result is None
        run_calls = [c.args for c in p4_mock.run.call_args_list]
        assert any(
            call[0] == "change" and call[1] == "-d" for call in run_calls
        ), "expected `p4 change -d` to delete the empty CL"
        assert not any(call[0] == "submit" for call in run_calls), "must not submit an empty CL"
        assert "empty after revert -a" in caplog.text

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_calls_revert_a_before_submit(self, connection_cls_mock: Mock):
        # GIVEN a successful submit flow
        p4_mock = self._make_p4_mock_for_submit(save_change_cl="42")
        connection_cls_mock.return_value.p4 = p4_mock

        # WHEN
        app.submit_renders(
            unreal_project_name="MyProject",
            output_directories=["C:/renders/MyProject"],
            mode="submit",
        )

        # THEN `revert -a -c <cl>` runs after reopen and before submit
        run_calls = [c.args for c in p4_mock.run.call_args_list]
        cmd_order = [c[0] for c in run_calls]
        assert "revert" in cmd_order
        revert_idx = cmd_order.index("revert")
        # Find indices of reopen and submit
        reopen_idx = cmd_order.index("reopen")
        submit_idx = cmd_order.index("submit")
        assert (
            reopen_idx < revert_idx < submit_idx
        ), f"expected reopen → revert → submit, got {cmd_order}"
        # And revert was called with -a -c <cl> //...
        revert_call = run_calls[revert_idx]
        assert revert_call[1] == "-a"
        assert revert_call[2] == "-c"
        assert revert_call[3] == "42"

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_syncs_k_head_for_each_explicit_file_before_reconcile(
        self, connection_cls_mock: Mock
    ):
        # The workspace's have-list can be stale relative to depot HEAD
        # (create_workspace only syncs to PerforceChangelistNumber; nothing
        # re-syncs after our own aggregate submits). Reconcile then refuses
        # to open files that are "in depot but not in have," so per-task
        # shelves come back empty. `submit_renders` fixes this by running
        # `p4 sync -k <path>@head` on each explicit file — metadata-only,
        # aligns have with depot without touching workspace bytes.
        p4_mock = self._make_p4_mock_for_submit()
        connection_cls_mock.return_value.p4 = p4_mock

        app.submit_renders(
            unreal_project_name="MyProject",
            output_directories=[],
            explicit_files=[
                "C:/ws/MyProject/Saved/MovieRenders/Main_SEQ.0001.jpeg",
                "C:/ws/MyProject/Saved/MovieRenders/Main_SEQ.0002.jpeg",
            ],
            mode="shelve",
        )

        run_calls = [c.args for c in p4_mock.run.call_args_list]
        sync_k_calls = [c for c in run_calls if c[0] == "sync" and len(c) > 1 and c[1] == "-k"]
        assert len(sync_k_calls) == 2, f"expected one sync -k per explicit file, got {sync_k_calls}"
        assert sync_k_calls[0][2].endswith("Main_SEQ.0001.jpeg#head")
        assert sync_k_calls[1][2].endswith("Main_SEQ.0002.jpeg#head")

        # AND sync -k runs before reconcile (order matters — reconcile needs
        # the aligned have-list to decide correctly).
        cmd_order = [c[0] for c in run_calls]
        first_sync_k_idx = next(
            i for i, c in enumerate(run_calls) if c[0] == "sync" and len(c) > 1 and c[1] == "-k"
        )
        first_reconcile_idx = cmd_order.index("reconcile")
        assert (
            first_sync_k_idx < first_reconcile_idx
        ), f"sync -k must precede reconcile; got {cmd_order}"

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_skips_sync_k_for_directory_recursion_callers(
        self, connection_cls_mock: Mock
    ):
        # When called with output_directories (no explicit_files), we don't
        # sync -k — the untargeted glob could touch files we shouldn't.
        p4_mock = self._make_p4_mock_for_submit()
        connection_cls_mock.return_value.p4 = p4_mock

        app.submit_renders(
            unreal_project_name="MyProject",
            output_directories=["C:/ws/MyProject/Saved/MovieRenders"],
            mode="shelve",
        )

        run_calls = [c.args for c in p4_mock.run.call_args_list]
        sync_k_calls = [c for c in run_calls if c[0] == "sync" and len(c) > 1 and c[1] == "-k"]
        assert (
            sync_k_calls == []
        ), f"unexpected sync -k when using output_directories: {sync_k_calls}"

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_scopes_reopen_and_revert_to_explicit_files(
        self, connection_cls_mock: Mock
    ):
        # `reopen -c <cl> //...` was the smoking gun for p4test7-10: it swept
        # stale opens from prior tasks into the new CL, causing each task
        # to shelve every leftover file. When called with explicit_files
        # both `reopen` and the `revert -a` cleanup must be scoped to just
        # this task's file list so we can't inherit unrelated state.
        p4_mock = self._make_p4_mock_for_submit()
        connection_cls_mock.return_value.p4 = p4_mock

        explicit = [
            "C:/ws/MyProject/Saved/MovieRenders/Main_SEQ.0001.jpeg",
            "C:/ws/MyProject/Saved/MovieRenders/Main_SEQ.0002.jpeg",
        ]
        app.submit_renders(
            unreal_project_name="MyProject",
            output_directories=[],
            explicit_files=explicit,
            mode="shelve",
        )

        run_calls = [c.args for c in p4_mock.run.call_args_list]
        reopen_calls = [c for c in run_calls if c[0] == "reopen"]
        assert len(reopen_calls) == 1
        # `reopen -c <cl> <file> <file> ...` — args past -c/<cl> are the
        # explicit file list, and NOT `//...`.
        reopen_args = reopen_calls[0]
        assert reopen_args[1] == "-c"
        # cl_number is at index 2; targets start at index 3
        assert (
            "//..." not in reopen_args[3:]
        ), f"reopen must be scoped to explicit files, saw //... in {reopen_args}"
        assert set(reopen_args[3:]) == {p.replace("\\", "/") for p in explicit}

        revert_a_calls = [c for c in run_calls if c[0] == "revert" and "-a" in c]
        assert len(revert_a_calls) == 1
        revert_a_args = revert_a_calls[0]
        # revert -a -c <cl> <file> <file> — same shape as reopen.
        assert (
            "//..." not in revert_a_args
        ), f"revert -a must be scoped to explicit files, saw //... in {revert_a_args}"

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_reverts_stale_opens_before_reconcile(self, connection_cls_mock: Mock):
        # If a prior task crashed leaving files opened in default, this task's
        # reconcile would ignore them (already opened) and eventually `reopen`
        # would sweep them into our new CL. Guard against that by running
        # `revert -k <explicit_files>` first — clears any stale opens on the
        # exact paths we're about to touch, without disturbing the working files.
        p4_mock = self._make_p4_mock_for_submit()
        connection_cls_mock.return_value.p4 = p4_mock

        explicit = ["C:/ws/foo.png", "C:/ws/bar.png"]
        app.submit_renders(
            unreal_project_name="MyProject",
            output_directories=[],
            explicit_files=explicit,
            mode="shelve",
        )

        run_calls = [c.args for c in p4_mock.run.call_args_list]
        # First revert call must be the pre-reconcile `revert -k <files>`.
        revert_calls = [c for c in run_calls if c[0] == "revert"]
        assert len(revert_calls) >= 1
        pre_revert = revert_calls[0]
        assert pre_revert[1] == "-k"
        assert set(pre_revert[2:]) == {p.replace("\\", "/") for p in explicit}
        # And it happens before reconcile.
        cmd_order = [c[0] for c in run_calls]
        pre_revert_idx = cmd_order.index("revert")
        reconcile_idx = cmd_order.index("reconcile")
        assert (
            pre_revert_idx < reconcile_idx
        ), f"pre-reconcile revert -k must precede reconcile; got {cmd_order}"

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_submit_renders_tolerates_sync_k_no_such_file(self, connection_cls_mock: Mock):
        # sync -k raises "no such file(s)" for files not yet in depot. That's
        # the "new file" case — benign; reconcile -a will pick it up.
        p4_mock = MagicMock()

        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else None
            if cmd == "sync" and len(args) > 1 and args[1] == "-k":
                raise RuntimeError(f"{args[2]} - no such file(s).")
            if cmd == "reconcile":
                return [{"depotFile": "//depot/A/foo.png"}]
            if cmd == "opened":
                return [{"depotFile": "//depot/A/foo.png"}]
            return []

        p4_mock.run.side_effect = run_side_effect
        p4_mock.fetch_change.return_value = {"Change": "new", "Description": ""}
        p4_mock.save_change.return_value = ["Change 42 created."]
        connection_cls_mock.return_value.p4 = p4_mock

        # Should NOT raise despite sync -k failing on every file.
        result = app.submit_renders(
            unreal_project_name="MyProject",
            output_directories=[],
            explicit_files=["C:/ws/foo.png"],
            mode="shelve",
        )
        assert result == 42

    # ---- assemble_shelves ---------------------------------------------------

    def _make_p4_mock_for_assemble(
        self,
        job_id="job-abc",
        task_shelved_cls=(101, 102, 103),
        aggregate_cl="500",
        opened_after_unshelve=None,
    ):
        """
        Build a P4 mock for assemble_shelves. Returns shelved-CL rows tagged
        with the marker for `job_id`, plus one unrelated shelve to prove the
        filter works.
        """
        from deadline.unreal_perforce_utils.app import DEADLINE_CL_MARKER_PREFIX

        marker = f"{DEADLINE_CL_MARKER_PREFIX}{job_id}"
        p4_mock = MagicMock()
        p4_mock.user = "renderbot"
        # Rows: matching + one unrelated shelve
        rows = [
            {"change": str(cl), "desc": f"{marker}\nDeadline Cloud render output\n"}
            for cl in task_shelved_cls
        ]
        rows.append({"change": "999", "desc": "Some other unrelated shelve"})

        # For opened check: default to non-empty (unshelve worked)
        if opened_after_unshelve is None:
            opened_after_unshelve = [{"depotFile": f"//depot/frame_{i}.png"} for i in range(3)]

        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else None
            if cmd == "changes":
                return rows
            if cmd == "opened":
                return opened_after_unshelve
            return []

        p4_mock.run.side_effect = run_side_effect
        p4_mock.fetch_change.return_value = {"Change": "new", "Description": ""}
        p4_mock.save_change.return_value = [f"Change {aggregate_cl} created."]
        return p4_mock

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_assemble_shelves_discovers_and_aggregates_by_job_marker(
        self, connection_cls_mock: Mock
    ):
        # GIVEN three task shelves for our job + one unrelated shelve
        p4_mock = self._make_p4_mock_for_assemble(
            job_id="job-abc",
            task_shelved_cls=(101, 102, 103),
            aggregate_cl="500",
        )
        connection_cls_mock.return_value.p4 = p4_mock

        # WHEN
        result = app.assemble_shelves(
            unreal_project_name="MyProject",
            deadline_job_id="job-abc",
            final_mode="submit",
        )

        # THEN — final aggregate CL got submitted (not shelved)
        assert result == 500
        run_calls = [c.args for c in p4_mock.run.call_args_list]
        cmds = [c[0] for c in run_calls]
        assert "changes" in cmds  # discovery
        # Three unshelves for the three matching task CLs.
        # `-f` is required because each per-task shelve leaves its rendered
        # frames on disk as writable/untracked; without -f, unshelve refuses
        # to clobber them and the aggregate ends up empty.
        unshelves = [c for c in run_calls if c[0] == "unshelve"]
        assert len(unshelves) == 3
        for c in unshelves:
            # -f -s <src_cl> -c <aggregate_cl>
            assert c[1] == "-f", f"unshelve missing -f (force); saw {c}"
            assert c[2] == "-s"
            assert int(c[3]) in (101, 102, 103)
            assert c[4] == "-c"
            assert c[5] == "500"
        # And the unrelated shelve (999) was NOT unshelved
        assert not any(c for c in unshelves if len(c) > 3 and c[3] == "999")
        # Source shelves cleaned up
        source_shelve_deletes = [
            c for c in run_calls if c[0] == "shelve" and len(c) > 2 and c[1] == "-d"
        ]
        assert len(source_shelve_deletes) == 3
        # And the empty source CLs themselves were deleted (`change -d <cl>`)
        source_cl_deletes = [
            c
            for c in run_calls
            if c[0] == "change" and len(c) > 2 and c[1] == "-d" and c[2] in ("101", "102", "103")
        ]
        assert (
            len(source_cl_deletes) == 3
        ), f"expected 3 source CL deletions, got {source_cl_deletes}"
        # And the aggregate was submitted, not shelved
        submits = [c for c in run_calls if c[0] == "submit"]
        assert len(submits) == 1

        # And `Files` was explicitly cleared on save — otherwise stale opens
        # in the default CL would ride along into the aggregate CL via
        # fetch_change's auto-populate. Belt-and-suspenders against
        # over-shelving foreign files.
        saved_change = p4_mock.save_change.call_args[0][0]
        assert saved_change.get("Files") == []

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_assemble_shelves_shelve_final_mode_shelves_aggregate_not_submits(
        self, connection_cls_mock: Mock, caplog
    ):
        p4_mock = self._make_p4_mock_for_assemble(
            job_id="job-abc",
            task_shelved_cls=(101, 102),
            aggregate_cl="777",
        )
        connection_cls_mock.return_value.p4 = p4_mock

        import logging

        with caplog.at_level(logging.INFO):
            result = app.assemble_shelves(
                unreal_project_name="MyProject",
                deadline_job_id="job-abc",
                final_mode="shelve",
            )

        assert result == 777
        run_calls = [c.args for c in p4_mock.run.call_args_list]
        # Aggregate CL was shelved (final `p4 shelve -c <aggregate_cl>`), not submitted
        assert not any(c[0] == "submit" for c in run_calls)
        aggregate_shelves = [
            c
            for c in run_calls
            if c[0] == "shelve" and len(c) > 1 and c[1] == "-c" and c[2] == "777"
        ]
        assert len(aggregate_shelves) == 1
        # Emits SHELVED_CL for observability / downstream tooling
        assert "openjd_env: SHELVED_CL=777" in caplog.text

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_assemble_shelves_raises_when_no_shelves_found(self, connection_cls_mock: Mock):
        # GIVEN a job with zero matching shelves
        p4_mock = self._make_p4_mock_for_assemble(
            job_id="job-abc",
            task_shelved_cls=(),  # no matches
        )
        connection_cls_mock.return_value.p4 = p4_mock

        # WHEN / THEN — must fail loudly. Silent success = renders vanished.
        with pytest.raises(RuntimeError, match="no shelved CLs found"):
            app.assemble_shelves(
                unreal_project_name="MyProject",
                deadline_job_id="job-abc",
                final_mode="submit",
            )

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_assemble_shelves_continues_on_partial_unshelve_failure(
        self, connection_cls_mock: Mock, caplog
    ):
        # GIVEN one unshelve of the 3 task shelves fails, but the other two work
        from deadline.unreal_perforce_utils.app import DEADLINE_CL_MARKER_PREFIX

        marker = f"{DEADLINE_CL_MARKER_PREFIX}job-abc"
        p4_mock = MagicMock()
        p4_mock.user = "renderbot"
        rows = [
            {"change": "101", "desc": f"{marker}\ndesc"},
            {"change": "102", "desc": f"{marker}\ndesc"},
            {"change": "103", "desc": f"{marker}\ndesc"},
        ]

        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else None
            if cmd == "changes":
                return rows
            # unshelve now runs `-f -s <src> -c <agg>` so the src CL is at args[3]
            if cmd == "unshelve" and len(args) >= 4 and args[3] == "102":
                raise RuntimeError("File(s) already opened for edit — merge conflict")
            if cmd == "opened":
                return [{"depotFile": "//depot/foo.png"}]
            return []

        p4_mock.run.side_effect = run_side_effect
        p4_mock.fetch_change.return_value = {"Change": "new", "Description": ""}
        p4_mock.save_change.return_value = ["Change 500 created."]
        connection_cls_mock.return_value.p4 = p4_mock

        import logging

        # _diag routes through logging.getLogger(__name__) at INFO level so
        # events surface in the adaptor's captured output. Match that level.
        with caplog.at_level(logging.INFO, logger="deadline.unreal_perforce_utils.app"):
            result = app.assemble_shelves(
                unreal_project_name="MyProject",
                deadline_job_id="job-abc",
                final_mode="submit",
            )

        # THEN — proceeds with the shelves that worked; failed one is logged
        assert result == 500
        assert "unshelve -f -s 102" in caplog.text
        assert "could not be aggregated" in caplog.text

    @patch("deadline.unreal_perforce_utils.app.perforce.PerforceConnection")
    def test_assemble_shelves_raises_when_all_unshelves_fail(self, connection_cls_mock: Mock):
        # GIVEN every unshelve fails → aggregate CL is empty
        from deadline.unreal_perforce_utils.app import DEADLINE_CL_MARKER_PREFIX

        marker = f"{DEADLINE_CL_MARKER_PREFIX}job-abc"
        p4_mock = MagicMock()
        p4_mock.user = "renderbot"

        def run_side_effect(*args, **kwargs):
            cmd = args[0] if args else None
            if cmd == "changes":
                return [{"change": "101", "desc": f"{marker}\ndesc"}]
            if cmd == "unshelve":
                raise RuntimeError("bang")
            if cmd == "opened":
                return []  # empty aggregate CL
            return []

        p4_mock.run.side_effect = run_side_effect
        p4_mock.fetch_change.return_value = {"Change": "new", "Description": ""}
        p4_mock.save_change.return_value = ["Change 500 created."]
        connection_cls_mock.return_value.p4 = p4_mock

        with pytest.raises(RuntimeError, match="aggregate CL was empty"):
            app.assemble_shelves(
                unreal_project_name="MyProject",
                deadline_job_id="job-abc",
                final_mode="submit",
            )

    def test_assemble_shelves_invalid_final_mode_raises(self):
        with pytest.raises(ValueError, match="'submit' or 'shelve'"):
            app.assemble_shelves(
                unreal_project_name="MyProject",
                deadline_job_id="job-abc",
                final_mode="not-a-mode",
            )

    def test_assemble_shelves_missing_job_id_raises(self):
        with pytest.raises(ValueError, match="deadline_job_id is required"):
            app.assemble_shelves(
                unreal_project_name="MyProject",
                deadline_job_id="",
                final_mode="submit",
            )

    def test_build_changelist_description_prepends_marker_when_job_id_given(self):
        from deadline.unreal_perforce_utils.app import (
            _build_changelist_description,
            DEADLINE_CL_MARKER_PREFIX,
        )

        # Ensure DEADLINE_JOB_ID env var doesn't leak into this test
        with patch.dict(os.environ, {}, clear=True):
            desc = _build_changelist_description(
                job_name="job-abc",
                extra_description=None,
                deadline_job_id="job-abc",
            )
        # First line is the machine-parseable marker
        assert desc.splitlines()[0] == f"{DEADLINE_CL_MARKER_PREFIX}job-abc"
        # Human-readable header follows
        assert desc.splitlines()[1] == "Deadline Cloud render output"

    def test_build_changelist_description_omits_marker_when_no_job_id(self):
        from deadline.unreal_perforce_utils.app import (
            _build_changelist_description,
            DEADLINE_CL_MARKER_PREFIX,
        )

        with patch.dict(os.environ, {}, clear=True):
            desc = _build_changelist_description(
                job_name=None,
                extra_description=None,
                deadline_job_id=None,
            )
        assert not desc.startswith(DEADLINE_CL_MARKER_PREFIX)
        assert desc.splitlines()[0] == "Deadline Cloud render output"

    def test_build_changelist_description_does_not_fall_back_to_env_var(self):
        """
        Regression: `deadline_job_id=None` must NOT fall back to
        DEADLINE_JOB_ID env var. Callers that want the aggregate CL to
        stay invisible to task-shelve discovery rely on this: an env-var
        fallback would re-stamp the aggregate with the task-shelve marker
        for the current job (since assemble_shelves runs on a worker where
        DEADLINE_JOB_ID is set to that job).
        """
        from deadline.unreal_perforce_utils.app import (
            _build_changelist_description,
            DEADLINE_CL_MARKER_PREFIX,
        )

        with patch.dict(os.environ, {"DEADLINE_JOB_ID": "job-from-env"}, clear=True):
            desc = _build_changelist_description(
                job_name=None,
                extra_description=None,
                deadline_job_id=None,
            )
        # First line MUST NOT be the task-shelve marker with the env-var
        # job ID — otherwise the aggregate CL would be picked up by
        # `_find_shelved_cls_for_job` on a retry.
        assert not desc.splitlines()[0].startswith(DEADLINE_CL_MARKER_PREFIX)

    def test_build_changelist_description_stamps_aggregate_marker_when_requested(self):
        """
        The aggregate CL is stamped with a distinct prefix so
        `_find_shelved_cls_for_job` (which filters on the task prefix
        only) cannot mistake an aggregate for a task shelve on a retry.
        """
        from deadline.unreal_perforce_utils.app import (
            _build_changelist_description,
            DEADLINE_CL_AGGREGATE_MARKER_PREFIX,
            DEADLINE_CL_MARKER_PREFIX,
        )

        with patch.dict(os.environ, {}, clear=True):
            desc = _build_changelist_description(
                job_name=None,
                extra_description=None,
                deadline_job_id="job-abc",
                marker_prefix=DEADLINE_CL_AGGREGATE_MARKER_PREFIX,
            )
        assert desc.splitlines()[0] == f"{DEADLINE_CL_AGGREGATE_MARKER_PREFIX}job-abc"
        # And critically, does NOT start with the task-shelve prefix.
        assert not desc.splitlines()[0].startswith(DEADLINE_CL_MARKER_PREFIX)

    def test_find_shelved_cls_for_job_ignores_aggregate_markers(self):
        """
        `_find_shelved_cls_for_job` must return only task shelves, never
        aggregate shelves — even when both carry the same job ID. This
        is the retry-safety property.
        """
        from deadline.unreal_perforce_utils.app import (
            _find_shelved_cls_for_job,
            DEADLINE_CL_AGGREGATE_MARKER_PREFIX,
            DEADLINE_CL_MARKER_PREFIX,
        )

        p4_mock = MagicMock()
        p4_mock.user = "renderbot"
        p4_mock.run.return_value = [
            # Two task shelves.
            {"change": "101", "desc": f"{DEADLINE_CL_MARKER_PREFIX}job-abc\nDeadline Cloud"},
            {"change": "102", "desc": f"{DEADLINE_CL_MARKER_PREFIX}job-abc\nDeadline Cloud"},
            # And a previously-created aggregate shelve for the same job.
            {
                "change": "200",
                "desc": f"{DEADLINE_CL_AGGREGATE_MARKER_PREFIX}job-abc\nDeadline Cloud",
            },
        ]
        connection = MagicMock()
        connection.p4 = p4_mock

        result = _find_shelved_cls_for_job(connection, deadline_job_id="job-abc")

        # Only the two task shelves — aggregate 200 must be excluded.
        assert result == [101, 102]
