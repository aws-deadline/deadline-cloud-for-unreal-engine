#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest
from unittest.mock import patch, MagicMock


from deadline.unreal_submitter import exceptions
from deadline.unreal_submitter.perforce_api import PerforceApi, P4Exception, P4


class TestPerforceApi:
    @pytest.mark.parametrize(
        "port, user, client",
        [("port:1999", "j.doe", "JOHN-DOE-PC"), (None, None, None)],
    )
    @patch("deadline.unreal_submitter.perforce_api.P4", autospec=True)
    def test_perforce_api_parameters(self, p4_mock, port, user, client):
        # GIVEN & WHEN
        api = PerforceApi(port=port, user=user, client=client)

        # THEN
        assert hasattr(api.p4, "port") == (port is not None)
        assert hasattr(api.p4, "user") == (user is not None)
        assert hasattr(api.p4, "client") == (client is not None)

    @patch.object(P4, "connect", MagicMock(side_effect=P4Exception("NOT CONNECTED")))
    def test_connection_failed(self):
        # GIVEN
        with pytest.raises(exceptions.PerforceConnectionError) as exc_info:
            # WHEN
            PerforceApi()

        # THEN
        assert "Could not connect Perforce server" in str(exc_info.value)

    @pytest.mark.parametrize("password, login_calls", [(None, 0), ("VeryStrongPassword", 1)])
    @patch.object(P4, "run_login", new_callable=MagicMock())
    @patch.object(P4, "connect", MagicMock())
    def test_login(self, run_login_mock, password, login_calls):
        # GIVEN & WHEN
        PerforceApi(password=password)

        # THEN
        assert run_login_mock.call_count == login_calls

    @pytest.mark.parametrize(
        "p4_output, expected_result",
        [
            ({"clientStream": "testClientStream"}, "testClientStream"),
            ({"otherInfo": "otherValue"}, None),
        ],
    )
    @patch("deadline.unreal_submitter.perforce_api.P4", autospec=True)
    def test_get_stream_path(self, p4_mock, p4_output, expected_result):
        # GIVEN
        perforce_api = PerforceApi()

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
    @patch("deadline.unreal_submitter.perforce_api.P4", autospec=True)
    def test_get_client_root(self, p4_mock, p4_output, expected_result):
        # GIVEN
        perforce_api = PerforceApi()

        # WHEN
        with patch.object(perforce_api, "get_info", return_value=p4_output):
            client_root = perforce_api.get_client_root()

        # THEN
        assert client_root == expected_result

    @pytest.mark.parametrize(
        "p4_output, expected_result",
        [([{"change": 10}, {"change": 9}, {"change": 8}], 10), ([], None)],
    )
    @patch("deadline.unreal_submitter.perforce_api.P4", autospec=True)
    def test_get_latest_changelist_number(self, p4_mock, p4_output, expected_result):
        # GIVEN
        perforce_api = PerforceApi()

        # WHEN
        with (
            patch.object(perforce_api, "p4", MagicMock()),
            patch.object(perforce_api.p4, "run", return_value=p4_output),
            patch.object(perforce_api.p4, "client", "MockClient"),
        ):
            changelist = perforce_api.get_latest_changelist_number()

        # THEN
        assert changelist == expected_result
