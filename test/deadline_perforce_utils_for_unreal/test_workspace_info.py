# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from deadline.unreal_perforce_utils.app import (
    WorkspaceInfoFile,
    _stream_path_to_name_component,
    create_perforce_workspace_from_template,
    merge_view_mappings,
)


class TestWorkspaceInfoFileProperties:
    """Tests for WorkspaceInfoFile and merge_view_mappings."""

    @pytest.mark.parametrize(
        "stream_workspaces, view_workspace",
        [
            ({}, None),
            ({"//Stream/Main": "ws_1"}, None),
            ({}, "ws_2"),
            (
                {"//Stream/Main": "ws_1", "//Stream/Dev": "ws_2"},
                "ws_shared",
            ),
            ({"//a/b": "x", "//c/d": "y", "//e/f": "z"}, "w_view"),
        ],
    )
    def test_serialization_round_trip(self, stream_workspaces, view_workspace, tmp_path):
        """
        Property 1: WorkspaceInfoFile serialization round-trip.
        Validates: Requirements 1.5, 7.3
        """
        original = WorkspaceInfoFile(
            stream_workspaces=stream_workspaces,
            view_workspace=view_workspace,
        )

        file_path = str(tmp_path / "workspace_info.json")
        original.save(file_path)
        loaded = WorkspaceInfoFile.load(file_path)

        assert loaded.stream_workspaces == original.stream_workspaces
        assert loaded.view_workspace == original.view_workspace

    @pytest.mark.parametrize(
        "stream_workspaces, view_workspace",
        [
            ({}, None),
            ({"//S/M": "ws1"}, "ws2"),
            (
                {"//a/b": "x", "//c/d": "y"},
                "w_shared",
            ),
        ],
    )
    def test_serialized_schema_invariant(self, stream_workspaces, view_workspace, tmp_path):
        """
        Property 2: Serialized schema invariant.
        Validates: Requirements 1.2, 7.1, 7.2
        """
        info = WorkspaceInfoFile(
            stream_workspaces=stream_workspaces,
            view_workspace=view_workspace,
        )

        file_path_1 = str(tmp_path / "workspace_info_1.json")
        info.save(file_path_1)

        with open(file_path_1, "r") as f:
            raw_content_1 = f.read()
        parsed = json.loads(raw_content_1)

        assert set(parsed.keys()) == {"stream_workspaces", "view_workspace"}
        assert isinstance(parsed["stream_workspaces"], dict)
        for k, v in parsed["stream_workspaces"].items():
            assert isinstance(k, str)
            assert isinstance(v, str)
        assert parsed["view_workspace"] is None or isinstance(parsed["view_workspace"], str)

        # Deterministic: serialize twice, get identical output
        file_path_2 = str(tmp_path / "workspace_info_2.json")
        info.save(file_path_2)
        with open(file_path_2, "r") as f:
            raw_content_2 = f.read()
        assert raw_content_1 == raw_content_2

    @pytest.mark.parametrize(
        "stream_workspaces, lookup_key",
        [
            ({"//MeerkatDemo/Mainline": "ws_meerkat"}, "//MeerkatDemo/Mainline"),
            (
                {"//A/B": "ws_a", "//C/D": "ws_c", "//E/F": "ws_e"},
                "//C/D",
            ),
        ],
    )
    def test_stream_workspace_reuse_returns_registered_name(self, stream_workspaces, lookup_key):
        """
        Property 3: Stream workspace reuse returns registered name.
        Validates: Requirements 2.1, 2.2
        """
        info = WorkspaceInfoFile(stream_workspaces=stream_workspaces)
        assert info.lookup_stream(lookup_key) == stream_workspaces[lookup_key]

    def test_stream_workspace_lookup_missing_returns_none(self):
        info = WorkspaceInfoFile(stream_workspaces={"//A/B": "ws"})
        assert info.lookup_stream("//missing") is None

    @pytest.mark.parametrize(
        "view_workspace",
        [
            "ws_meerkat",
            "ws_shared_view",
        ],
    )
    def test_view_workspace_reuse_returns_registered_name(self, view_workspace):
        """
        Property 4: View workspace reuse returns registered name.
        Validates: Requirements 3.1, 3.2
        """
        info = WorkspaceInfoFile(view_workspace=view_workspace)
        assert info.lookup_view() == view_workspace

    def test_view_workspace_lookup_missing_returns_none(self):
        info = WorkspaceInfoFile()
        assert info.lookup_view() is None

    @pytest.mark.parametrize(
        "initial_streams, initial_view, new_stream_key, new_stream_val, new_view_val",
        [
            ({}, None, "//New/Stream", "ws_new_s", "ws_new_v"),
            (
                {"//Existing/S": "ws_e"},
                "ws_ep",
                "//Brand/New",
                "ws_bn",
                "ws_bnp",
            ),
        ],
    )
    def test_registry_updated_after_new_workspace_creation(
        self,
        initial_streams,
        initial_view,
        new_stream_key,
        new_stream_val,
        new_view_val,
    ):
        """
        Property 5: Registry updated after new workspace creation.
        Validates: Requirements 1.4, 2.3, 3.3
        """
        info = WorkspaceInfoFile(
            stream_workspaces=dict(initial_streams),
            view_workspace=initial_view,
        )

        info.register_stream(new_stream_key, new_stream_val)
        assert info.lookup_stream(new_stream_key) == new_stream_val

        info.register_view(new_view_val)
        assert info.lookup_view() == new_view_val

    @pytest.mark.parametrize(
        "existing_views, new_views",
        [
            ([], []),
            (["//A/... //ws/..."], []),
            ([], ["//B/... //ws/..."]),
            (
                ["//A/... //ws/..."],
                ["//B/... //ws/..."],
            ),
            (
                ["//A/... //ws/...", "//B/... //ws/..."],
                ["//B/... //ws/...", "//C/... //ws/..."],
            ),
        ],
    )
    def test_view_merge_appends_new_mappings(self, existing_views, new_views):
        """
        Property 6: View merge appends new mappings.
        Validates: Requirements 4.2
        """
        result = merge_view_mappings(existing_views, new_views)
        for entry in existing_views:
            assert entry in result
        for entry in new_views:
            assert entry in result

    @pytest.mark.parametrize(
        "views",
        [
            [],
            ["//A/... //ws/..."],
            ["//A/... //ws/...", "//B/... //ws/..."],
            ["//A/... //ws/...", "//B/... //ws/...", "//C/... //ws/..."],
        ],
    )
    def test_view_merge_idempotence(self, views):
        """
        Property 7: View merge idempotence.
        Validates: Requirements 4.3
        """
        result = merge_view_mappings(views, views)
        assert result == views

    @pytest.mark.parametrize(
        "stream_path, expected_readable, expected_suffix_len",
        [
            ("//MeerkatDemo/Mainline", "MeerkatDemo_Mainline", 4),
            ("//MeerkatDemo/Dev", "MeerkatDemo_Dev", 4),
            ("//A/B/C", "A_B_C", 4),
        ],
    )
    def test_stream_path_to_name_component(
        self, stream_path, expected_readable, expected_suffix_len
    ):
        """Stream paths are converted to readable name components with a hash suffix."""
        result = _stream_path_to_name_component(stream_path)
        # Should start with the readable portion
        assert result.startswith(expected_readable + "_")
        # Should end with a short hex hash
        suffix = result[len(expected_readable) + 1 :]
        assert len(suffix) == expected_suffix_len
        int(suffix, 16)  # Should be valid hex

    def test_stream_path_to_name_component_different_paths_differ(self):
        """Different stream paths produce different name components."""
        a = _stream_path_to_name_component("//MeerkatDemo/Mainline")
        b = _stream_path_to_name_component("//MeerkatDemo/Dev")
        assert a != b

    def test_stream_path_to_name_component_ambiguous_paths_differ(self):
        """Paths that look the same after slash replacement are disambiguated by hash."""
        a = _stream_path_to_name_component("//A_B/C")
        b = _stream_path_to_name_component("//A/B_C")
        # Both have readable portion A_B_C but different hash suffixes
        assert a != b


