import os
import sys

import pytest
import yaml
import copy
import unreal
import unittest
from unittest.mock import patch, Mock, MagicMock
from openjd.model.v2023_09 import StepTemplate

from open_job_template_api import PythonYamlLibraryImplementation  # noga: E402
from deadline.unreal_submitter.unreal_open_job import UnrealOpenJobStep, RenderUnrealOpenJobStep
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import OpenJobStepParameterNames


TEMPLATES_DIRECTORY = f'{os.path.dirname(__file__)}/templates/default'.replace('\\', '/')
TEMPLATE_FILE = TEMPLATES_DIRECTORY + '/step_template.yml'

with open(TEMPLATE_FILE, 'r') as f:
    TEMPLATE_CONTENT: dict = yaml.safe_load(f)


class TestUnrealOpenJobStep(unittest.TestCase):

    def test__check_parameters_consistency_passed(self):

        openjd_step = UnrealOpenJobStep(
            file_path=TEMPLATE_FILE,
            extra_parameters=[
                PythonYamlLibraryImplementation.step_parameter_to_u_step_task_parameter(step_parameter)
                for step_parameter in TEMPLATE_CONTENT['parameterSpace']['taskParameterDefinitions']
            ]
        )

        consistency_check_result = openjd_step._check_parameters_consistency()

        self.assertEqual(consistency_check_result.passed, True)
        self.assertIn('Parameters are consensual', consistency_check_result.reason)

    @patch(
        'deadline.unreal_submitter.unreal_open_job.UnrealOpenJobStep.get_template_object',
        return_value={'parameterSpace': {'taskParameterDefinitions': []}}
    )
    def test__check_parameters_consistency_failed_yaml(self, mock_get_template_object: Mock):
        openjd_step = UnrealOpenJobStep(
            file_path=TEMPLATE_FILE,
            extra_parameters=[
                PythonYamlLibraryImplementation.step_parameter_to_u_step_task_parameter(step_parameter)
                for step_parameter in TEMPLATE_CONTENT['parameterSpace']['taskParameterDefinitions']
            ]
        )
        consistency_check_result = openjd_step._check_parameters_consistency()

        self.assertEqual(consistency_check_result.passed, False)
        self.assertIn('Data Asset\'s parameters missed in YAML', consistency_check_result.reason)

    def test__check_parameters_consistency_failed_data_asset(self):
        openjd_step = UnrealOpenJobStep(file_path=TEMPLATE_FILE, extra_parameters=[])
        consistency_check_result = openjd_step._check_parameters_consistency()

        self.assertEqual(consistency_check_result.passed, False)
        self.assertIn('YAML\'s parameters missed in Data Asset', consistency_check_result.reason)

    def test__check_parameters_consistency_failed_same_parameters_different_types(self):
        change_type = {'PATH': 'STRING', 'STRING': 'INT', 'INT': 'FLOAT', 'FLOAT': 'PATH'}
        template_content = copy.deepcopy(TEMPLATE_CONTENT)
        extra_parameters = []
        for i, step_parameter in enumerate(template_content['parameterSpace']['taskParameterDefinitions']):
            if i == 0:
                step_parameter['type'] = change_type[step_parameter['type']]

            extra_parameters.append(
                PythonYamlLibraryImplementation.step_parameter_to_u_step_task_parameter(step_parameter)
            )

        openjd_step = UnrealOpenJobStep(file_path=TEMPLATE_FILE, extra_parameters=extra_parameters)
        consistency_check_result = openjd_step._check_parameters_consistency()

        self.assertEqual(consistency_check_result.passed, False)
        self.assertIn('YAML\'s parameters missed in Data Asset', consistency_check_result.reason)
        self.assertIn('Data Asset\'s parameters missed in YAML', consistency_check_result.reason)

    def test__build_step_parameter_definition_list(self):
        extra_parameters = []
        value_map = {
            'INT': '1',
            'FLOAT': '1.0',
            'STRING': 'foo',
            'PATH': '/path/to/file'
        }
        for step_parameter in TEMPLATE_CONTENT['parameterSpace']['taskParameterDefinitions']:
            u_step_parameter = PythonYamlLibraryImplementation.step_parameter_to_u_step_task_parameter(step_parameter)
            u_step_parameter.range = [value_map[step_parameter['type']]]
            extra_parameters.append(u_step_parameter)

        openjd_step = UnrealOpenJobStep(file_path=TEMPLATE_FILE, extra_parameters=extra_parameters)

        parameter_definitions = openjd_step._build_step_parameter_definition_list()

        self.assertEqual(
            len(parameter_definitions),
            len(TEMPLATE_CONTENT['parameterSpace']['taskParameterDefinitions'])
        )

        self.assertEqual(
            [p.name for p in parameter_definitions],
            [p['name'] for p in TEMPLATE_CONTENT['parameterSpace']['taskParameterDefinitions']]
        )

    def test__build_template(self):
        openjd_step = UnrealOpenJobStep(
            file_path=TEMPLATE_FILE,
            name=TEMPLATE_CONTENT['name'],
            extra_parameters=[
                PythonYamlLibraryImplementation.step_parameter_to_u_step_task_parameter(step_parameter)
                for step_parameter in TEMPLATE_CONTENT['parameterSpace']['taskParameterDefinitions']
            ]
        )
        openjd_template = openjd_step._build_template()

        assert isinstance(openjd_template, StepTemplate)
        assert set(TEMPLATE_CONTENT.keys()).issubset(set(openjd_template.__fields__.keys()))

    @patch('deadline.unreal_submitter.unreal_open_job.unreal_open_job.UnrealOpenJobEnvironment.from_data_asset')
    def test_from_data_asset(self, env_from_data_asset_mock: Mock):
        step_data_asset = MagicMock()
        step_data_asset.path_to_template = ''
        step_data_asset.name = 'StepA'
        step_data_asset.depends_on = []

        environment_data_asset = MagicMock()
        step_data_asset.environments = [environment_data_asset]

        get_step_parameters_mock = MagicMock()
        get_step_parameters_mock.return_value = [
            PythonYamlLibraryImplementation.step_parameter_to_u_step_task_parameter(step_parameter)
            for step_parameter in TEMPLATE_CONTENT['parameterSpace']['taskParameterDefinitions']
        ]
        step_data_asset.get_step_parameters = get_step_parameters_mock

        open_job_step = UnrealOpenJobStep.from_data_asset(step_data_asset)

        assert isinstance(open_job_step, UnrealOpenJobStep)
        assert open_job_step.name == step_data_asset.name
        assert open_job_step._step_dependencies == step_data_asset.depends_on
        assert open_job_step._extra_parameters == step_data_asset.get_step_parameters()
        env_from_data_asset_mock.assert_called()


