import os
import re
import json
import unreal
from collections import OrderedDict
from typing import List, Dict, Any

from openjd.model.v2023_09 import *
from deadline.client.job_bundle.submission import AssetReferences
from deadline.client.job_bundle import deadline_yaml_dump, create_job_history_bundle_dir

from deadline.unreal_submitter import common
from deadline.unreal_submitter import settings
from deadline.unreal_submitter.unreal_dependency_collector import DependencyCollector, DependencyFilters
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (
    UnrealOpenJobEntity,
    OpenJobParameterNames,
    PARAMETER_DEFINITION_MAPPING,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
    UnrealOpenJobStep,
    RenderUnrealOpenJobStep
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (
    UnrealOpenJobEnvironment,
    UnrealOpenJobUgsEnvironment
)


class JobSharedSettings:
    """
    OpenJob shared settings representation.
    Contains SharedSettings model as dictionary built from template and allows to fill its values
    """

    def __init__(self, job_shared_settings):
        self.source_shared_settings = job_shared_settings
        self.parameter_values: List[Dict[Any, Any]] = [
            {
                "name": "deadline:targetTaskRunStatus",
                "type": "STRING",
                "userInterface": {
                    "control": "DROPDOWN_LIST",
                    "label": "Initial State",
                },
                "allowedValues": ["READY", "SUSPENDED"],
                "value": self.get_initial_state(),
            },
            {
                "name": "deadline:maxFailedTasksCount",
                "description": "Maximum number of Tasks that can fail before the Job will be marked as failed.",
                "type": "INT",
                "userInterface": {
                    "control": "SPIN_BOX",
                    "label": "Maximum Failed Tasks Count",
                },
                "minValue": 0,
                "value": self.get_max_failed_tasks_count(),
            },
            {
                "name": "deadline:maxRetriesPerTask",
                "description": "Maximum number of times that a Task will retry before it's marked as failed.",
                "type": "INT",
                "userInterface": {
                    "control": "SPIN_BOX",
                    "label": "Maximum Retries Per Task",
                },
                "minValue": 0,
                "value": self.get_max_retries_per_task(),
            },
            {"name": "deadline:priority", "type": "INT", "value": self.get_priority()},
        ]

    def to_dict(self) -> list[dict]:
        """
        Returns the OpenJob SharedSettings object as list of dictionaries

        :return: OpenJob SharedSettings as list of dictionaries
        :rtype: dict
        """
        return self.parameter_values

    def get_initial_state(self) -> str:
        """
        Returns the OpenJob Initial State value

        :return: OpenJob Initial State
        :rtype: str
        """
        return self.source_shared_settings.initial_state

    def get_max_failed_tasks_count(self) -> int:
        """
        Returns the OpenJob Max Failed Task Count value

        :return: OpenJob Max Failed Task Count
        :rtype: int
        """
        return self.source_shared_settings.maximum_failed_tasks_count

    def get_max_retries_per_task(self) -> int:
        """
        Returns the OpenJob Max Retries Per Task value

        :return: OpenJob Max Retries Per Task
        :rtype: int
        """
        return self.source_shared_settings.maximum_retries_per_task

    def get_priority(self) -> int:
        """
        Return the OpenJob Priority value

        :return: OpenJob Priority
        :rtype: int
        """
        # TODO Add priority to the settings
        return 1


class UnrealOpenJob(UnrealOpenJobEntity):
    """
    Open Job for Unreal Engine
    """

    def __init__(
        self,
        file_path: str,
        name: str = None,
        steps: list[UnrealOpenJobStep] = None,
        environments: list[UnrealOpenJobEnvironment] = None,
        extra_parameters: list[unreal.ParameterDefinition] = None,
        job_shared_settings: unreal.DeadlineCloudJobSharedSettingsStruct = None
    ):
        """
        :param file_path: Path to the open job template file
        :type file_path: str
        
        :param name: Name of the job
        :type name: str
        
        :param steps: List of steps to be executed by deadline cloud
        :type steps: list
        
        :param environments: List of environments to be used by deadline cloud
        :type environments: list
        
        :param extra_parameters: List of additional parameters to be added to the job
        :type extra_parameters: list
        """

        super().__init__(JobTemplate, file_path, name)

        if self._name is None:
            self._name = self.get_template_object().get('name')

        self._extra_parameters: list[unreal.ParameterDefinition] = extra_parameters or []
        self._steps: list[UnrealOpenJobStep] = steps
        self._environments: list[UnrealOpenJobEnvironment] = environments
        self._job_shared_settings = job_shared_settings

    @property
    def job_shared_settings(self):
        return self._job_shared_settings

    @job_shared_settings.setter
    def job_shared_settings(self, value):
        self._job_shared_settings = value

    @classmethod
    def from_data_asset(cls, data_asset: unreal.DeadlineCloudJob) -> "UnrealOpenJob":
        steps = [UnrealOpenJobStep.from_data_asset(step) for step in data_asset.steps]
        for step in steps:
            step.host_requirements = data_asset.job_preset_struct.host_requirements

        shared_settings = data_asset.job_preset_struct.job_shared_settings

        return cls(
            file_path=data_asset.path_to_template,
            name=None if shared_settings.name in ['', 'Untitled'] else shared_settings.name,
            steps=steps,
            environments=[UnrealOpenJobEnvironment.from_data_asset(env) for env in data_asset.environments],
            extra_parameters=data_asset.get_job_parameters(),
            job_shared_settings=shared_settings
        )

    def _build_parameter_values(self) -> list:
        """
        :return: Parameter values list
        :rtype: list
        """
        job_template_object = self.get_template_object()
        parameter_values = []
        for param in job_template_object['parameterDefinitions']:
            extra_param = next((extra_p for extra_p in self._extra_parameters if extra_p.name == param['name']), None)
            if extra_param:
                python_class = PARAMETER_DEFINITION_MAPPING.get(param['type']).python_class
                param_value = python_class(extra_param.value)
            else:
                param_value = param.get('default')

            parameter_values.append(dict(name=param['name'], value=param_value))

        if self._job_shared_settings:
            parameter_values += JobSharedSettings(self._job_shared_settings).to_dict()

        return parameter_values

    def _get_asset_references(self) -> AssetReferences:
        return AssetReferences()

    def _check_parameters_consistency(self):
        import open_job_template_api

        template = self.get_template_object()

        result = open_job_template_api.ParametersConsistencyChecker.check_parameters_consistency(
            yaml_parameters=[(p['name'], p['type']) for p in template['parameterDefinitions']],
            data_asset_parameters=[(p.name, p.type.name) for p in self._extra_parameters]
        )
        result.reason = f'OpenJob: ' + result.reason
        return result

    def _build_template(self) -> JobTemplate:
        job_template = self.template_class(
            specificationVersion=settings.JOB_TEMPLATE_VERSION,
            name=self.name,
            parameterDefinitions=[
                PARAMETER_DEFINITION_MAPPING.get(param['type']).job_parameter_openjd_class(**param)
                for param in self.get_template_object()['parameterDefinitions']
            ],
            steps=[s.build_template() for s in self._steps],
            jobEnvironments=[e.build_template() for e in self._environments] if self._environments else None
        )
        return job_template

    @staticmethod
    def serialize_template(template: JobTemplate):
        def delete_none(_dict):
            for key, value in list(_dict.items()):
                if isinstance(value, dict):
                    delete_none(value)
                elif value is None:
                    del _dict[key]
                elif isinstance(value, list):
                    for v_i in value:
                        if isinstance(v_i, dict):
                            delete_none(v_i)

            return _dict

        template_json = json.loads(template.json())
        ordered_keys = ['specificationVersion', 'name', 'parameterDefinitions', 'jobEnvironments', 'steps']
        ordered_data = dict(OrderedDict((key, template_json[key]) for key in ordered_keys))
        ordered_data = delete_none(ordered_data)
        return ordered_data

    def create_job_bundle(self):
        job_template = self.build_template()

        job_bundle_path = create_job_history_bundle_dir("Unreal", self.name)
        unreal.log(f"Job bundle path: {job_bundle_path}")

        with open(job_bundle_path + "/template.yaml", "w", encoding="utf8") as f:
            job_template_dict = UnrealOpenJob.serialize_template(job_template)
            deadline_yaml_dump(job_template_dict, f, indent=1)

        with open(job_bundle_path + "/parameter_values.yaml", "w", encoding="utf8") as f:
            param_values = self._build_parameter_values()
            deadline_yaml_dump(dict(parameterValues=param_values), f, indent=1)

        with open(job_bundle_path + "/asset_references.yaml", "w", encoding="utf8") as f:
            asset_references = self._get_asset_references()
            deadline_yaml_dump(asset_references.to_dict(), f, indent=1)

        return job_bundle_path


class RenderUnrealOpenJob(UnrealOpenJob):
    """
    Unreal Open Job for rendering Unreal Engine projects
    """

    job_environment_map = {
        unreal.DeadlineCloudUgsEnvironment: UnrealOpenJobUgsEnvironment
    }

    job_step_map = {
        unreal.DeadlineCloudRenderStep: RenderUnrealOpenJobStep
    }

    def __init__(
            self,
            file_path: str,
            name: str = None,
            steps: list = None,
            environments: list = None,
            extra_parameters: list = None,
            job_shared_settings: unreal.DeadlineCloudJobSharedSettingsStruct = None,
            mrq_job: unreal.MoviePipelineExecutorJob = None,
            changelist_number: int = None,
    ):
        self._mrq_job = mrq_job
        self._changelist_number = changelist_number

        self._dependency_collector = DependencyCollector()

        self._manifest_path = ''

        super().__init__(file_path, name, steps, environments, extra_parameters, job_shared_settings)

        if self._name is None and isinstance(self._mrq_job, unreal.MoviePipelineExecutorJob):
            self._name = self._mrq_job.job_name

    @property
    def mrq_job(self):
        return self._mrq_job

    @mrq_job.setter
    def mrq_job(self, value):
        self._mrq_job = value

        for step in self._steps:
            step.host_requirements = self._mrq_job.preset_overrides.host_requirements

            if isinstance(step, RenderUnrealOpenJobStep):
                step.shots_count = len(self._mrq_job.shot_info)
                step.queue_manifest_path = self._save_manifest_file()

        self.job_shared_settings = self._mrq_job.preset_overrides.job_shared_settings

        # Job name set order:
        #   0. Job preset override (high priority)
        #   1. Get from data asset job preset struct
        #   2. Get from YAML template
        #   4. Get from mrq job name (shot name)
        if self.job_shared_settings.name not in ['', 'Untitled']:
            self._name = self.job_shared_settings.name

        if self._name is None:
            self._name = self._mrq_job.job_name

    @property
    def manifest_path(self):
        return self._manifest_path

    @classmethod
    def from_data_asset(cls, data_asset: unreal.DeadlineCloudRenderJob) -> "RenderUnrealOpenJob":
        if not RenderUnrealOpenJob.render_job_asset_has_render_step(data_asset):
            raise Exception('RenderJob data asset should have RenderStep')

        steps = []
        for source_step in data_asset.steps:
            job_step_cls = cls.job_step_map.get(type(source_step), UnrealOpenJobStep)
            job_step = job_step_cls.from_data_asset(source_step)
            job_step.host_requirements = data_asset.job_preset_struct.host_requirements
            steps.append(job_step)

        environments = []
        for source_environment in data_asset.environments:
            job_env_cls = cls.job_environment_map.get(type(source_environment), UnrealOpenJobEnvironment)
            job_env = job_env_cls.from_data_asset(source_environment)
            environments.append(job_env)

        shared_settings = data_asset.job_preset_struct.job_shared_settings

        return cls(
            file_path=data_asset.path_to_template,
            name=None if shared_settings.name in ['', 'Untitled'] else shared_settings.name,
            steps=steps,
            environments=environments,
            extra_parameters=data_asset.get_job_parameters(),
            job_shared_settings=shared_settings,
            changelist_number=None,  # TODO data_asset.changelist_number,
        )

    @staticmethod
    def render_job_asset_has_render_step(data_asset: unreal.DeadlineCloudRenderJob) -> bool:
        """ Check if given Render Job data asset has Render step or not """
        render_step = next((s for s in data_asset.steps if isinstance(s, unreal.DeadlineCloudRenderStep)), None)
        return render_step is not None

    @staticmethod
    def update_job_parameter_values(
            job_parameter_values: list[dict[str, Any]],
            job_parameter_name: str,
            job_parameter_value: Any
    ) -> list[dict[str, Any]]:
        param = next((p for p in job_parameter_values if p['name'] == job_parameter_name), None)
        if param:
            param['value'] = job_parameter_value
        else:
            job_parameter_values.append(dict(name=job_parameter_name, value=job_parameter_value))

        return job_parameter_values

    def _build_parameter_values(self):

        parameter_values = super()._build_parameter_values()

        parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=parameter_values,
            job_parameter_name=OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS,
            job_parameter_value=' '.join(self._get_ue_cmd_args())
        )

        parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=parameter_values,
            job_parameter_name=OpenJobParameterNames.UNREAL_PROJECT_PATH,
            job_parameter_value=common.get_project_file_path()
        )

        for env in self._environments:
            for parameter in env.get_used_job_parameter_values():
                RenderUnrealOpenJob.update_job_parameter_values(
                    job_parameter_values=parameter_values,
                    job_parameter_name=parameter['name'],
                    job_parameter_value=parameter['value']
                )

        return parameter_values

    def _get_ue_cmd_args(self) -> list[str]:
        cmd_args = []

        in_process_executor_settings = unreal.get_default_object(unreal.MoviePipelineInProcessExecutorSettings)

        # Append all of inherited command line arguments from the editor
        inherited_cmds: str = in_process_executor_settings.inherited_command_line_arguments

        # Sanitize the commandline by removing any execcmds that may have passed through the commandline.
        # We remove the execcmds because, in some cases, users may execute a script that is local to their editor build
        # for some automated workflow but this is not ideal on the farm.
        # We will expect all custom startup commands for rendering to go through the `Start Command` in the MRQ settings
        inherited_cmds = re.sub(pattern=".*(?P<cmds>-execcmds=[\s\S]+[\'\"])", repl="", string=inherited_cmds)
        cmd_args.extend(inherited_cmds.split(' '))

        # Append all of additional command line arguments from the editor
        additional_cmds: str = in_process_executor_settings.additional_command_line_arguments
        cmd_args.extend(additional_cmds.split(' '))

        # Initializes a single instance of every setting
        # so that even non-user-configured settings have a chance to apply their default values
        self._mrq_job.get_configuration().initialize_transient_settings()

        job_url_params = []
        job_cmd_args = []
        job_device_profile_cvars = []
        job_exec_cmds = []
        for setting in self._mrq_job.get_configuration().get_all_settings():
            (
                job_url_params,
                job_cmd_args,
                job_device_profile_cvars,
                job_exec_cmds
            ) = setting.build_new_process_command_line_args(
                out_unreal_url_params=job_url_params,
                out_command_line_args=job_cmd_args,
                out_device_profile_cvars=job_device_profile_cvars,
                out_exec_cmds=job_exec_cmds,
            )
            # TODO is that necessary?
            # Set the game override
            # if setting.get_class() == unreal.MoviePipelineGameOverrideSetting.static_class():
            #     game_override_class = setting.game_mode_override

        # Apply job cmd arguments
        cmd_args.extend(job_cmd_args)

        if job_device_profile_cvars:
            # -dpcvars="arg0,arg1,..."
            cmd_args.append(
                '-dpcvars="{}"'.format(",".join(job_device_profile_cvars))
            )

        if job_exec_cmds:
            # -execcmds="cmd0,cmd1,..."
            cmd_args.append(
                '-execcmds="{}"'.format(",".join(job_exec_cmds))
            )

        extra_cmd_args = next((str(p.value) for p in self._extra_parameters if p.name == 'ExtraCmdArgs'), None)
        if extra_cmd_args:
            cleared_extra_cmds_args = re.sub(
                pattern=".*(?P<cmds>-execcmds=[\s\S]+[\'\"])",
                repl="", string=extra_cmd_args
            )
            if cleared_extra_cmds_args:
                cmd_args.extend(cleared_extra_cmds_args.split(' '))

        # remove duplicates
        cmd_args = list(set(cmd_args))

        # remove empty args
        cmd_args = [a for a in cmd_args if a != '']

        return cmd_args

    def _collect_mrq_job_dependencies(self) -> list[str]:
        """
        Collects the dependencies of the Level and LevelSequence that used in MRQ Job.

        Use :class:`deadline.unreal_submitter.unreal_dependency_collector.collector.DependencyCollector` for collecting

        :return: List of the dependencies
        :rtype: list[str]
        """
        level_sequence_path = common.soft_obj_path_to_str(self._mrq_job.sequence)
        level_sequence_path = os.path.splitext(level_sequence_path)[0]

        level_path = common.soft_obj_path_to_str(self._mrq_job.map)
        level_path = os.path.splitext(level_path)[0]

        level_sequence_dependencies = self._dependency_collector.collect(
            level_sequence_path, filter_method=DependencyFilters.dependency_in_game_folder
        )

        level_dependencies = self._dependency_collector.collect(
            level_path, filter_method=DependencyFilters.dependency_in_game_folder
        )

        return level_sequence_dependencies + level_dependencies + [level_sequence_path, level_path]

    def _get_asset_references(self) -> AssetReferences:
        """
        Build asset references of the OpenJob with the given MRQ Job.

        Return :class:`deadline.client.job_bundle.submission.AssetReferences` instance

        :return: AssetReferences dataclass instance
        :rtype: :class:`deadline.client.job_bundle.submission.AssetReferences`
        """

        asset_references = AssetReferences()

        # add dependencies to attachments
        os_dependencies = []
        job_dependencies = self._collect_mrq_job_dependencies()
        for dependency in job_dependencies:
            os_dependency = common.os_path_from_unreal_path(dependency, with_ext=True)
            if os.path.exists(os_dependency):
                os_dependencies.append(os_dependency)

        asset_references.input_filenames.update(os_dependencies)

        # step_input_files = []
        # for step in self._steps:
        #     step_input_files.extend(step.get_step_input_files())
        # asset_references.input_filenames.update(step_input_files)

        # add manifest to attachments
        if os.path.exists(self._manifest_path):
            asset_references.input_filenames.add(self._manifest_path)

        # add other input files to attachments
        job_input_files = [
            common.os_abs_from_relative(input_file.file_path)
            for input_file in self._mrq_job.preset_overrides.job_attachments.input_files.files.paths
        ]
        for input_file in job_input_files:
            if os.path.exists(input_file):
                asset_references.input_filenames.add(input_file)

        # required input directories
        for sub_dir in ["Config", "Binaries"]:
            input_directory = common.os_abs_from_relative(sub_dir)
            if os.path.exists(input_directory):
                asset_references.input_directories.add(input_directory)

        # input directories
        job_input_directories = [
            common.os_abs_from_relative(input_directory.path)
            for input_directory in self._mrq_job.preset_overrides.job_attachments.input_directories.directories.paths
        ]
        for input_dir in job_input_directories:
            if os.path.exists(input_dir):
                asset_references.input_directories.add(input_dir)

        # output directories
        job_output_directories = [
            common.os_abs_from_relative(output_directory.path)
            for output_directory in self._mrq_job.preset_overrides.job_attachments.output_directories.directories.paths
        ]
        for output_dir in job_output_directories:
            asset_references.input_directories.add(output_dir)

        output_setting = self._mrq_job.get_configuration().find_setting_by_class(
            unreal.MoviePipelineOutputSetting
        )
        output_path = output_setting.output_directory.path

        path_context = common.get_path_context_from_mrq_job(self._mrq_job)
        output_path = output_path.format_map(path_context).rstrip("/")

        asset_references.output_directories.update([output_path])

        return asset_references

    def _save_manifest_file(self):
        new_queue = unreal.MoviePipelineQueue()
        new_job = new_queue.duplicate_job(self._mrq_job)

        # In duplicated job remove empty auto-detected files since we don't want them to be saved in manifest
        # List of the files is moved to OpenJob attachments
        new_job.preset_overrides.job_attachments.input_files.auto_detected = (
            unreal.DeadlineCloudFileAttachmentsArray()
        )

        duplicated_queue, manifest_path = unreal.MoviePipelineEditorLibrary.save_queue_to_manifest_file(new_queue)
        serialized_manifest = unreal.MoviePipelineEditorLibrary.convert_manifest_file_to_string(manifest_path)

        movie_render_pipeline_dir = os.path.join(
            unreal.SystemLibrary.get_project_saved_directory(),
            "MovieRenderPipeline",
            "RenderJobManifests",
        )
        os.makedirs(movie_render_pipeline_dir, exist_ok=True)

        render_job_manifest_path = unreal.Paths.create_temp_filename(
            movie_render_pipeline_dir,
            prefix='RenderJobManifest',
            extension='.utxt'
        )

        with open(render_job_manifest_path, 'w') as manifest:
            unreal.log(f"Saving Manifest file `{render_job_manifest_path}`")
            manifest.write(serialized_manifest)

        self._manifest_path = unreal.Paths.convert_relative_path_to_full(render_job_manifest_path)

        return self._manifest_path
