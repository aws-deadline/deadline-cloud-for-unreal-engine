#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import socket
import pytest
from unittest.mock import MagicMock, Mock, patch, mock_open

from deadline.unreal_perforce_utils import app


class TestUnrealP4UtilsApp:

    @pytest.mark.parametrize("project_name", ["MockedProject", "", None])
    def test_get_workspace_name(self, project_name: str):

        # GIVEN & WHEN
        workspace_name = app.get_workspace_name(project_name)

        # THEN
        assert workspace_name == f"{os.getlogin()}_{socket.gethostname()}_{project_name}"

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
