#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import sys
import yaml
import unreal
import unittest
from pathlib import Path

from deadline.unreal_submitter.common import soft_obj_path_to_str
from deadline.unreal_submitter.unreal_open_job import open_job_description
from deadline.unreal_submitter.unreal_dependency_collector import collector, common

UNREAL_PROJECT_DIRECTORY = str(
    Path(
        unreal.Paths.convert_relative_path_to_full(unreal.Paths.get_project_file_path())
    ).parent
).replace('\\', '/')

PIPELINE_QUEUE = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem).get_queue()
EXPECTED_JOB_BUNDLE_PATH = f'{Path(__file__).parent.parent}/expected_job_bundle'


class TestUnrealOpenJob(unittest.TestCase):

    mrq_job: unreal.MoviePipelineExecutorJob = None
    open_job: open_job_description.OpenJobDescription = None

    @staticmethod
    def get_expected_job_bundle():
        with open(f'{EXPECTED_JOB_BUNDLE_PATH}/template.yaml', 'r') as f:
            expected_template = yaml.safe_load(f)

        with open(f'{EXPECTED_JOB_BUNDLE_PATH}/parameter_values.yaml', 'r') as f:
            expected_parameter_values = yaml.safe_load(f)

        with open(f'{EXPECTED_JOB_BUNDLE_PATH}/asset_references.yaml', 'r') as f:
            expected_asset_references = yaml.safe_load(f)

        return expected_template, expected_parameter_values, expected_asset_references

    @staticmethod
    def get_open_job_bundle_path(open_job: open_job_description.OpenJobDescription):
        with open(f'{open_job.job_bundle_path}/template.yaml', 'r') as f:
            template = yaml.safe_load(f)

        with open(f'{open_job.job_bundle_path}/parameter_values.yaml', 'r') as f:
            parameter_values = yaml.safe_load(f)

        with open(f'{open_job.job_bundle_path}/asset_references.yaml', 'r') as f:
            asset_references = yaml.safe_load(f)

        return template, parameter_values, asset_references

    @staticmethod
    def get_step_by_name(step_name, template):
        return next((s for s in template['steps'] if s['name'] == step_name), None)

    @staticmethod
    def check_input_file_parameter(param_name: str, parameters: list[dict]):
        param = next((param for param in parameters if param['name'] == param_name), None)
        if param is None:
            return False
        param_value = param['range'][0]

        return os.path.exists(param_value)

    def _build_open_job(self):
        if self.open_job:
            return

        original_job = PIPELINE_QUEUE.get_jobs()[0]

        new_queue = unreal.MoviePipelineQueue()
        self.mrq_job = new_queue.duplicate_job(original_job)

        self.open_job = open_job_description.OpenJobDescription(mrq_job=self.mrq_job)

    def _get_job_dependencies(self):
        dependency_collector = collector.DependencyCollector()

        level_sequence_path = soft_obj_path_to_str(self.mrq_job.sequence)
        level_sequence_path = os.path.splitext(level_sequence_path)[0]

        level_path = soft_obj_path_to_str(self.mrq_job.map)
        level_path = os.path.splitext(level_path)[0]

        level_sequence_dependencies = dependency_collector.collect(
            level_sequence_path, filter_method=common.DependencyFilters.dependency_in_game_folder
        )

        level_dependencies = dependency_collector.collect(
            level_path, filter_method=common.DependencyFilters.dependency_in_game_folder
        )

        return level_sequence_dependencies + level_dependencies + [level_sequence_path, level_path]

    def test_open_job_template(self):

        self._build_open_job()

        expected_template, *_ = TestUnrealOpenJob.get_expected_job_bundle()
        template, *_ = TestUnrealOpenJob.get_open_job_bundle_path(self.open_job)

        expected_parameter_names = [p['name'] for p in expected_template['parameterDefinitions']]
        for parameter in template['parameterDefinitions']:
            self.assertIn(parameter['name'], expected_parameter_names)

        expected_environment_names = [e['name'] for e in expected_template['jobEnvironments']]
        for environment in template['jobEnvironments']:
            self.assertIn(environment['name'], expected_environment_names)

        render_step = TestUnrealOpenJob.get_step_by_name('Render', template)
        assert TestUnrealOpenJob.check_input_file_parameter(
            'QueueManifestPath',
            render_step['parameterSpace']['taskParameterDefinitions']
        ) is True

        for step in template['steps']:
            if step['name'] != 'Render':
                assert TestUnrealOpenJob.check_input_file_parameter(
                    'ScriptPath',
                    step['parameterSpace']['taskParameterDefinitions']
                ) is True

    def test_open_job_parameter_values(self):
        self._build_open_job()

        e_t, expected_parameter_values, e_a = TestUnrealOpenJob.get_expected_job_bundle()
        t, parameter_values, a = TestUnrealOpenJob.get_open_job_bundle_path(self.open_job)

        for parameter in expected_parameter_values['parameterValues']:
            parameter['value'] = 'mocked value'

        for parameter in parameter_values['parameterValues']:
            parameter['value'] = 'mocked value'

        self.assertEqual(parameter_values, expected_parameter_values)

    def test_open_job_asset_asset_references(self):
        self._build_open_job()

        *_, asset_references = TestUnrealOpenJob.get_open_job_bundle_path(self.open_job)

        self.assertIn(
            self.open_job._manifest_path,
            asset_references['assetReferences']['inputs']['filenames']
        )

        job_dependencies = self._get_job_dependencies()
        os_dependencies = []
        for dependency in job_dependencies:
            os_dependency = common.os_path_from_unreal_path(dependency, with_ext=True)
            if os.path.exists(os_dependency):
                os_dependencies.append(os_dependency)

        os_dependencies = set(os_dependencies)
        assert len(os_dependencies) != 0 and os_dependencies.issubset(asset_references['assetReferences']['inputs']['filenames'])

        input_directories = set(asset_references['assetReferences']['inputs']['directories'])
        assert input_directories.issubset(
            {f'{UNREAL_PROJECT_DIRECTORY}/Config', f'{UNREAL_PROJECT_DIRECTORY}/Binaries'}
        )

        assert len(asset_references['assetReferences']['outputs']['directories']) != 0


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUnrealOpenJob)
    unittest.TextTestRunner(stream=sys.stdout, buffer=True).run(suite)
