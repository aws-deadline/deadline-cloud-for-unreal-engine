#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest
from unittest.mock import patch, MagicMock


from deadline.unreal_submitter.perforce_api import PerforceApi


class TestPerforceApi:

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
        "p4_output, expected_result", [([{"change": 10}, {"change": 9}, {"change": 8}], 10)]
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
