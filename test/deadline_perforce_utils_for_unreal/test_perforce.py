#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest
from unittest.mock import patch, Mock, MagicMock

from deadline.unreal_perforce_utils import perforce, exceptions


class TestPerforceConnection:

    @pytest.mark.parametrize(
        "port, user",
        [("port:1999", "j.doe"), (None, None)],
    )
    @patch("deadline.unreal_perforce_utils.perforce.P4", autospec=True)
    def test_perforce_connection_parameters(self, p4_mock, port, user):
        # GIVEN & WHEN
        api = perforce.PerforceConnection(port=port, user=user)

        # THEN
        assert hasattr(api.p4, "port") == (port is not None)
        assert hasattr(api.p4, "user") == (user is not None)

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

    @pytest.mark.parametrize("password, login_calls", [(None, 0), ("VeryStrongPassword", 1)])
    @patch.object(perforce.P4, "run_login", new_callable=MagicMock())
    def test_login(self, run_login_mock, password, login_calls):
        # GIVEN & WHEN
        perforce.PerforceConnection(password=password)

        # THEN
        assert run_login_mock.call_count == login_calls

    @pytest.mark.parametrize(
        "p4_output, expected_result",
        [
            ({"clientStream": "testClientStream"}, "testClientStream"),
            ({"otherInfo": "otherValue"}, None),
        ],
    )
    @patch("deadline.unreal_perforce_utils.perforce.P4", autospec=True)
    def test_get_stream_path(self, p4_mock, p4_output, expected_result):
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
    @patch("deadline.unreal_perforce_utils.perforce.P4", autospec=True)
    def test_get_client_root(self, p4_mock, p4_output, expected_result):
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
    @patch("deadline.unreal_perforce_utils.perforce.P4", autospec=True)
    def test_get_latest_changelist_number(self, p4_mock, p4_output, expected_result):
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
            ("file_to_sync", 1, True, None, ["sync", "-f", "file_to_sync@1"]),
            (None, 12, True, "//DepotName/Main", ["sync", "-f", "//DepotName/Main/...@12"]),
            (None, None, False, None, ["sync"]),
            (None, None, True, None, ["sync", "-f"]),
        ]
    )
    @patch("deadline.unreal_perforce_utils.perforce.logger")
    @patch("deadline.unreal_perforce_utils.perforce.P4", autospec=True)
    def test_sync(
            self, p4_mock, logger_mock: Mock, filepath, changelist, force, stream_path, expected_arguments
    ):
        # GIVEN
        connection = perforce.PerforceConnection()
        with patch.object(connection.p4, "fetch_client", new_callable=MagicMock()):
            client = perforce.PerforceClient(perforce.PerforceConnection(), name="MyP4Client")

        if stream_path is not None:
            client.spec["Stream"] = stream_path

        # WHEN
        with patch.object(client.p4, "run", new_callable=MagicMock()):
            client.sync(filepath, changelist, force)

        # THEN
        assert logger_mock.assert_called_once_with(
            [f"Running P4 sync with following arguments: {expected_arguments}"]
        )


class TestPerforceWorkspaceSpecification:

    def test_get_perforce_workspace_specification_template_stream_only(self):
        pass