# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
from unittest.mock import  MagicMock, patch
import unreal
from openjd.model.v2023_09 import JobTemplate

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (  # noqa: E402
    UnrealOpenJobEntity,
    OpenJobParameterNames,
)
from deadline.unreal_submitter.submitter import UnrealMrqJobSubmitter


class TestCheckCondaPackageVersion:


    def test_check_conda_package_version_no_conda_packages_param(self):
        # Change UE version
        unreal.SystemLibrary.get_engine_version = lambda: "5.3.0"
        unreal.EditorDialog.show_message = MagicMock()

        open_job_entity = UnrealOpenJobEntity(template_class=JobTemplate, file_path="")

        open_job_entity.get_mrq_template_object = lambda: {"parameterDefinitions": []}

        result = open_job_entity.check_conda_package_version()

        assert result is True
        unreal.EditorDialog.show_message.assert_not_called()

    @patch("unreal.SystemLibrary.get_engine_version")
    @patch("unreal.EditorDialog.show_message")
    @patch.object(UnrealOpenJobEntity, "get_mrq_template_object", create=True)
    def test_check_conda_package_version_conda_packages_no_value(self, get_mrq_template_mock, show_message_mock, get_engine_version_mock):
        # GIVEN
        get_engine_version_mock.return_value = "5.3.0"
        get_mrq_template_mock.return_value = {
            "parameterDefinitions": [
                {"name": OpenJobParameterNames.CONDA_PACKAGES, "default": ""}
            ]
        }
        
        unreal_open_job_entity = UnrealOpenJobEntity(template_class=JobTemplate, file_path="")

        # WHEN
        result = unreal_open_job_entity.check_conda_package_version()

        # THEN
        assert result is True
        get_mrq_template_mock.assert_called_once()
        show_message_mock.assert_not_called()

    @patch("unreal.SystemLibrary.get_engine_version")
    @patch("unreal.EditorDialog.show_message")
    @patch.object(UnrealOpenJobEntity, "get_mrq_template_object", create=True)
    def test_check_conda_package_version_no_unrealengine_pattern(self, get_mrq_template_mock, show_message_mock, get_engine_version_mock):
        # GIVEN
        get_engine_version_mock.return_value = "5.3.0"
        get_mrq_template_mock.return_value = {
            "parameterDefinitions": [
                {"name": OpenJobParameterNames.CONDA_PACKAGES, "default": "somepackage=1.0"}
            ]
        }
        
        unreal_open_job_entity = UnrealOpenJobEntity(template_class=JobTemplate, file_path="")

        # WHEN
        result = unreal_open_job_entity.check_conda_package_version()

        # THEN
        assert result is True
        get_mrq_template_mock.assert_called_once()
        show_message_mock.assert_not_called()

    @patch("unreal.SystemLibrary.get_engine_version")
    @patch("unreal.EditorDialog.show_message")
    @patch.object(UnrealOpenJobEntity, "get_mrq_template_object", create=True)
    def test_check_conda_package_version_versions_match(self, get_mrq_template_mock, show_message_mock, get_engine_version_mock):
        # GIVEN
        get_engine_version_mock.return_value = "5.3.0"
        get_mrq_template_mock.return_value = {
            "parameterDefinitions": [
                {"name": OpenJobParameterNames.CONDA_PACKAGES, "default": "unrealengine=5.3"}
            ]
        }
        
        unreal_open_job_entity = UnrealOpenJobEntity(template_class=JobTemplate, file_path="")

        # WHEN
        result = unreal_open_job_entity.check_conda_package_version()

        # THEN
        assert result is True
        get_mrq_template_mock.assert_called_once()
        show_message_mock.assert_not_called()

    @patch("unreal.SystemLibrary.get_engine_version")
    @patch("unreal.EditorDialog.show_message")
    def test_check_conda_package_version_minor_version_difference(self, show_message_mock, get_engine_version_mock):
    # GIVEN
        get_engine_version_mock.return_value = "5.3.2"

        unreal_open_job_entity = UnrealOpenJobEntity(template_class=JobTemplate, file_path="")

        unreal_open_job_entity.get_mrq_template_object = lambda: {
            "parameterDefinitions": [
                {"name": OpenJobParameterNames.CONDA_PACKAGES, "default": "unrealengine=5.3"}
            ]
        }

    # WHEN
        result = unreal_open_job_entity.check_conda_package_version()

    # THEN
        assert result is True
        show_message_mock.assert_not_called()
