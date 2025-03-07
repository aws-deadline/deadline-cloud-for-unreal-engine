# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import pytest
from unittest.mock import patch, Mock, MagicMock

from deadline.unreal_perforce_utils import perforce, exceptions


class TestPerforceConnection:

    @patch.object(
        perforce.P4, "connect", MagicMock(side_effect=perforce.P4Exception("NOT CONNECTED"))
    )
    def test_connection_failed(self):
        # GIVEN
        with pytest.raises(exceptions.PerforceConnectionError) as exc_info:
            # WHEN
            perforce.PerforceConnection()

        # THEN
        assert "Could not connect Perforce server" in str(exc_info.value)

    @pytest.mark.parametrize(
        "in_password, env_vars, out_password, login_called",
        [
            (None, {}, "", False),
            (None, {"P4PASSWD": ""}, "", False),
            (None, {"P4PASSWD": "EnvPassword"}, "EnvPassword", True),
            ("InPassword", {}, "InPassword", True),
            ("InPassword", {"P4PASSWD": ""}, "InPassword", True),
            ("InPassword", {"P4PASSWD": "EnvPassword"}, "InPassword", True),
        ],
    )
    @patch.object(perforce.P4, "connect", MagicMock())
    @patch.object(perforce.P4, "run", MagicMock())
    @patch.object(perforce.P4, "run_login", new_callable=MagicMock())
    def test_login(self, run_login_mock, in_password, env_vars, out_password, login_called):
        # GIVEN & WHEN
        with patch.dict(os.environ, env_vars, clear=True):
            conn = perforce.PerforceConnection(password=in_password)

        # THEN
        assert conn.p4.password == out_password

        if login_called:
            run_login_mock.assert_called()
        else:
            run_login_mock.assert_not_called()

    @pytest.mark.parametrize(
        "p4_output, expected_result",
        [
            ({"clientStream": "testClientStream"}, "testClientStream"),
            ({"otherInfo": "otherValue"}, None),
        ],
    )
    @patch.object(perforce.P4, "connect", MagicMock())
    @patch.object(perforce.P4, "run", MagicMock())
    def test_get_stream_path(self, p4_output, expected_result):
        # GIVEN
        perforce_api = perforce.PerforceConnection()

        # WHEN
        with patch.object(perforce_api, "get_info", return_value=p4_output):
            stream_path = perforce_api.get_stream_path()

        # THEN
        assert stream_path == expected_result

    @pytest.mark.parametrize(
        "p4_output, expected_result",
        [
            ({"clientRoot": "path\\to\\root"}, "path/to/root"),
            ({"clientRoot": "path/to/root"}, "path/to/root"),
            ({"otherInfo": "otherValue"}, None),
        ],
    )
    @patch.object(perforce.P4, "connect", MagicMock())
    @patch.object(perforce.P4, "run", MagicMock())
    def test_get_client_root(self, p4_output, expected_result):
        # GIVEN
        perforce_api = perforce.PerforceConnection()

        # WHEN
        with patch.object(perforce_api, "get_info", return_value=p4_output):
            client_root = perforce_api.get_client_root()

        # THEN
        assert client_root == expected_result

    @pytest.mark.parametrize(
        "p4_output, expected_result",
        [([{"change": 10}, {"change": 9}, {"change": 8}], 10), ([], None)],
    )
    @patch.object(perforce.P4, "connect", MagicMock())
    @patch.object(perforce.P4, "run", MagicMock())
    def test_get_latest_changelist_number(self, p4_output, expected_result):
        # GIVEN
        perforce_api = perforce.PerforceConnection()

        # WHEN
        with (
            patch.object(perforce_api, "p4", MagicMock()),
            patch.object(perforce_api.p4, "run", return_value=p4_output),
            patch.object(perforce_api.p4, "client", "MockClient"),
        ):
            changelist = perforce_api.get_latest_changelist_number()

        # THEN
        assert changelist == expected_result


class TestPerforceClient:

    @pytest.mark.parametrize(
        "filepath, changelist, force, stream_path, expected_arguments",
        [
            ("file_to_sync", "1", True, None, ["sync", "-f", "file_to_sync@1"]),
            (None, "12", True, "//DepotName/Main", ["sync", "-f", "//DepotName/Main/...@12"]),
            (None, None, False, None, ["sync"]),
            (None, None, True, None, ["sync", "-f"]),
        ],
    )
    @patch("deadline.unreal_perforce_utils.perforce.logger")
    @patch.object(perforce.P4, "connect", MagicMock())
    @patch.object(perforce.P4, "run", MagicMock())
    def test_sync(
        self,
        logger_mock: Mock,
        filepath,
        changelist,
        force,
        stream_path,
        expected_arguments,
    ):
        # GIVEN
        client = perforce.PerforceClient(perforce.PerforceConnection(), name="MyP4Client")

        spec_stream_mock = MagicMock()
        client.spec = spec_stream_mock

        if stream_path is not None:
            spec_stream_mock.__getitem__.return_value = stream_path

        # WHEN
        client.sync(filepath, changelist, force)

        # THEN
        logger_mock.info.assert_called_once_with(
            f"Running P4 sync with following arguments: {expected_arguments}"
        )


class TestPerforceWorkspaceSpecification:

    @pytest.mark.parametrize(
        "workspace_spec, expected_result",
        [
            (
                {
                    "Client": "MockedClientName",
                    "Root": "path/to/root",
                    "Stream": "//MockedProjectName/Mainline",
                },
                {
                    "Client": "{workspace_name}",
                    "Root": "path/to/root",
                    "Stream": "//MockedProjectName/Mainline",
                },
            ),
            (
                {
                    "Client": "MockedClientName",
                    "Root": "path/to/root",
                    "View": [
                        "//MockedProjectName/Mainline/... //MockedClientName/...",
                        "//PluginsStream/Dev/... //MockedClientName/Plugins/...",
                        "//OtherProjectName/Mainline/... //OtherClientName/...",
                    ],
                },
                {
                    "Client": "{workspace_name}",
                    "Root": "path/to/root",
                    "View": [
                        "//MockedProjectName/Mainline/... //{workspace_name}/...",
                        "//PluginsStream/Dev/... //{workspace_name}/Plugins/...",
                        "//OtherProjectName/Mainline/... //OtherClientName/...",
                    ],
                },
            ),
        ],
    )
    @patch.object(perforce.P4, "connect", MagicMock())
    @patch.object(perforce.P4, "run", MagicMock())
    def test_get_perforce_workspace_specification_template(
        self, workspace_spec: dict, expected_result: dict
    ):
        # GIVEN
        perforce.get_perforce_workspace_specification = MagicMock(return_value=workspace_spec)

        # WHEN
        template = perforce.get_perforce_workspace_specification_template()

        # THEN
        assert template == expected_result

    @patch.object(perforce.P4, "connect", MagicMock())
    @patch.object(perforce.P4, "run", MagicMock())
    def test_get_perforce_workspace_specification_template_failed(self):

        # GIVEN
        perforce.get_perforce_workspace_specification = MagicMock(return_value=None)

        # WHEN
        with pytest.raises(exceptions.PerforceWorkspaceNotFoundError) as exc_info:
            perforce.get_perforce_workspace_specification_template()

        # THEN
        assert exc_info
