import os
import sys
import yaml
import copy
import unreal
import pytest
import unittest
from unittest.mock import patch, MagicMock

from open_job_template_api import PythonYamlLibraryImplementation  # noga: E402
from deadline.unreal_submitter.unreal_open_job import UnrealOpenJob, RenderUnrealOpenJob


TEMPLATES_DIRECTORY = f'{os.path.dirname(__file__)}/templates/default'.replace('\\', '/')
TEMPLATE_FILE = TEMPLATES_DIRECTORY + '/job_template.yml'

with open(TEMPLATE_FILE, 'r') as f:
    TEMPLATE_CONTENT = yaml.safe_load(f)


class TestUnrealOpenJob(unittest.TestCase):

    def test__build_parameter_values(self):
        extra_parameters = []
        for param in TEMPLATE_CONTENT['parameterDefinitions']:
            u_parameter = unreal.ParameterDefinition()
            u_parameter.name = param['name']
            u_parameter.type = getattr(unreal.ValueType, param['type'])
            u_parameter.value = str(param.get('default'))
            extra_parameters.append(u_parameter)

        open_job = UnrealOpenJob(file_path=TEMPLATE_FILE, extra_parameters=extra_parameters)
        parameter_values = open_job._build_parameter_values()

        assert [(p['name'], p['value']) for p in parameter_values] == \
               [(p['name'], p.get('default')) for p in TEMPLATE_CONTENT['parameterDefinitions']]

    def test__check_parameter_consistency_passed(self):
        open_job = UnrealOpenJob(
            file_path=TEMPLATE_FILE,
            extra_parameters=[
                PythonYamlLibraryImplementation.job_parameter_to_u_parameter_definition(job_parameter)
                for job_parameter in TEMPLATE_CONTENT['parameterDefinitions']
            ]
        )

        consistency_check_result = open_job._check_parameters_consistency()

        self.assertEqual(consistency_check_result.passed, True)
        self.assertIn('Parameters are consensual', consistency_check_result.reason)

    @patch('builtins.open', MagicMock())
    @patch(
        'yaml.safe_load',
        MagicMock(
            side_effect=[
                {'parameterDefinitions': []},
                {'parameterDefinitions': []}
            ]
        )
    )
    def test__check_parameters_consistency_failed_yaml(self):
        open_job = UnrealOpenJob(
            file_path=TEMPLATE_FILE,
            extra_parameters=[
                PythonYamlLibraryImplementation.job_parameter_to_u_parameter_definition(job_parameter)
                for job_parameter in TEMPLATE_CONTENT['parameterDefinitions']
            ]
        )
        consistency_check_result = open_job._check_parameters_consistency()

        self.assertEqual(consistency_check_result.passed, False)
        self.assertIn('Data Asset\'s parameters missed in YAML', consistency_check_result.reason)

    def test__check_parameters_consistency_failed_data_asset(self):
        open_job = UnrealOpenJob(file_path=TEMPLATE_FILE, extra_parameters=[])
        consistency_check_result = open_job._check_parameters_consistency()

        self.assertEqual(consistency_check_result.passed, False)
        self.assertIn('YAML\'s parameters missed in Data Asset', consistency_check_result.reason)

    def test__check_parameters_consistency_failed_same_parameters_different_types(self):
        change_type = {'PATH': 'STRING', 'STRING': 'INT', 'INT': 'FLOAT', 'FLOAT': 'PATH'}
        template_content = copy.deepcopy(TEMPLATE_CONTENT)
        extra_parameters = []
        for i, job_parameter in enumerate(template_content['parameterDefinitions']):
            if i == 0:
                job_parameter['type'] = change_type[job_parameter['type']]

            extra_parameters.append(
                PythonYamlLibraryImplementation.job_parameter_to_u_parameter_definition(job_parameter)
            )

        open_job = UnrealOpenJob(file_path=TEMPLATE_FILE, extra_parameters=extra_parameters)
        consistency_check_result = open_job._check_parameters_consistency()

        self.assertEqual(consistency_check_result.passed, False)
        self.assertIn('YAML\'s parameters missed in Data Asset', consistency_check_result.reason)
        self.assertIn('Data Asset\'s parameters missed in YAML', consistency_check_result.reason)


class TestRenderUnrealOpenJob(unittest.TestCase):

    def test_update_job_parameter_values_existed(self):
        parameters = [
            dict(name='ParamInt', value=1, new_value=2),
            dict(name='ParamFloat', value=1.0, new_value=2.0),
            dict(name='ParamString', value='foo', new_value='bar'),
            dict(name='ParamPath', value='path/to/file', new_value='path/to/new/file'),
        ]

        job_parameter_values = [dict(name=p['name'], value=p['value']) for p in parameters]
        param_names_before_update = [p['name'] for p in job_parameter_values]

        for p in parameters:
            job_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                job_parameter_values=job_parameter_values,
                job_parameter_name=p['name'],
                job_parameter_value=p['new_value']
            )

        self.assertEqual([p['name'] for p in job_parameter_values], param_names_before_update)
        self.assertEqual([p['value'] for p in job_parameter_values], [p['new_value'] for p in parameters])

    def test_update_job_parameter_values_new(self):
        job_parameter_values = [dict(name='ParamExisted', value=1)]
        job_parameters_count_before_update = len(job_parameter_values)

        job_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=job_parameter_values,
            job_parameter_name='ParamNew',
            job_parameter_value='foo',
            create_if_not_exists=True
        )
        self.assertEqual(job_parameters_count_before_update + 1, len(job_parameter_values))

    def test_update_job_parameter_values_not_existed(self):
        job_parameter_values = [dict(name='ParamExisted', value=1)]
        job_parameters_count_before_update = len(job_parameter_values)

        job_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=job_parameter_values,
            job_parameter_name='ParamNotExisted',
            job_parameter_value='foo'
        )
        self.assertEqual(job_parameters_count_before_update, len(job_parameter_values))


if __name__ == '__main__':
    for case in [TestUnrealOpenJob, TestRenderUnrealOpenJob]:
        suite = unittest.TestLoader().loadTestsFromTestCase(case)
        result = unittest.TextTestRunner(stream=sys.stdout, buffer=True).run(suite)
