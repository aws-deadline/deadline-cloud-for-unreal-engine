import os
import sys
import yaml
import unreal
import unittest
from unittest.mock import patch, MagicMock
from openjd.model.v2023_09 import Environment
from deadline.unreal_submitter.unreal_open_job import UnrealOpenJobEnvironment


TEMPLATES_DIRECTORY = f'{os.path.dirname(__file__)}/templates/default'.replace('\\', '/')
TEMPLATE_FILE = TEMPLATES_DIRECTORY + '/environment_template.yml'

with open(TEMPLATE_FILE, 'r') as f:
    TEMPLATE_CONTENT = yaml.safe_load(f)


class TestUnrealOpenJobEnvironment(unittest.TestCase):

    def test__check_parameters_consistency_passed(self):
        openjd_env = UnrealOpenJobEnvironment(file_path=TEMPLATE_FILE, variables=TEMPLATE_CONTENT['variables'])

        consistency_check_result = openjd_env._check_parameters_consistency()

        self.assertEqual(consistency_check_result.passed, True)
        self.assertIn('Parameters are consensual', consistency_check_result.reason)

    @patch('builtins.open', MagicMock())
    @patch('yaml.safe_load', MagicMock(side_effect=[{'variables': {}}, {'variables': {}}]))
    def test__check_parameters_consistency_failed_yaml(self):
        openjd_env = UnrealOpenJobEnvironment(file_path=TEMPLATE_FILE, variables=TEMPLATE_CONTENT['variables'])

        consistency_check_result = openjd_env._check_parameters_consistency()

        self.assertEqual(consistency_check_result.passed, False)
        self.assertIn('Data Asset\'s parameters missed in YAML', consistency_check_result.reason)

    def test__check_parameters_consistency_failed_data_asset(self):
        openjd_env = UnrealOpenJobEnvironment(file_path=TEMPLATE_FILE, variables={})

        consistency_check_result = openjd_env._check_parameters_consistency()
        self.assertEqual(consistency_check_result.passed, False)
        self.assertIn('YAML\'s parameters missed in Data Asset', consistency_check_result.reason)

    def test__build_template(self):
        openjd_entity = UnrealOpenJobEnvironment(
            file_path=TEMPLATE_FILE,
            name=TEMPLATE_CONTENT['name'],
            variables=TEMPLATE_CONTENT['variables']
        )
        openjd_template = openjd_entity._build_template()

        assert isinstance(openjd_template, Environment)
        assert set(TEMPLATE_CONTENT.keys()).issubset(set(openjd_template.__fields__.keys()))


if __name__ == '__main__':
    for case in [TestUnrealOpenJobEnvironment]:
        suite = unittest.TestLoader().loadTestsFromTestCase(case)
        result = unittest.TextTestRunner(stream=sys.stdout, buffer=True).run(suite)