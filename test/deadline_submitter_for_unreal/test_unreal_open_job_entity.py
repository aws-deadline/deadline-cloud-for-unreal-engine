import os
import sys
import unreal
import pytest
import unittest
from openjd.model.v2023_09 import JobTemplate, StepTemplate
from deadline.unreal_submitter.unreal_open_job import UnrealOpenJobEntity


TEMPLATES_DIRECTORY = f'{os.path.dirname(__file__)}/templates/default'.replace('\\', '/')


class TestUnrealOpenJobEntity(unittest.TestCase):

    def test_read_template(self):
        openjd_entity = UnrealOpenJobEntity(
            template_class=JobTemplate,
            file_path=f'{TEMPLATES_DIRECTORY}/job_template.yml'
        )
        template = openjd_entity.get_template_object()
        assert isinstance(template, dict)

    def test_read_not_existed_template(self):
        with pytest.raises(FileNotFoundError):
            openjd_entity = UnrealOpenJobEntity(template_class=JobTemplate, file_path='not_existed_template.yml')
            openjd_entity.get_template_object()

    def test_build_template(self):
        template_cls = StepTemplate
        openjd_entity = UnrealOpenJobEntity(
            template_class=template_cls,
            file_path=f'{TEMPLATES_DIRECTORY}/step_template.yml'
        )
        template = openjd_entity.get_template_object()
        openjd_template = openjd_entity.build_template()

        assert isinstance(openjd_template, template_cls)
        assert set(template.keys()).issubset(set(openjd_template.__fields__.keys()))


if __name__ == '__main__':
    for case in [TestUnrealOpenJobEntity]:
        suite = unittest.TestLoader().loadTestsFromTestCase(case)
        result = unittest.TextTestRunner(stream=sys.stdout, buffer=True).run(suite)