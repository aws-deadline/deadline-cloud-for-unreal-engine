import os
import sys
import yaml
import unittest
from unittest.mock import patch, Mock, MagicMock
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

    @patch(
        'deadline.unreal_submitter.unreal_open_job.UnrealOpenJobEnvironment.get_template_object',
        return_value={'variables': {}}
    )
    def test__check_parameters_consistency_failed_yaml(self, mock_get_template_object: Mock):
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

    def test_from_data_asset(self):
        env_data_asset = MagicMock()
        env_data_asset.path_to_template = ''
        env_data_asset.name = 'StepA'

        variables_mock = MagicMock()
        variables_mock.variables = TEMPLATE_CONTENT['variables']

        env_data_asset.variables = variables_mock

        open_job_environment = UnrealOpenJobEnvironment.from_data_asset(env_data_asset)

        assert isinstance(open_job_environment, UnrealOpenJobEnvironment)
        assert open_job_environment.name == env_data_asset.name
        assert env_data_asset.variables.variables == open_job_environment._variables


if __name__ == '__main__':
    for case in [TestUnrealOpenJobEnvironment]:
        suite = unittest.TestLoader().loadTestsFromTestCase(case)
        result = unittest.TextTestRunner(stream=sys.stdout, buffer=True).run(suite)