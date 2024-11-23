#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
from unittest.mock import Mock, MagicMock, PropertyMock, patch

from openjd.model.v2023_09 import JobTemplate, StepTemplate

from test.deadline_submitter_for_unreal import fixtures

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (  # noqa: E402
    UnrealOpenJobEntity,
)


class TestUnrealOpenJobEntity:

    @patch.object(UnrealOpenJobEntity, "_check_parameters_consistency")
    def test__validate_parameters_passed(self, check_consistency_mock: Mock):
        # GIVEN
        unreal_open_job_entity = UnrealOpenJobEntity(template_class=JobTemplate, file_path="")

        return_value = Mock()
        return_value.passed = True
        check_consistency_mock.return_value = return_value

        # WHEN
        is_valid = unreal_open_job_entity._validate_parameters()

        # THEN
        assert is_valid

    @patch.object(UnrealOpenJobEntity, "_check_parameters_consistency")
    def test__validate_parameters_failed(self, check_consistency_mock: Mock):
        # GIVEN
        unreal_open_job_entity = UnrealOpenJobEntity(template_class=JobTemplate, file_path="")
        fail_reason = "Mocked reason"

        return_value = Mock()
        return_value.passed = False
        return_value.reason = fail_reason
        check_consistency_mock.return_value = return_value

        # WHEN
        with pytest.raises(Exception) as exception_info:
            unreal_open_job_entity._validate_parameters()

        # THEN
        assert str(exception_info.value) == fail_reason

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.file_path",
        new_callable=PropertyMock,
    )
    def test_get_template_object_not_existed(self, file_path_mock: PropertyMock):
        # GIVEN
        file_path = "not_existed_template.yml"
        unreal_open_job_entity = UnrealOpenJobEntity(JobTemplate, file_path)
        file_path_mock.side_effect = [file_path] * 4

        # WHEN
        with pytest.raises(FileNotFoundError) as exc_info:
            print(unreal_open_job_entity.get_template_object())

        # THEN
        assert str(exc_info.value) == f'Descriptor file "{file_path}" not found'

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value=fixtures.f_step_template_default(),
    )
    def test_build_template(self, get_template_object_mock: Mock):
        # GIVEN
        template_cls = StepTemplate
        openjd_entity = UnrealOpenJobEntity(template_class=template_cls, file_path="")
        template = fixtures.f_step_template_default()

        # WHEN
        openjd_template = openjd_entity.build_template()

        # THEN
        assert isinstance(openjd_template, template_cls)
        assert set(template.keys()).issubset(set(openjd_template.__fields__.keys()))
