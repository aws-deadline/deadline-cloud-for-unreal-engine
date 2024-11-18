import os
import re
import sys
import json
import unreal
from collections import OrderedDict
from typing import Any, Union, Optional
from dataclasses import dataclass, asdict

from openjd.model.v2023_09 import JobTemplate

from deadline.client.job_bundle.submission import AssetReferences
from deadline.client.job_bundle import deadline_yaml_dump, create_job_history_bundle_dir

from deadline.unreal_submitter import common
from deadline.unreal_submitter import settings
from deadline.unreal_submitter.perforce_api import PerforceApi
from deadline.unreal_submitter.unreal_dependency_collector import (
    DependencyCollector,
    DependencyFilters,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (
    UnrealOpenJobEntity,
    OpenJobParameterNames,
    PARAMETER_DEFINITION_MAPPING,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
    UnrealOpenJobStep,
    RenderUnrealOpenJobStep,
    UnrealOpenJobStepParameterDefinition,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (
    UnrealOpenJobEnvironment,
    UnrealOpenJobUgsEnvironment,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_shared_settings import (
    JobSharedSettings,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_parameters_consistency import (
    ParametersConsistencyChecker,
)

from deadline.unreal_logger import get_logger


logger = get_logger()

perforce_api = PerforceApi()


@dataclass
class UnrealOpenJobParameterDefinition:
    name: str
    type: str
    value: Union[int, float, str, None] = None

    @classmethod
    def from_unreal_param_definition(cls, u_param: unreal.ParameterDefinition):
        build_kwargs = dict(name=u_param.name, type=u_param.type.name)
        if u_param.value:
            python_class = PARAMETER_DEFINITION_MAPPING.get(u_param.type.name).python_class
            build_kwargs["value"] = python_class(u_param.value)
        return cls(**build_kwargs)

    def to_dict(self):
        return asdict(self)


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
        extra_parameters: list[UnrealOpenJobParameterDefinition] = None,
        job_shared_settings: unreal.DeadlineCloudJobSharedSettingsStruct = None,
        asset_references: AssetReferences = AssetReferences(),
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

        :param asset_references: AssetReferences object
        :type asset_references: AssetReferences
        """

        super().__init__(JobTemplate, file_path, name)

        if self._name is None:
            self._name = self.get_template_object().get("name")

        self._extra_parameters: list[UnrealOpenJobParameterDefinition] = extra_parameters or []
        self._steps: list[UnrealOpenJobStep] = steps
        self._environments: list[UnrealOpenJobEnvironment] = environments
        self._job_shared_settings = job_shared_settings
        self._asset_references = asset_references

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
            file_path=data_asset.path_to_template.file_path,
            name=None if shared_settings.name in ["", "Untitled"] else shared_settings.name,
            steps=steps,
            environments=[
                UnrealOpenJobEnvironment.from_data_asset(env) for env in data_asset.environments
            ],
            extra_parameters=[
                UnrealOpenJobParameterDefinition.from_unreal_param_definition(param)
                for param in data_asset.get_job_parameters()
            ],
            job_shared_settings=shared_settings,
        )

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
        ordered_keys = [
            "specificationVersion",
            "name",
            "parameterDefinitions",
            "jobEnvironments",
            "steps",
        ]
        ordered_data = dict(OrderedDict((key, template_json[key]) for key in ordered_keys))
        ordered_data = delete_none(ordered_data)
        return ordered_data

    def _find_extra_parameter_by_name(
        self, name: str
    ) -> Optional[UnrealOpenJobParameterDefinition]:
        return next((p for p in self._extra_parameters if p.name == name), None)

    def _build_parameter_values(self) -> list:
        """
        Build and return list of parameter values for the OpenJob

        :return: Parameter values list of dictionaries
        :rtype: list
        """

        job_template_object = self.get_template_object()
        parameter_values = []
        for yaml_p in job_template_object["parameterDefinitions"]:
            extra_p = next((p for p in self._extra_parameters if p.name == yaml_p["name"]), None)
            value = extra_p.value if extra_p else yaml_p.get("default")
            parameter_values.append(dict(name=yaml_p["name"], value=value))

        if self._job_shared_settings:
            parameter_values += JobSharedSettings(self._job_shared_settings).to_dict()

        return parameter_values

    def _check_parameters_consistency(self):
        result = ParametersConsistencyChecker.check_job_parameters_consistency(
            job_template_path=self.file_path,
            job_parameters=[p.to_dict() for p in self._extra_parameters],
        )

        result.reason = "OpenJob: " + result.reason

        return result

    def _build_template(self) -> JobTemplate:
        job_template = self.template_class(
            specificationVersion=settings.JOB_TEMPLATE_VERSION,
            name=self.name,
            parameterDefinitions=[
                PARAMETER_DEFINITION_MAPPING.get(param["type"]).job_parameter_openjd_class(**param)
                for param in self.get_template_object()["parameterDefinitions"]
            ],
            steps=[s.build_template() for s in self._steps],
            jobEnvironments=(
                [e.build_template() for e in self._environments] if self._environments else None
            ),
        )
        return job_template

    def get_asset_references(self) -> AssetReferences:
        asset_references = super().get_asset_references()

        if self._asset_references:
            asset_references = asset_references.union(self._asset_references)

        for step in self._steps:
            asset_references = asset_references.union(step.get_asset_references())

        for environment in self._environments:
            asset_references = asset_references.union(environment.get_asset_references())

        return asset_references

    def create_job_bundle(self):
        job_template = self.build_template()

        job_bundle_path = create_job_history_bundle_dir("Unreal", self.name)
        logger.info(f"Job bundle path: {job_bundle_path}")

        with open(job_bundle_path + "/template.yaml", "w", encoding="utf8") as f:
            job_template_dict = UnrealOpenJob.serialize_template(job_template)
            deadline_yaml_dump(job_template_dict, f, indent=1)

        with open(job_bundle_path + "/parameter_values.yaml", "w", encoding="utf8") as f:
            param_values = self._build_parameter_values()
            deadline_yaml_dump(dict(parameterValues=param_values), f, indent=1)

        with open(job_bundle_path + "/asset_references.yaml", "w", encoding="utf8") as f:
            asset_references = self.get_asset_references()
            deadline_yaml_dump(asset_references.to_dict(), f, indent=1)

        return job_bundle_path


class RenderUnrealOpenJob(UnrealOpenJob):
    """
    Unreal Open Job for rendering Unreal Engine projects
    """

    job_environment_map = {unreal.DeadlineCloudUgsEnvironment: UnrealOpenJobUgsEnvironment}

    job_step_map = {unreal.DeadlineCloudRenderStep: RenderUnrealOpenJobStep}

    def __init__(
        self,
        file_path: str,
        name: str = None,
        steps: list = None,
        environments: list = None,
        extra_parameters: list = None,
        job_shared_settings: unreal.DeadlineCloudJobSharedSettingsStruct = None,
        asset_references: AssetReferences = AssetReferences(),
        mrq_job: unreal.MoviePipelineExecutorJob = None,
    ):
        super().__init__(
            file_path,
            name,
            steps,
            environments,
            extra_parameters,
            job_shared_settings,
            asset_references,
        )

        self._mrq_job = mrq_job

        self._dependency_collector = DependencyCollector()

        self._manifest_path = ""
        self._extra_cmd_args_file_path = ""

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
                step.mrq_job = self._mrq_job

                for parameter in self._mrq_job.step_parameter_overrides.parameters:
                    step.update_extra_parameter(
                        UnrealOpenJobStepParameterDefinition.from_unreal_param_definition(parameter)
                    )

        self._extra_parameters = [
            UnrealOpenJobParameterDefinition.from_unreal_param_definition(p)
            for p in self._mrq_job.parameter_definition_overrides.parameters
        ]

        self.job_shared_settings = self._mrq_job.preset_overrides.job_shared_settings

        # Job name set order:
        #   0. Job preset override (high priority)
        #   1. Get from data asset job preset struct
        #   2. Get from YAML template
        #   4. Get from mrq job name (shot name)
        if self.job_shared_settings.name not in ["", "Untitled"]:
            self._name = self.job_shared_settings.name

        if self._name is None:
            self._name = self._mrq_job.job_name

    @property
    def manifest_path(self):
        return self._manifest_path

    @classmethod
    def from_data_asset(cls, data_asset: unreal.DeadlineCloudRenderJob) -> "RenderUnrealOpenJob":
        render_steps_count = RenderUnrealOpenJob.render_steps_count(data_asset)
        if not render_steps_count == 1:
            raise Exception(
                f"RenderJob data asset should have exactly 1 Render Step. "
                f"Currently it has {render_steps_count} Render Steps"
            )

        steps = []
        for source_step in data_asset.steps:
            job_step_cls = cls.job_step_map.get(type(source_step), UnrealOpenJobStep)
            job_step = job_step_cls.from_data_asset(source_step)
            job_step.host_requirements = data_asset.job_preset_struct.host_requirements
            steps.append(job_step)

        environments = []
        for source_environment in data_asset.environments:
            job_env_cls = cls.job_environment_map.get(
                type(source_environment), UnrealOpenJobEnvironment
            )
            job_env = job_env_cls.from_data_asset(source_environment)
            environments.append(job_env)

        shared_settings = data_asset.job_preset_struct.job_shared_settings

        return cls(
            file_path=data_asset.path_to_template.file_path,
            name=None if shared_settings.name in ["", "Untitled"] else shared_settings.name,
            steps=steps,
            environments=environments,
            extra_parameters=[
                UnrealOpenJobParameterDefinition.from_unreal_param_definition(param)
                for param in data_asset.get_job_parameters()
            ],
            job_shared_settings=shared_settings,
        )

    @classmethod
    def from_mrq_job(
        cls, mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob
    ) -> "RenderUnrealOpenJob":
        render_unreal_open_job = cls.from_data_asset(mrq_job.job_preset)
        render_unreal_open_job.mrq_job = mrq_job
        return render_unreal_open_job

    @staticmethod
    def render_steps_count(data_asset: unreal.DeadlineCloudRenderJob) -> int:
        """Count Render Step in the given Render Job data asset"""
        return sum(isinstance(s, unreal.DeadlineCloudRenderStep) for s in data_asset.steps)

    @staticmethod
    def update_job_parameter_values(
        job_parameter_values: list[dict[str, Any]],
        job_parameter_name: str,
        job_parameter_value: Any,
        create_if_not_exists: bool = False,
    ) -> list[dict[str, Any]]:
        param = next((p for p in job_parameter_values if p["name"] == job_parameter_name), None)
        if param:
            param["value"] = job_parameter_value
        elif create_if_not_exists:
            job_parameter_values.append(dict(name=job_parameter_name, value=job_parameter_value))

        return job_parameter_values

    def _have_ugs_environment(self) -> bool:
        return (
            next(
                (env for env in self._environments if isinstance(env, UnrealOpenJobUgsEnvironment)),
                None,
            )
            is not None
        )

    def _write_cmd_args_to_file(self, cmd_args_str: str) -> str:

        destination_dir = os.path.join(
            unreal.SystemLibrary.get_project_saved_directory(),
            "UnrealDeadlineCloudService",
            "ExtraCmdArgs",
        )
        os.makedirs(destination_dir, exist_ok=True)

        cmd_args_file = unreal.Paths.create_temp_filename(
            destination_dir, prefix="ExtraCmdArgs", extension=".txt"
        )

        with open(cmd_args_file, "w") as f:
            logger.info(f"Saving ExtraCmdArgs file `{cmd_args_file}`")
            f.write(cmd_args_str)

        self._extra_cmd_args_file_path = unreal.Paths.convert_relative_path_to_full(cmd_args_file)
        return self._extra_cmd_args_file_path

    def _build_parameter_values(self):

        parameter_values = super()._build_parameter_values()

        cmd_args_str = " ".join(self._get_ue_cmd_args())

        for p in parameter_values:
            # skip params predefined in YAML or by given extra parameters
            # if it not ExtraCmdArgs since we want to update them with mrq job args
            if p["value"] is not None and p["name"] != OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS:
                continue

            if (
                p["name"] == OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS
                and len(cmd_args_str) <= 1024
            ):
                parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                    job_parameter_values=parameter_values,
                    job_parameter_name=OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS,
                    job_parameter_value=cmd_args_str,
                )

            if p["name"] == OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS_FILE:
                cmd_args_file_path = self._write_cmd_args_to_file(cmd_args_str).replace("\\", "/")

                parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                    job_parameter_values=parameter_values,
                    job_parameter_name=OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS_FILE,
                    job_parameter_value=cmd_args_file_path,
                )

            if p["name"] == OpenJobParameterNames.UNREAL_PROJECT_PATH:
                parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                    job_parameter_values=parameter_values,
                    job_parameter_name=OpenJobParameterNames.UNREAL_PROJECT_PATH,
                    job_parameter_value=common.get_project_file_path(),
                )

            if p["name"] == OpenJobParameterNames.PERFORCE_STREAM_PATH:
                parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                    job_parameter_values=parameter_values,
                    job_parameter_name=OpenJobParameterNames.PERFORCE_STREAM_PATH,
                    job_parameter_value=perforce_api.get_stream_path(),
                )

            if p["name"] == OpenJobParameterNames.PERFORCE_CHANGELIST_NUMBER:
                parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                    job_parameter_values=parameter_values,
                    job_parameter_name=OpenJobParameterNames.PERFORCE_CHANGELIST_NUMBER,
                    job_parameter_value=str(perforce_api.get_latest_changelist_number())
                    or "latest",
                )

            if p["name"] == OpenJobParameterNames.UNREAL_PROJECT_NAME:
                parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                    job_parameter_values=parameter_values,
                    job_parameter_name=OpenJobParameterNames.UNREAL_PROJECT_NAME,
                    job_parameter_value=common.get_project_name(),
                )

            if p["name"] == OpenJobParameterNames.UNREAL_PROJECT_RELATIVE_PATH:
                client_root = perforce_api.get_client_root()
                unreal_project_path = common.get_project_file_path().replace("\\", "/")
                unreal_project_relative_path = unreal_project_path.replace(client_root, "")
                unreal_project_relative_path = unreal_project_relative_path.lstrip("/")

                parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                    job_parameter_values=parameter_values,
                    job_parameter_name=OpenJobParameterNames.UNREAL_PROJECT_RELATIVE_PATH,
                    job_parameter_value=unreal_project_relative_path,
                )

            if p["name"] == OpenJobParameterNames.UNREAL_EXECUTABLE_RELATIVE_PATH:
                client_root = perforce_api.get_client_root()
                unreal_executable_path = sys.executable.replace("\\", "/")
                unreal_executable_relative_path = unreal_executable_path.replace(client_root, "")
                unreal_executable_relative_path = unreal_executable_relative_path.lstrip("/")

                parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                    job_parameter_values=parameter_values,
                    job_parameter_name=OpenJobParameterNames.UNREAL_EXECUTABLE_RELATIVE_PATH,
                    job_parameter_value=unreal_executable_relative_path,
                )

        return parameter_values

    def _get_ue_cmd_args(self) -> list[str]:
        cmd_args = []

        in_process_executor_settings = unreal.get_default_object(
            unreal.MoviePipelineInProcessExecutorSettings
        )

        # Append all of inherited command line arguments from the editor
        inherited_cmds: str = in_process_executor_settings.inherited_command_line_arguments

        # Sanitize the commandline by removing any execcmds that may have passed through the commandline.
        # We remove the execcmds because, in some cases, users may execute a script that is local to their editor build
        # for some automated workflow but this is not ideal on the farm.
        # We will expect all custom startup commands for rendering to go through the `Start Command` in the MRQ settings
        inherited_cmds = re.sub(pattern='(-execcmds="[^"]*")', repl="", string=inherited_cmds)
        inherited_cmds = re.sub(pattern="(-execcmds='[^']*')", repl="", string=inherited_cmds)
        cmd_args.extend(inherited_cmds.split(" "))

        # Append all of additional command line arguments from the editor
        additional_cmds: str = in_process_executor_settings.additional_command_line_arguments
        cmd_args.extend(additional_cmds.split(" "))

        # Initializes a single instance of every setting
        # so that even non-user-configured settings have a chance to apply their default values
        self._mrq_job.get_configuration().initialize_transient_settings()

        job_url_params = []
        job_cmd_args = []
        job_device_profile_cvars = []
        job_exec_cmds = []
        for setting in self._mrq_job.get_configuration().get_all_settings():
            (job_url_params, job_cmd_args, job_device_profile_cvars, job_exec_cmds) = (
                setting.build_new_process_command_line_args(
                    out_unreal_url_params=job_url_params,
                    out_command_line_args=job_cmd_args,
                    out_device_profile_cvars=job_device_profile_cvars,
                    out_exec_cmds=job_exec_cmds,
                )
            )

        # Apply job cmd arguments
        cmd_args.extend(job_cmd_args)

        if job_device_profile_cvars:
            cmd_args.append('-dpcvars="{}"'.format(",".join(job_device_profile_cvars)))

        if job_exec_cmds:
            cmd_args.append('-execcmds="{}"'.format(",".join(job_exec_cmds)))

        extra_cmd_args = next(
            (
                p.value
                for p in self._extra_parameters
                if p.name == OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS
            ),
            None,
        )
        if extra_cmd_args:
            cleared_extra_cmds_args = re.sub(
                pattern='(-execcmds="[^"]*")', repl="", string=extra_cmd_args
            )
            cleared_extra_cmds_args = re.sub(
                pattern="(-execcmds='[^']*')", repl="", string=cleared_extra_cmds_args
            )
            if cleared_extra_cmds_args:
                cmd_args.extend(cleared_extra_cmds_args.split(" "))

        # remove duplicates
        cmd_args = list(set(cmd_args))

        # remove empty args
        cmd_args = [a for a in cmd_args if a != ""]

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

    def get_asset_references(self) -> AssetReferences:
        """
        Build asset references of the OpenJob with the given MRQ Job.

        Return :class:`deadline.client.job_bundle.submission.AssetReferences` instance

        :return: AssetReferences dataclass instance
        :rtype: :class:`deadline.client.job_bundle.submission.AssetReferences`
        """

        asset_references = super().get_asset_references()
        logger.info(f"RENDER JOB ASSET REFERENCES: {asset_references.to_dict()}")

        if not self._have_ugs_environment():
            # add dependencies to attachments
            os_dependencies = []
            job_dependencies = self._collect_mrq_job_dependencies()
            for dependency in job_dependencies:
                os_dependency = common.os_path_from_unreal_path(dependency, with_ext=True)
                if os.path.exists(os_dependency):
                    os_dependencies.append(os_dependency)

            asset_references.input_filenames.update(os_dependencies)

            # required input directories
            for sub_dir in ["Config", "Binaries"]:
                input_directory = common.os_abs_from_relative(sub_dir)
                if os.path.exists(input_directory):
                    asset_references.input_directories.add(input_directory)

        # add ue cmd args file
        if os.path.exists(self._extra_cmd_args_file_path):
            asset_references.input_filenames.add(self._extra_cmd_args_file_path)

        # add other input files to attachments
        job_input_files = [
            common.os_abs_from_relative(input_file.file_path)
            for input_file in self._mrq_job.preset_overrides.job_attachments.input_files.files.paths
        ]
        for input_file in job_input_files:
            if os.path.exists(input_file):
                asset_references.input_filenames.add(input_file)

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
