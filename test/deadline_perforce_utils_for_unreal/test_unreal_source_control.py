#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
import configparser
from unittest.mock import patch, Mock, MagicMock

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_perforce_utils import unreal_source_control  # noqa: E402


class TestUnrealSourceControl:

    @pytest.mark.parametrize("exists", [True, False])
    def test_validate_source_control_file(self, exists: bool):
        # GIVEN & WHEN
        with patch("os.path.exists", return_value=exists):
            # THEN
            if exists:
                assert (
                    unreal_source_control.validate_source_control_file("path/to/file")
                    == "path/to/file"
                )
            else:
                with pytest.raises(FileNotFoundError):
                    unreal_source_control.validate_source_control_file("path/to/file")

    @pytest.mark.parametrize("exists", [True, False])
    def test_validate_has_section(self, exists: bool):
        # GIVEN
        config = Mock()
        config.has_section.return_value = exists

        # WHEN & THEN
        if exists:
            assert unreal_source_control.validate_has_section(config, "section") == config
        else:
            with pytest.raises(KeyError):
                unreal_source_control.validate_has_section(config, "section")

    @pytest.mark.parametrize("exists", [True, False])
    def test_validate_has_option(self, exists: bool):
        # GIVEN
        config = Mock()

        if exists:
            config.get.return_value = "option"
        else:
            config.get = MagicMock(side_effect=configparser.NoOptionError("option", "section"))

        # WHEN & THEN
        if exists:
            assert unreal_source_control.validate_has_option(config, "section", "option") == config
        else:
            with pytest.raises(KeyError):
                unreal_source_control.validate_has_option(config, "section", "option")

    @patch(
        target="deadline.unreal_perforce_utils.unreal_source_control.validate_has_option",
        return_value=True,
    )
    def test_validate_provider_passed(self, validate_has_option_mock: Mock):
        # GIVEN
        config = Mock()
        config.get.return_value = "Perforce"

        # WHEN
        result = unreal_source_control.validate_provider(config)

        # THEN
        assert result == config

    @pytest.mark.parametrize(
        "has_option, get_result, exc_type",
        [(False, None, KeyError), (True, "NotPerforce", ValueError)],
    )
    def test_validate_provider_failed(
        self, has_option: bool, get_result: str, exc_type: type[Exception]
    ):
        config = configparser.ConfigParser()
        config.add_section("SourceControl.SourceControlSettings")
        if has_option:
            config["SourceControl.SourceControlSettings"]["Provider"] = "NotPerforce"

        # WHEN & THEN
        with pytest.raises(exc_type):
            unreal_source_control.validate_provider(config)

    def test_validate_perforce_source_control_settings_passed(self):
        # GIVEN
        config = configparser.ConfigParser()
        config.add_section("PerforceSourceControl.PerforceSourceControlSettings")
        config["PerforceSourceControl.PerforceSourceControlSettings"] = {
            "Port": "1234",
            "UserName": "user",
            "Workspace": "workspace",
        }

        # WHEN
        result = unreal_source_control.validate_perforce_source_control_settings(config)

        # THEN
        assert result == config

    @pytest.mark.parametrize(
        "options, exc_type",
        [
            ({"Port": "1234", "UserName": "user"}, KeyError),
            ({"Port": "1234", "Workspace": "workspace"}, KeyError),
            ({"Workspace": "workspace", "UserName": "user"}, KeyError),
            ({"UserName": "user"}, KeyError),
            ({"Workspace": "workspace"}, KeyError),
            ({"Workspace": "Port"}, KeyError),
            ({}, KeyError),
            ({"Port": "1234", "UserName": "user", "Workspace": ""}, ValueError),
            ({"Port": "1234", "UserName": "", "Workspace": "workspace"}, ValueError),
            ({"Port": "", "UserName": "user", "Workspace": "workspace"}, ValueError),
            ({"Port": "1234", "UserName": "", "Workspace": ""}, ValueError),
            ({"Port": "", "UserName": "user", "Workspace": ""}, ValueError),
            ({"Port": "", "UserName": "", "Workspace": "workspace"}, ValueError),
            ({"Port": "", "UserName": "", "Workspace": ""}, ValueError),
        ],
    )
    def test_validate_perforce_source_control_settings_failed(
        self, options: dict[str, str], exc_type: type[Exception]
    ):
        # GIVEN
        config = configparser.ConfigParser()
        config.add_section("PerforceSourceControl.PerforceSourceControlSettings")
        config["PerforceSourceControl.PerforceSourceControlSettings"] = options

        # WHEN & THEN
        with pytest.raises(exc_type):
            unreal_source_control.validate_perforce_source_control_settings(config)
