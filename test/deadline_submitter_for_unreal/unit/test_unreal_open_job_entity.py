import os
import sys
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from openjd.model.v2023_09 import JobTemplate, StepTemplate


TEMPLATES_DIRECTORY = f"{os.path.dirname(os.path.dirname(__file__))}/templates/default".replace(
    "\\", "/"
)

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock


class TestUnrealOpenJobEntity:

    def test_read_template(self):
        # GIVEN
        from deadline.unreal_submitter.unreal_open_job import UnrealOpenJobEntity

        unreal_open_job_entity = UnrealOpenJobEntity(
            template_class=JobTemplate, file_path=f"{TEMPLATES_DIRECTORY}/job_template.yml"
        )

        # WHEN
        template = unreal_open_job_entity.get_template_object()

        # THEN
        assert isinstance(template, dict)

    @patch(
        "deadline.unreal_submitter.unreal_open_job.UnrealOpenJobEntity.file_path",
        new_callable=PropertyMock,
    )
    def test_read_not_existed_template(self, file_path_mock: PropertyMock):
        # GIVEN
        from deadline.unreal_submitter.unreal_open_job import UnrealOpenJobEntity

        file_path = "not_existed_template.yml"
        unreal_open_job_entity = UnrealOpenJobEntity(JobTemplate, file_path)
        file_path_mock.side_effect = [file_path] * 4

        # WHEN
        with pytest.raises(FileNotFoundError) as exc_info:
            print(unreal_open_job_entity.get_template_object())

        # THEN
        assert str(exc_info.value) == f'Descriptor file "{file_path}" not found'

    def test_build_template(self):
        # GIVEN
        from deadline.unreal_submitter.unreal_open_job import UnrealOpenJobEntity

        template_cls = StepTemplate
        openjd_entity = UnrealOpenJobEntity(
            template_class=template_cls, file_path=f"{TEMPLATES_DIRECTORY}/step_template.yml"
        )
        template = openjd_entity.get_template_object()
        openjd_template = openjd_entity.build_template()

        assert isinstance(openjd_template, template_cls)
        assert set(template.keys()).issubset(set(openjd_template.__fields__.keys()))