class TestRenderUnrealOpenJobStep(unittest.TestCase):

    def test_build_u_step_task_parameter(self):
        name = 'test_name'
        parameter_types = ['INT', 'FLOAT', 'STRING', 'PATH']
        parameter_range = ['1', '1.0', 'foo', 'path/to/bar']

        for parameter in zip(parameter_types, parameter_range):
            u_parameter = RenderUnrealOpenJobStep.build_u_step_task_parameter(
                name=name,
                parameter_type=parameter[0],
                parameter_range=[parameter[1]]
            )
            self.assertIsInstance(u_parameter, unreal.StepTaskParameterDefinition)
            self.assertEqual(u_parameter.name, name)
            self.assertEqual(u_parameter.type.name, parameter[0])
            self.assertEqual(u_parameter.range, [parameter[1]])

    def test__get_chunk_ids_count(self):
        for task_chunk_size, enabled_shots_count, expected_ids_range in [
            (1, 15, [i for i in range(15)]),
            (2, 15, [i for i in range(8)]),
            (5, 29, [0, 1, 2, 3, 4, 5]),
            (6, 36, [0, 1, 2, 3, 4, 5]),
            (100000, 100, [0])
        ]:
            shot_info = []
            for i in range(enabled_shots_count):
                shot_info_mock = MagicMock()
                shot_info_mock.enabled = True
                shot_info.append(shot_info_mock)

            mrq_job_mock = MagicMock()
            mrq_job_mock.shot_info = shot_info

            chunk_size_param = unreal.StepTaskParameterDefinition()
            chunk_size_param.name = OpenJobStepParameterNames.TASK_CHUNK_SIZE
            chunk_size_param.type = getattr(unreal.ValueType, 'INT')
            chunk_size_param.range = [str(task_chunk_size)]

            render_step = RenderUnrealOpenJobStep('', extra_parameters=[chunk_size_param], mrq_job=mrq_job_mock)
            ids_count = render_step._get_chunk_ids_count()
            self.assertEqual([i for i in range(ids_count)], expected_ids_range)

    def test__find_extra_parameter_by_name(self):
        existed_param_name = 'ExistedParam'
        not_existed_param_name = 'NotExistedParam'

        param = unreal.StepTaskParameterDefinition()
        param.name = existed_param_name
        param.type = getattr(unreal.ValueType, 'INT')
        param.range = [str(1)]
        render_step = RenderUnrealOpenJobStep('', extra_parameters=[param])

        self.assertIsInstance(
            render_step._find_extra_parameter_by_name(existed_param_name),
            unreal.StepTaskParameterDefinition
        )
        self.assertIsNone(
            render_step._find_extra_parameter_by_name(not_existed_param_name)
        )

    def test__update_extra_parameter(self):
        param_to_update_name = 'ParamToUpdate'
        param_to_update = unreal.StepTaskParameterDefinition()
        param_to_update.name = param_to_update_name
        param_to_update.type = getattr(unreal.ValueType, 'INT')
        param_to_update.range = [str(1)]
        render_step = RenderUnrealOpenJobStep('', extra_parameters=[param_to_update])

        p = unreal.StepTaskParameterDefinition()
        p.name = param_to_update_name
        p.type = param_to_update.type
        p.range = [str(1), str(2)]
        render_step._update_extra_parameter(p)

        new_param_name = 'NewParamName'
        new_param = unreal.StepTaskParameterDefinition()
        new_param.name = new_param_name
        new_param.type = getattr(unreal.ValueType, 'STRING')
        new_param.range = ['foo']
        render_step._update_extra_parameter(new_param)

        self.assertEqual(len(render_step._extra_parameters), 1)
        self.assertNotIn(new_param, render_step._extra_parameters)

    def test__get_render_arguments_type(self):
        for extra_parameters, expected_type in [
            (
                    [{'name': OpenJobStepParameterNames.QUEUE_MANIFEST_PATH, 'type': 'PATH', 'range': ['path/to/manifest']}],
                    RenderUnrealOpenJobStep.RenderArgsType.QUEUE_MANIFEST_PATH
            ),
            (
                    [{'name': OpenJobStepParameterNames.MOVIE_PIPELINE_QUEUE_PATH, 'type': 'PATH', 'range': ['path/to/mrq/asset']}],
                    RenderUnrealOpenJobStep.RenderArgsType.MRQ_ASSET
            ),
            (
                    [
                        {'name': OpenJobStepParameterNames.LEVEL_SEQUENCE_PATH, 'type': 'PATH', 'range': ['path/to/sequence']},
                        {'name': OpenJobStepParameterNames.LEVEL_PATH, 'type': 'PATH', 'range': ['path/to/level']},
                        {'name': OpenJobStepParameterNames.MRQ_JOB_CONFIGURATION_PATH, 'type': 'PATH', 'range': ['path/to/config']},
                    ],
                    RenderUnrealOpenJobStep.RenderArgsType.RENDER_DATA
            ),
            (
                [], RenderUnrealOpenJobStep.RenderArgsType.NOT_SET
            )
        ]:
            render_open_job_step = RenderUnrealOpenJobStep(
                file_path='',
                extra_parameters=[
                    PythonYamlLibraryImplementation.step_parameter_to_u_step_task_parameter(step_parameter)
                    for step_parameter in extra_parameters
                ]
            )

            assert render_open_job_step._get_render_arguments_type() == expected_type

    def test__build_template_validation_failed(self):
        with pytest.raises(ValueError) as expected_exc:
            render_open_job_step = RenderUnrealOpenJobStep(file_path='', extra_parameters=[])
            render_open_job_step._build_template()
            assert 'RenderOpenJobStep parameters are not valid' in expected_exc.value


if __name__ == '__main__':
    for case in [TestUnrealOpenJobStep, TestRenderUnrealOpenJobStep]:
        suite = unittest.TestLoader().loadTestsFromTestCase(case)
        result = unittest.TextTestRunner(stream=sys.stdout, buffer=True).run(suite)