class TestCreateWorkspaceFromTemplatePersistence:
    """Unit tests for reusable workspace behavior in create_perforce_workspace_from_template."""

    # --- Task 3.2: Fallback-root (~/Perforce) applies persistent semantics ---
    # When P4_CLIENTS_ROOT_DIRECTORY is unset, `create_perforce_workspace_from_template`
    # falls back to ~/Perforce and treats the workspace as reusable (same code path
    # as when the env var is set). We patch `_default_clients_root` to a tmp path
    # so tests don't touch the real user home.

    @patch("deadline.unreal_perforce_utils.app.perforce")
    @patch("deadline.unreal_perforce_utils.app.get_workspace_name", return_value="user_host_proj")
    def test_no_clients_root_creates_new_workspace(self, mock_get_name, mock_perforce, tmp_path):
        """When P4_CLIENTS_ROOT_DIRECTORY is not set, ~/Perforce fallback is used."""
        mock_client = MagicMock()
        mock_perforce.PerforceClient.return_value = mock_client
        mock_perforce.PerforceConnection.return_value = MagicMock()

        template = {
            "Client": "{workspace_name}",
            "Root": "D:/workspace",
            "Stream": "//MeerkatDemo/Mainline",
        }

        with (
            patch.dict(os.environ, {}, clear=True),
            patch(
                "deadline.unreal_perforce_utils.app._default_clients_root",
                return_value=str(tmp_path / "Perforce"),
            ),
        ):
            result = create_perforce_workspace_from_template(template, "MeerkatDemo")

        # For stream workspaces the fallback path uses the stream-derived
        # workspace-name component, not the raw project name.
        mock_get_name.assert_called_once()
        mock_perforce.PerforceClient.assert_called_once()
        mock_client.save.assert_called_once()
        assert result is mock_client

    @patch("deadline.unreal_perforce_utils.app.perforce")
    @patch("deadline.unreal_perforce_utils.app.get_workspace_name", return_value="user_host_proj")
    def test_no_clients_root_uses_home_perforce_fallback(
        self, mock_get_name, mock_perforce, tmp_path
    ):
        """Fallback root is <clients_root>/<workspace_name>."""
        mock_perforce.PerforceClient.return_value = MagicMock()
        mock_perforce.PerforceConnection.return_value = MagicMock()

        template = {
            "Client": "{workspace_name}",
            "Root": "D:/workspace",
            "Stream": "//MeerkatDemo/Mainline",
        }

        fake_home_perforce = str(tmp_path / "Perforce")
        with (
            patch.dict(os.environ, {}, clear=True),
            patch(
                "deadline.unreal_perforce_utils.app._default_clients_root",
                return_value=fake_home_perforce,
            ),
        ):
            create_perforce_workspace_from_template(template, "MeerkatDemo")

        expected_root = f"{fake_home_perforce}/user_host_proj".replace("\\", "/")
        actual_root = str(template["Root"]).replace("\\", "/")
        assert actual_root == expected_root

    # --- Task 3.3: Stream workspace reuse flow ---

    @patch("deadline.unreal_perforce_utils.app.perforce")
    @patch("deadline.unreal_perforce_utils.app.get_workspace_name", return_value="new_ws_name")
    def test_stream_reuse_existing_workspace(self, mock_get_name, mock_perforce, tmp_path):
        """When stream path is in registry, reuse existing workspace name."""
        mock_client = MagicMock()
        mock_perforce.PerforceClient.return_value = mock_client
        mock_perforce.PerforceConnection.return_value = MagicMock()

        # Pre-populate registry
        info = WorkspaceInfoFile(
            stream_workspaces={"//MeerkatDemo/Mainline": "existing_ws"},
        )
        info_path = str(tmp_path / "workspace_info.json")
        info.save(info_path)

        template = {
            "Client": "{workspace_name}",
            "Root": "D:/workspace",
            "Stream": "//MeerkatDemo/Mainline",
        }

        with patch.dict(os.environ, {"P4_CLIENTS_ROOT_DIRECTORY": str(tmp_path)}, clear=True):
            create_perforce_workspace_from_template(template, "MeerkatDemo")

        # Should NOT call get_workspace_name since we're reusing
        mock_get_name.assert_not_called()
        # PerforceClient should be created with the existing workspace name
        call_kwargs = mock_perforce.PerforceClient.call_args
        assert call_kwargs[1]["name"] == "existing_ws"
        mock_client.save.assert_called_once()

    @patch("deadline.unreal_perforce_utils.app.perforce")
    @patch("deadline.unreal_perforce_utils.app.get_workspace_name", return_value="new_ws_name")
    def test_stream_new_workspace_registered(self, mock_get_name, mock_perforce, tmp_path):
        """When stream path is NOT in registry, create new workspace and register it."""
        mock_client = MagicMock()
        mock_perforce.PerforceClient.return_value = mock_client
        mock_perforce.PerforceConnection.return_value = MagicMock()

        # Empty registry
        info = WorkspaceInfoFile()
        info_path = str(tmp_path / "workspace_info.json")
        info.save(info_path)

        template = {
            "Client": "{workspace_name}",
            "Root": "D:/workspace",
            "Stream": "//MeerkatDemo/Mainline",
        }

        with patch.dict(os.environ, {"P4_CLIENTS_ROOT_DIRECTORY": str(tmp_path)}, clear=True):
            create_perforce_workspace_from_template(template, "MeerkatDemo")

        # When reusing workspaces, stream workspaces use stream-derived name component
        expected_component = _stream_path_to_name_component("//MeerkatDemo/Mainline")
        mock_get_name.assert_called_once_with(project_name=expected_component)

        # Verify registry was updated
        loaded = WorkspaceInfoFile.load(info_path)
        assert loaded.lookup_stream("//MeerkatDemo/Mainline") == "new_ws_name"

    # --- Task 3.4: View workspace reuse flow ---

    @patch("deadline.unreal_perforce_utils.app.perforce")
    @patch("deadline.unreal_perforce_utils.app.get_workspace_name", return_value="new_ws_name")
    def test_view_reuse_existing_workspace_merges_views(
        self, mock_get_name, mock_perforce, tmp_path
    ):
        """When view workspace exists in registry, reuse workspace, fetch existing spec, merge views."""
        mock_connection = MagicMock()
        mock_perforce.PerforceConnection.return_value = mock_connection
        # Simulate existing spec on P4 server with one view
        mock_connection.p4.fetch_client.return_value = {
            "Client": "existing_ws",
            "View": ["//MeerkatDemo/Mainline/... //existing_ws/..."],
        }
        mock_client = MagicMock()
        mock_perforce.PerforceClient.return_value = mock_client

        # Pre-populate registry with single view workspace
        info = WorkspaceInfoFile(
            view_workspace="existing_ws",
        )
        info_path = str(tmp_path / "workspace_info.json")
        info.save(info_path)

        template = {
            "Client": "{workspace_name}",
            "Root": "D:/workspace",
            "View": [
                "//MeerkatDemo/Mainline/... //{workspace_name}/...",
                "//Plugins/Mainline/... //{workspace_name}/Plugins/...",
            ],
        }

        with patch.dict(os.environ, {"P4_CLIENTS_ROOT_DIRECTORY": str(tmp_path)}, clear=True):
            create_perforce_workspace_from_template(template, "MeerkatDemo")

        mock_get_name.assert_not_called()
        # fetch_client should have been called to get existing spec
        mock_connection.p4.fetch_client.assert_called_with("existing_ws")
        # The merged views should contain both existing and new
        call_kwargs = mock_perforce.PerforceClient.call_args[1]
        spec_views = call_kwargs["specification"]["View"]
        assert "//MeerkatDemo/Mainline/... //existing_ws/..." in spec_views
        assert "//Plugins/Mainline/... //existing_ws/Plugins/..." in spec_views

    @patch("deadline.unreal_perforce_utils.app.perforce")
    @patch("deadline.unreal_perforce_utils.app.get_workspace_name", return_value="new_ws_name")
    def test_view_new_workspace_registered(self, mock_get_name, mock_perforce, tmp_path):
        """When no view workspace in registry, create new workspace and register it."""
        mock_client = MagicMock()
        mock_perforce.PerforceClient.return_value = mock_client
        mock_perforce.PerforceConnection.return_value = MagicMock()

        info = WorkspaceInfoFile()
        info_path = str(tmp_path / "workspace_info.json")
        info.save(info_path)

        template = {
            "Client": "{workspace_name}",
            "Root": "D:/workspace",
            "View": ["//MeerkatDemo/Mainline/... //{workspace_name}/..."],
        }

        with patch.dict(os.environ, {"P4_CLIENTS_ROOT_DIRECTORY": str(tmp_path)}, clear=True):
            create_perforce_workspace_from_template(template, "MeerkatDemo")

        mock_get_name.assert_called_once()
        loaded = WorkspaceInfoFile.load(info_path)
        assert loaded.lookup_view() == "new_ws_name"

    # --- Task 3.5: Error handling ---

    @pytest.mark.parametrize(
        "bad_data",
        [
            {"stream_workspaces": "not_a_dict", "view_workspace": None},
            {"stream_workspaces": {"ok": 123}, "view_workspace": None},
            {"stream_workspaces": {}, "view_workspace": 42},
        ],
    )
    def test_load_invalid_types_logs_warning_returns_empty(self, bad_data, tmp_path):
        """WorkspaceInfoFile.load() with valid JSON but wrong types returns empty registry."""
        path = str(tmp_path / "workspace_info.json")
        with open(path, "w") as f:
            json.dump(bad_data, f)

        with patch("deadline.unreal_perforce_utils.app.logger") as mock_logger:
            result = WorkspaceInfoFile.load(path)

        assert result.stream_workspaces == {}
        assert result.view_workspace is None
        mock_logger.warning.assert_called_once()

    def test_load_invalid_json_logs_warning_returns_empty(self, tmp_path):
        """WorkspaceInfoFile.load() with invalid JSON logs warning and returns empty registry."""
        bad_path = str(tmp_path / "workspace_info.json")
        with open(bad_path, "w") as f:
            f.write("not valid json {{{")

        with patch("deadline.unreal_perforce_utils.app.logger") as mock_logger:
            result = WorkspaceInfoFile.load(bad_path)

        assert result.stream_workspaces == {}
        assert result.view_workspace is None
        mock_logger.warning.assert_called_once()

    def test_load_fs_error_logs_warning_returns_empty(self, tmp_path):
        """WorkspaceInfoFile.load() with FS read error logs warning and returns empty registry."""
        with patch("builtins.open", side_effect=PermissionError("access denied")):
            with patch("deadline.unreal_perforce_utils.app.logger") as mock_logger:
                result = WorkspaceInfoFile.load("/some/path/workspace_info.json")

        assert result.stream_workspaces == {}
        assert result.view_workspace is None
        mock_logger.warning.assert_called_once()

    def test_save_fs_error_logs_error_does_not_raise(self, tmp_path):
        """WorkspaceInfoFile.save() with FS write error logs error and does not raise."""
        info = WorkspaceInfoFile(stream_workspaces={"a": "b"})

        with patch("builtins.open", side_effect=PermissionError("access denied")):
            with patch("deadline.unreal_perforce_utils.app.logger") as mock_logger:
                # Should not raise
                info.save("/some/readonly/path/workspace_info.json")

        mock_logger.error.assert_called_once()

    @patch("deadline.unreal_perforce_utils.app.perforce")
    @patch(
        "deadline.unreal_perforce_utils.app.get_workspace_name",
        side_effect=lambda project_name: f"mock_ws_{project_name}",
    )
    def test_different_streams_get_different_workspace_names(
        self, mock_get_name, mock_perforce, tmp_path
    ):
        """Two different stream paths on the same worker produce different workspace names."""
        mock_perforce.PerforceClient.return_value = MagicMock()
        mock_perforce.PerforceConnection.return_value = MagicMock()

        info = WorkspaceInfoFile()
        info_path = str(tmp_path / "workspace_info.json")
        info.save(info_path)

        with patch.dict(os.environ, {"P4_CLIENTS_ROOT_DIRECTORY": str(tmp_path)}, clear=True):
            template1 = {
                "Client": "{workspace_name}",
                "Root": "D:/workspace",
                "Stream": "//MeerkatDemo/Mainline",
            }
            create_perforce_workspace_from_template(template1, "MeerkatDemo")

            template2 = {
                "Client": "{workspace_name}",
                "Root": "D:/workspace",
                "Stream": "//MeerkatDemo/Dev",
            }
            create_perforce_workspace_from_template(template2, "MeerkatDemo")

        loaded = WorkspaceInfoFile.load(info_path)
        mainline_ws = loaded.lookup_stream("//MeerkatDemo/Mainline")
        dev_ws = loaded.lookup_stream("//MeerkatDemo/Dev")
        assert mainline_ws is not None
        assert dev_ws is not None
        assert mainline_ws != dev_ws

    @patch("deadline.unreal_perforce_utils.app.perforce")
    @patch("deadline.unreal_perforce_utils.app.get_workspace_name", return_value="new_ws")
    def test_reusable_workspace_clears_host_field(self, mock_get_name, mock_perforce, tmp_path):
        """When P4_CLIENTS_ROOT_DIRECTORY is set, Host field is cleared for host portability."""
        mock_client = MagicMock()
        mock_perforce.PerforceClient.return_value = mock_client
        mock_perforce.PerforceConnection.return_value = MagicMock()

        template = {
            "Client": "{workspace_name}",
            "Root": "D:/workspace",
            "Stream": "//MeerkatDemo/Mainline",
        }

        with patch.dict(os.environ, {"P4_CLIENTS_ROOT_DIRECTORY": str(tmp_path)}, clear=True):
            create_perforce_workspace_from_template(template, "MeerkatDemo")

        call_kwargs = mock_perforce.PerforceClient.call_args[1]
        assert call_kwargs["specification"]["Host"] == ""

    @patch("deadline.unreal_perforce_utils.app.perforce")
    @patch("deadline.unreal_perforce_utils.app.get_workspace_name", return_value="new_ws")
    def test_no_clients_root_clears_host_field_via_fallback(
        self, mock_get_name, mock_perforce, tmp_path
    ):
        """
        With the ~/Perforce fallback in place, workspaces are always treated as
        reusable, which means Host is cleared to allow the workspace to be used
        from any host. Pins the fallback's persistent semantics.
        """
        mock_client = MagicMock()
        mock_perforce.PerforceClient.return_value = mock_client
        mock_perforce.PerforceConnection.return_value = MagicMock()

        template = {
            "Client": "{workspace_name}",
            "Root": "D:/workspace",
            "Stream": "//MeerkatDemo/Mainline",
        }

        with (
            patch.dict(os.environ, {}, clear=True),
            patch(
                "deadline.unreal_perforce_utils.app._default_clients_root",
                return_value=str(tmp_path / "Perforce"),
            ),
        ):
            create_perforce_workspace_from_template(template, "MeerkatDemo")

        call_kwargs = mock_perforce.PerforceClient.call_args[1]
        assert call_kwargs["specification"]["Host"] == ""
