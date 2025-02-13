import os
import re
import sys
import json
import unreal
from enum import IntEnum
from typing import Any, Optional
from collections import OrderedDict
from dataclasses import dataclass, asdict

from openjd.model.v2023_09 import JobTemplate

from deadline.client.job_bundle.submission import AssetReferences
from deadline.client.job_bundle import deadline_yaml_dump, create_job_history_bundle_dir

from deadline.unreal_submitter import common, exceptions, settings
from deadline.unreal_submitter.perforce_api import PerforceApi
from deadline.unreal_submitter.unreal_dependency_collector import (
    DependencyCollector,
    DependencyFilters,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (
    Template,
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
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step_host_requirements import (
    HostRequirementsHelper,
)

from deadline.unreal_logger import get_logger


logger = get_logger()


class TransferProjectFilesStrategy(IntEnum):
    """
    Enumeration of ways of transferring project files

    :cvar S3: Default, with S3 file manager
    :cvar P4: with Perforce API
    :cvar UGS: with UnrealGameSync API
    """

    S3 = 0
    P4 = 1
    UGS = 2


@dataclass
class UnrealOpenJobParameterDefinition:
    """
    Dataclass for storing and managing OpenJob Parameter Definitions

    :cvar name: Name of the parameter
    :cvar type: OpenJD Type of the parameter (INT, FLOAT, STRING, PATH)
    :cvar value: Parameter value
    """

    name: str
    type: str
    value: Any = None

    @classmethod
    def from_unreal_param_definition(cls, u_param: unreal.ParameterDefinition):
        """
        Create UnrealOpenJobParameterDefinition instance from unreal.ParameterDefinition
        object.

        :return: UnrealOpenJobParameterDefinition instance
        :rtype: UnrealOpenJobParameterDefinition
        """

        build_kwargs = dict(name=u_param.name, type=u_param.type.name)
        if u_param.value:
            python_class = PARAMETER_DEFINITION_MAPPING[u_param.type.name].python_class
            build_kwargs["value"] = python_class(u_param.value)
        return cls(**build_kwargs)

    @classmethod
    def from_dict(cls, param_dict: dict):
        """
        Create UnrealOpenJobParameterDefinition instance python dict.
        If source dict has "default" key, use its value

        :return: UnrealOpenJobParameterDefinition instance
        :rtype: UnrealOpenJobParameterDefinition
        """

        build_kwargs = dict(name=param_dict["name"], type=param_dict["type"])
        if "default" in param_dict:
            build_kwargs["value"] = param_dict["default"]

        return cls(**build_kwargs)

    def to_dict(self):
        """
        Return UnrealOpenJobParameterDefinition as dictionary

        :return: UnrealOpenJobParameterDefinition as python dictionary
        :rtype: dict[str, Any]
        """

        return asdict(self)


# Base Open Job implementation
class UnrealOpenJob(UnrealOpenJobEntity):
    """
    Open Job for Unreal Engine
    """

    def __init__(
        self,
        file_path: Optional[str] = None,
        name: Optional[str] = None,
        steps: Optional[list[UnrealOpenJobStep]] = None,
        environments: Optional[list[UnrealOpenJobEnvironment]] = None,
        extra_parameters: Optional[list[UnrealOpenJobParameterDefinition]] = None,
        job_shared_settings: JobSharedSettings = JobSharedSettings(),
        asset_references: AssetReferences = AssetReferences(),
    ):
        """
        :param file_path: Path to the open job template file
        :type file_path: str

        :param name: Name of the job
        :type name: str

        :param steps: List of steps to be executed by deadline cloud
        :type steps: list[UnrealOpenJobStep]

        :param environments: List of environments to be used by deadline cloud
        :type environments: list[UnrealOpenJobEnvironment]

        :param extra_parameters: List of additional parameters to be added to the job
        :type extra_parameters: list[UnrealOpenJobParameterDefinition]

        :param job_shared_settings: JobSharedSettings instance
        :type job_shared_settings: JobSharedSettings

        :param asset_references: AssetReferences object
        :type asset_references: AssetReferences
        """

        super().__init__(JobTemplate, file_path, name)

        self._extra_parameters: list[UnrealOpenJobParameterDefinition] = extra_parameters or []
        self._create_missing_extra_parameters_from_template()

        self._steps: list[UnrealOpenJobStep] = steps or []
        self._environments: list[UnrealOpenJobEnvironment] = environments or []
        self._job_shared_settings = job_shared_settings
        self._asset_references = asset_references

        self._transfer_files_strategy = TransferProjectFilesStrategy.S3

    @property
    def job_shared_settings(self) -> JobSharedSettings:
        return self._job_shared_settings

    @job_shared_settings.setter
    def job_shared_settings(self, value: JobSharedSettings):
        self._job_shared_settings = value

    @classmethod
    def from_data_asset(cls, data_asset: unreal.DeadlineCloudJob) -> "UnrealOpenJob":
        """
        Create the instance of UnrealOpenJob from unreal.DeadlineCloudJob.
        Call same method on data_asset's steps, environments.

        :param data_asset: unreal.DeadlineCloudJob instance

        :return: UnrealOpenJob instance
        :rtype: UnrealOpenJob
        """

        steps = [UnrealOpenJobStep.from_data_asset(step) for step in data_asset.steps]

        host_requirements = HostRequirementsHelper.u_host_requirements_to_openjd_host_requirements(
            data_asset.job_preset_struct.host_requirements
        )
        for step in steps:
            step.host_requirements = host_requirements

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
            job_shared_settings=JobSharedSettings.from_u_deadline_cloud_job_shared_settings(
                shared_settings
            ),
        )

    @staticmethod
    def serialize_template(template: Template) -> dict[str, Any]:
        """
        Serialize given template and return ordered dictionary
        (spec version, name, parameters, envs, steps).

        :param template: Template (JobTemplate, StepTemplate, Environment)
        :type template: Union[JobTemplate, StepTemplate, Environment]

        :return: Ordered python dictionary
        :rtype: dict[str, Any]
        """

        template_json = json.loads(template.json(exclude_none=True))
        ordered_keys = [
            "specificationVersion",
            "name",
            "parameterDefinitions",
            "jobEnvironments",
            "steps",
        ]
        ordered_data = dict(
            OrderedDict((key, template_json[key]) for key in ordered_keys if key in template_json)
        )
        return ordered_data

    @staticmethod
    def update_job_parameter_values(
        job_parameter_values: list[dict[str, Any]],
        job_parameter_name: str,
        job_parameter_value: Any,
    ) -> list[dict[str, Any]]:
        """
        Try to find parameter in given list by the provided name
        and update its value wih provided value.

        :param job_parameter_values: List of parameter values dictionaries (name and value)
        :type job_parameter_values: list[dict[str, Any]]
        :param job_parameter_name: Name of the parameter to update
        :type job_parameter_name: str
        :param job_parameter_value: Value of the parameter to set
        :type job_parameter_value: Any

        :return: Given list of parameter values with possibly updated parameter
        :rtype: list[dict[str, Any]]
        """

        param = next((p for p in job_parameter_values if p["name"] == job_parameter_name), None)
        if param:
            param["value"] = job_parameter_value
        return job_parameter_values

    def _create_missing_extra_parameters_from_template(self):
        """
        Update parameters with YAML template data. Mostly needed for custom job submission process.

        If no template file found, skip updating and log warning.
        This is not an error and should not break the building process.
        """

        try:
            extra_param_names = [p.name for p in self._extra_parameters]
            for p in self.get_template_object()["parameterDefinitions"]:
                if p["name"] not in extra_param_names:
                    self._extra_parameters.append(UnrealOpenJobParameterDefinition.from_dict(p))
        except FileNotFoundError:
            logger.warning("No template file found to read parameters from.")

    def _find_extra_parameter(
        self, parameter_name: str, parameter_type: str
    ) -> Optional[UnrealOpenJobParameterDefinition]:
        """
        Find extra parameter by given name and type

        :param parameter_name: Parameter name
        :param parameter_type: Parameter type (INT, FLOAT, STRING, PATH)

        :return: Parameter if found, None otherwise
        :rtype: Optional[UnrealOpenJobParameterDefinition]
        """

        return next(
            (
                p
                for p in self._extra_parameters
                if p.name == parameter_name and p.type == parameter_type
            ),
            None,
        )

    def _build_parameter_values(self) -> list:
        """
        Build and return list of parameter values for the OpenJob. Use YAML parameter names and
        extra parameter values/YAML defaults if exists.

        :return: Parameter values list of dictionaries
        :rtype: list
        """

        job_template_object = self.get_template_object()
        parameter_values = []
        for yaml_p in job_template_object["parameterDefinitions"]:
            extra_p = self._find_extra_parameter(yaml_p["name"], yaml_p["type"])
            value = extra_p.value if extra_p else yaml_p.get("default")
            parameter_values.append(dict(name=yaml_p["name"], value=value))

        if self._job_shared_settings:
            parameter_values += self._job_shared_settings.serialize()

        return parameter_values

    def _check_parameters_consistency(self):
        """
        Check Job parameters consistency

        :return: Result of parameters consistency check
        :rtype: ParametersConsistencyCheckResult
        """

        result = ParametersConsistencyChecker.check_job_parameters_consistency(
            job_template_path=self.file_path,
            job_parameters=[p.to_dict() for p in self._extra_parameters],
        )

        result.reason = f"OpenJob {self.name}: " + result.reason

        return result

    def _build_template(self) -> JobTemplate:
        """
        Build JobTemplate OpenJD model.

        Build process:
            1. Fill specification version for the Job
            2. Fill Job parameter definition list
            3. Build given Steps
            4. Build given Environments

        :return: JobTemplate instance
        :rtype: JobTemplate
        """

        job_template = self.template_class(
            specificationVersion=settings.JOB_TEMPLATE_VERSION,
            name=self.name,
            parameterDefinitions=[
                PARAMETER_DEFINITION_MAPPING[param["type"]].job_parameter_openjd_class(**param)
                for param in self.get_template_object()["parameterDefinitions"]
            ],
            steps=[s.build_template() for s in self._steps],
            jobEnvironments=(
                [e.build_template() for e in self._environments] if self._environments else None
            ),
        )
        return job_template

    def get_asset_references(self) -> AssetReferences:
        """
        Return AssetReferences of itself that union given Environments and Steps' AssetReferences

        :return: AssetReferences from this Job and its Environments and Steps
        :rtype: AssetReferences
        """

        asset_references = super().get_asset_references()

        if self._asset_references:
            asset_references = asset_references.union(self._asset_references)

        for step in self._steps:
            asset_references = asset_references.union(step.get_asset_references())

        for environment in self._environments:
            asset_references = asset_references.union(environment.get_asset_references())

        return asset_references

    def create_job_bundle(self):
        """
        Create Job bundle directory with next files inside:
            1. template.yaml - Full OpenJD Job template with steps, envs, parameters, etc.
            2. parameter_values.yaml - List of Job parameter values + Shared settings values
            3. asset_references.yaml - Input directories/files, outputs to sync with S3 on submit

        :return: Job bundle directory path
        :rtype: str
        """

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


# Render Open Job
class RenderUnrealOpenJob(UnrealOpenJob):
    """
    Unreal Open Job for rendering Unreal Engine projects

    :cvar job_environment_map: Map for converting C++ environment classes to Python classes
    :cvar job_step_map: Map for converting C++ step classes to Python classes
    """

    default_template_path = settings.RENDER_JOB_TEMPLATE_DEFAULT_PATH

    job_environment_map = {unreal.DeadlineCloudUgsEnvironment: UnrealOpenJobUgsEnvironment}

    job_step_map = {unreal.DeadlineCloudRenderStep: RenderUnrealOpenJobStep}

    def __init__(
        self,
        file_path: Optional[str] = None,
        name: Optional[str] = None,
        steps: Optional[list[UnrealOpenJobStep]] = None,
        environments: Optional[list[UnrealOpenJobEnvironment]] = None,
        extra_parameters: Optional[list[UnrealOpenJobParameterDefinition]] = None,
        job_shared_settings: JobSharedSettings = JobSharedSettings(),
        asset_references: AssetReferences = AssetReferences(),
        mrq_job: Optional[unreal.MoviePipelineExecutorJob] = None,
    ):
        """
        Construct RenderUnrealOpenJob instance.

        :param file_path: Path to the open job template file
        :type file_path: str

        :param name: Name of the job
        :type name: str

        :param steps: List of steps to be executed by deadline cloud
        :type steps: list[UnrealOpenJobStep]

        :param environments: List of environments to be used by deadline cloud
        :type environments: list[UnrealOpenJobEnvironment]

        :param extra_parameters: List of additional parameters to be added to the job
        :type extra_parameters: list[UnrealOpenJobParameterDefinition]

        :param job_shared_settings: JobSharedSettings instance
        :type job_shared_settings: JobSharedSettings

        :param asset_references: AssetReferences object
        :type asset_references: AssetReferences

        :param mrq_job: unreal.MoviePipelineExecutorJob instance to take render data from
        :type mrq_job: unreal.MoviePipelineExecutorJob
        """
        super().__init__(
            file_path,
            name,
            steps,
            environments,
            extra_parameters,
            job_shared_settings,
            asset_references,
        )

        self._mrq_job = None
        if mrq_job:
            self.mrq_job = mrq_job

        self._dependency_collector = DependencyCollector()

        self._manifest_path = ""
        self._extra_cmd_args_file_path = ""

        if self._name is None and isinstance(self.mrq_job, unreal.MoviePipelineExecutorJob):
            self._name = self.mrq_job.job_name

        ugs_envs = [
            env for env in self._environments if isinstance(env, UnrealOpenJobUgsEnvironment)
        ]
        if ugs_envs:
            self._transfer_files_strategy = TransferProjectFilesStrategy.UGS

    @property
    def mrq_job(self):
        return self._mrq_job

    @mrq_job.setter
    def mrq_job(self, value):
        """
        Set mrq_job as given value.
        Updates next objects:
            1. Job extra parameters from mrq job parameter definition overrides
            2. Step's parameters and environments from mrq job step overrides for each step
            3. Environment's variables from mrq job environment overrides for each environment
            4. Job name if not set by next priority:
                I. Job preset override - (highest priority)
                II. Data asset job preset struct
                III. YAML template
                IV. MRQ Job name (shot name) - lowest priority

        :param value: unreal.MoviePipelineExecutorJob instance
        :type value: unreal.MoviePipelineExecutorJob
        """

        self._mrq_job = value
        self._update_steps_settings_from_mrq_job(self._mrq_job)
        self._update_environments_settings_from_mrq_job(self._mrq_job)

        if self._mrq_job.parameter_definition_overrides.parameters:
            self._extra_parameters = [
                UnrealOpenJobParameterDefinition.from_unreal_param_definition(p)
                for p in self._mrq_job.parameter_definition_overrides.parameters
            ]

        self.job_shared_settings = JobSharedSettings.from_u_deadline_cloud_job_shared_settings(
            self._mrq_job.preset_overrides.job_shared_settings
        )

        # Job name set order:
        #   0. Job preset override (high priority)
        #   1. Get from data asset job preset struct
        #   2. Get from YAML template
        #   4. Get from mrq job name (shot name)
        preset_override_name = self._mrq_job.preset_overrides.job_shared_settings.name
        if preset_override_name not in ["", "Untitled"]:
            self._name = preset_override_name

        if self._name is None:
            self._name = self._mrq_job.job_name

    @property
    def manifest_path(self):
        return self._manifest_path

    @classmethod
    def from_data_asset(cls, data_asset: unreal.DeadlineCloudRenderJob) -> "RenderUnrealOpenJob":
        """
        Create the instance of RenderUnrealOpenJob from unreal.DeadlineCloudRenderJob.
        Call same method on data_asset's steps, environments.
        Create appropriate Steps and Environments listed in job_step_map, job_environment_map

        :param data_asset: unreal.DeadlineCloudRenderJob instance

        :return: RenderUnrealOpenJob instance
        :rtype: RenderUnrealOpenJob
        """

        render_steps_count = RenderUnrealOpenJob.render_steps_count(data_asset)
        if render_steps_count != 1:
            raise exceptions.RenderStepCountConstraintError(
                f"RenderJob data asset should have exactly 1 Render Step. "
                f"Currently it has {render_steps_count} Render Steps"
            )

        host_requirements = HostRequirementsHelper.u_host_requirements_to_openjd_host_requirements(
            data_asset.job_preset_struct.host_requirements
        )
        steps = []
        for source_step in data_asset.steps:
            job_step_cls = cls.job_step_map.get(type(source_step), UnrealOpenJobStep)
            job_step = job_step_cls.from_data_asset(source_step)
            job_step.host_requirements = host_requirements
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
            job_shared_settings=JobSharedSettings.from_u_deadline_cloud_job_shared_settings(
                shared_settings
            ),
        )

    @classmethod
    def from_mrq_job(
        cls, mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob
    ) -> "RenderUnrealOpenJob":
        """
        Create the instance of RenderUnrealOpenJob from unreal.MoviePipelineDeadlineCloudExecutorJob.
        Use it job_preset to create from data asset and set mrq_job as given mrq_job.

        :param mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob instance

        :return: RenderUnrealOpenJob instance
        :rtype: RenderUnrealOpenJob
        """

        render_unreal_open_job = cls.from_data_asset(mrq_job.job_preset)
        render_unreal_open_job.mrq_job = mrq_job
        return render_unreal_open_job

    @staticmethod
    def render_steps_count(data_asset: unreal.DeadlineCloudRenderJob) -> int:
        """
        Count unreal.DeadlineCloudRenderStep in the given Render Job data asset

        :param data_asset: unreal.DeadlineCloudRenderJob instance

        :return: unreal.DeadlineCloudRenderStep count
        :rtype: int
        """

        return sum(isinstance(s, unreal.DeadlineCloudRenderStep) for s in data_asset.steps)

    @staticmethod
    def get_required_project_directories() -> list[str]:
        """
        Returns a list of required project directories such as Config and Binaries

        :return: list of required project directories
        :rtype: list
        """

        required_project_directories = []
        for sub_dir in ["Config", "Binaries"]:
            directory = common.os_abs_from_relative(sub_dir)
            if os.path.exists(directory):
                required_project_directories.append(directory)
        return required_project_directories

    def _update_steps_settings_from_mrq_job(
        self, mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob
    ):
        """
        Iterate through the Job's Steps and update settings with overrides of given MRQ Job
        for each Step.

        Settings to update:
            1. Host requirements
            2. MRQ Job (If step is RenderUnrealOpenJobStep)
            3. Step depends on list
            4. Environment variables for each Environment of the Step
            5. Step parameters

        :param mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob instance
        :type mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob
        """

        host_requirements = HostRequirementsHelper.u_host_requirements_to_openjd_host_requirements(
            mrq_job.preset_overrides.host_requirements
        )
        for step in self._steps:
            # update host requirements
            step.host_requirements = host_requirements

            # set mrq job to render step
            if isinstance(step, RenderUnrealOpenJobStep):
                step.mrq_job = mrq_job

            # find appropriate step override
            step_override = next(
                (override for override in mrq_job.steps_overrides if override.name == step.name),
                None,
            )
            if not step_override:
                continue

            # update depends on
            step.step_dependencies = list(step_override.depends_on)

            # update step environments
            for env in step.environments:
                step_environment_override = next(
                    (
                        env_override
                        for env_override in step_override.environments_overrides
                        if env_override.name == env.name
                    ),
                    None,
                )
                if step_environment_override:
                    env.variables = step_environment_override.variables.variables

            # update step parameters
            for override_param in step_override.task_parameter_definitions.parameters:
                step.update_extra_parameter(
                    UnrealOpenJobStepParameterDefinition.from_unreal_param_definition(
                        override_param
                    )
                )

    def _update_environments_settings_from_mrq_job(
        self, mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob
    ):
        """
        Iterate through the Job's Environments and update variables map with overrides of given MRQ Job
        for each Environment.

        :param mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob instance
        :type mrq_job: unreal.MoviePipelineDeadlineCloudExecutorJob
        """

        for env in self._environments:
            override_environment = next(
                (
                    env_override
                    for env_override in mrq_job.environments_overrides
                    if env_override.name == env.name
                ),
                None,
            )
            if override_environment:
                env.variables = override_environment.variables.variables

    def _write_cmd_args_to_file(self, cmd_args_str: str) -> str:
        """
        Write Unreal launch arguments to temp file with unique name

        :param cmd_args_str: command arguments string
        :type cmd_args_str: str

        :return: temp file path with cmd args content
        :rtype: str
        """

        destination_dir = os.path.join(
            unreal.SystemLibrary.get_project_saved_directory(),
            "UnrealDeadlineCloudService",
            "ExtraCmdArgs",
        )
        os.makedirs(destination_dir, exist_ok=True)

        cmd_args_file = unreal.Paths.create_temp_filename(
            destination_dir, prefix="ExtraCmdArgs", extension=".txt"
        )

        with open(cmd_args_file, "w", encoding="utf-8") as f:
            logger.info(f"Saving ExtraCmdArgs file `{cmd_args_file}`")
            f.write(cmd_args_str)

        self._extra_cmd_args_file_path = unreal.Paths.convert_relative_path_to_full(cmd_args_file)
        return self._extra_cmd_args_file_path

    def _build_parameter_values(self) -> list:
        """
        Build and return list of parameter values for the OpenJob. Use YAML parameter names and
        extra parameter values/ YAML defaults if exists.

        Fill parameters that were not filled by user on in YAML. Typically, this parameters
        should not be filled by user (such as Project Path, Extra Cmd Args File, UGS settings, etc.)

        .. note:: Set ExtraCmdArgs parameter as empty string "" since Adaptor read args only from file.

        :return: list of parameter values
        :rtype: list[dict[str, Any]]
        """

        parameter_values = super()._build_parameter_values()

        # skip params with filled values (in YAML or by User in UI)
        # if it is not ExtraCmdArgs since we want to update them with mrq job args
        unfilled_parameter_values = [
            p
            for p in parameter_values
            if p["value"] is None or p["name"] == OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS
        ]
        filled_parameter_values = [
            p for p in parameter_values if p not in unfilled_parameter_values
        ]

        # Unreal Engine can handle long CMD args strings and OpenJD has a limit of 1024 chars.
        # Therefore, we need to write them to file and set ExtraCmdArgs parameter as empty string.
        # Unreal Adaptor uses only ExtraCmdArgsFile parameter to read args from file.
        cmd_args_str = " ".join(self._get_ue_cmd_args())

        unfilled_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=unfilled_parameter_values,
            job_parameter_name=OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS,
            job_parameter_value="",
        )

        unfilled_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=unfilled_parameter_values,
            job_parameter_name=OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS_FILE,
            job_parameter_value=self._write_cmd_args_to_file(cmd_args_str).replace("\\", "/"),
        )

        unfilled_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=unfilled_parameter_values,
            job_parameter_name=OpenJobParameterNames.UNREAL_PROJECT_PATH,
            job_parameter_value=common.get_project_file_path(),
        )

        if self._transfer_files_strategy == TransferProjectFilesStrategy.UGS:
            perforce_api = PerforceApi()

            unfilled_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                job_parameter_values=unfilled_parameter_values,
                job_parameter_name=OpenJobParameterNames.PERFORCE_STREAM_PATH,
                job_parameter_value=perforce_api.get_stream_path(),
            )

            unfilled_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                job_parameter_values=unfilled_parameter_values,
                job_parameter_name=OpenJobParameterNames.PERFORCE_CHANGELIST_NUMBER,
                job_parameter_value=str(perforce_api.get_latest_changelist_number()) or "latest",
            )

            unfilled_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                job_parameter_values=unfilled_parameter_values,
                job_parameter_name=OpenJobParameterNames.UNREAL_PROJECT_NAME,
                job_parameter_value=common.get_project_name(),
            )

            client_root = perforce_api.get_client_root()
            if isinstance(client_root, str):
                unreal_project_path = common.get_project_file_path().replace("\\", "/")
                unreal_project_relative_path = unreal_project_path.replace(client_root, "")
                unreal_project_relative_path = unreal_project_relative_path.lstrip("/")

                unfilled_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                    job_parameter_values=unfilled_parameter_values,
                    job_parameter_name=OpenJobParameterNames.UNREAL_PROJECT_RELATIVE_PATH,
                    job_parameter_value=unreal_project_relative_path,
                )

                unreal_executable_path = sys.executable.replace("\\", "/")
                unreal_executable_relative_path = unreal_executable_path.replace(client_root, "")
                unreal_executable_relative_path = unreal_executable_relative_path.lstrip("/")

                unfilled_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
                    job_parameter_values=unfilled_parameter_values,
                    job_parameter_name=OpenJobParameterNames.UNREAL_EXECUTABLE_RELATIVE_PATH,
                    job_parameter_value=unreal_executable_relative_path,
                )

        all_parameter_values = filled_parameter_values + unfilled_parameter_values
        return all_parameter_values

    def _get_ue_cmd_args(self) -> list[str]:
        """
        Build and return a list of command line arguments to pass to Unreal while launching.

        Arguments to include:
            1. unreal.MoviePipelineInProcessExecutorSettings' inherited CMDs except of any
            `-execcmds`. In some cases, users may execute a script that is local to their editor
            build for some automated workflow but this is not ideal on the farm
            2. unreal.MoviePipelineInProcessExecutorSettings' additional CMDs
            3. MRQ Job Configuration's CMD args, device profile class vars, execution CMD args
            4. Extra CMD args provided by user except of `-execcmds` for the same reason
        """
        cmd_args = []

        in_process_executor_settings = unreal.get_default_object(
            unreal.MoviePipelineInProcessExecutorSettings
        )

        # Append all of inherited command line arguments from the editor
        inherited_cmds: str = in_process_executor_settings.inherited_command_line_arguments
        inherited_cmds = re.sub(pattern='(-execcmds="[^"]*")', repl="", string=inherited_cmds)
        inherited_cmds = re.sub(pattern="(-execcmds='[^']*')", repl="", string=inherited_cmds)
        cmd_args.extend(inherited_cmds.split(" "))

        logger.warning(
            "Appearance of custom '-execcmds' argument on the Render node can cause unpredictable "
            "issues. Argument '-execcmds' of MoviePipelineInProcessExecutorSettings' "
            "Inherited Command Line arguments will be ignored."
        )

        # Append all of additional command line arguments from the editor
        additional_cmds: str = in_process_executor_settings.additional_command_line_arguments
        cmd_args.extend(additional_cmds.split(" "))

        # Initializes a single instance of every setting
        # so that even non-user-configured settings have a chance to apply their default values
        if self._mrq_job:
            self._mrq_job.get_configuration().initialize_transient_settings()

            job_url_params: list[str] = []
            job_cmd_args: list[str] = []
            job_device_profile_cvars: list[str] = []
            job_exec_cmds: list[str] = []
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

        extra_cmd_args_param = self._find_extra_parameter(
            parameter_name=OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS,
            parameter_type="STRING",
        )

        if extra_cmd_args_param:
            extra_cmd_args = str(extra_cmd_args_param.value)
            cleared_extra_cmds_args = re.sub(
                pattern='(-execcmds="[^"]*")', repl="", string=extra_cmd_args
            )
            cleared_extra_cmds_args = re.sub(
                pattern="(-execcmds='[^']*')", repl="", string=cleared_extra_cmds_args
            )

            logger.warning(
                "Appearance of custom '-execcmds' argument on the Render node can cause unpredictable "
                "issues. Argument '-execcmds' of Unreal Open Job's "
                "Extra Command Line arguments will be ignored."
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
        if not self._mrq_job:
            raise exceptions.MrqJobIsMissingError("MRQ Job must be provided")

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

    def _get_mrq_job_dependency_paths(self):
        """
        Collects the dependencies of the Level and LevelSequence that used in MRQ Job and
        returns paths converted from UE relative (i.e. /Game/...) to OS absolute (D:/...)

        :return: List of the dependencies
        :rtype: list[str]
        """

        os_dependencies = []

        job_dependencies = self._collect_mrq_job_dependencies()
        for dependency in job_dependencies:
            os_dependency = common.os_path_from_unreal_path(dependency, with_ext=True)
            if os.path.exists(os_dependency):
                os_dependencies.append(os_dependency)

        return os_dependencies

    def _get_mrq_job_attachments_input_files(self) -> list[str]:
        """
        Get Job Attachments Input Files from MRQ Job preset overrides

        :return: List of MRQ Job Attachments Input Files
        :rtype: list[str]
        """

        input_files = []

        job_input_files = self.mrq_job.preset_overrides.job_attachments.input_files.files.paths
        for job_input_file in job_input_files:
            input_file = common.os_abs_from_relative(job_input_file.file_path)
            if os.path.exists(input_file):
                input_files.append(input_file)

        return input_files

    def _get_mrq_job_attachments_input_directories(self) -> list[str]:
        """
        Get Job Attachments Input Directories from MRQ Job preset overrides

        :return: List of MRQ Job Attachments Input Directories
        :rtype: list[str]
        """

        input_directories = []

        job_input_directories = (
            self.mrq_job.preset_overrides.job_attachments.input_directories.directories.paths
        )
        for job_input_dir in job_input_directories:
            input_dir = common.os_abs_from_relative(job_input_dir.path)
            if os.path.exists(input_dir):
                input_directories.append(input_dir)

        return input_directories

    def _get_mrq_job_attachments_output_directories(self) -> list[str]:
        """
        Get Job Attachments Output Directories from MRQ Job preset overrides

        :return: List of MRQ Job Attachments Output Directories
        :rtype: list[str]
        """

        output_directories = []

        job_output_directories = (
            self.mrq_job.preset_overrides.job_attachments.output_directories.directories.paths
        )
        for job_output_dir in job_output_directories:
            output_dir = common.os_abs_from_relative(job_output_dir.path)
            if os.path.exists(output_dir):
                output_directories.append(output_dir)

        return output_directories

    def _get_mrq_job_output_directory(self) -> str:
        """
        Get the output directory path from  MRQ Job Configuration, resolve all possible tokens
        (e.g. job_name, level, map, etc.) and return resulted path.

        :return: MRQ Job Configuration's resolved Output Directory
        :rtype: str
        """

        output_setting = self.mrq_job.get_configuration().find_setting_by_class(
            unreal.MoviePipelineOutputSetting
        )
        output_path = output_setting.output_directory.path
        common.validate_path_does_not_contain_non_valid_chars(output_path)

        path_context = common.get_path_context_from_mrq_job(self.mrq_job)
        output_path = output_path.format_map(path_context).rstrip("/")

        return output_path

    def get_asset_references(self) -> AssetReferences:
        """
        Build asset references of the OpenJob with the given MRQ Job.

        Return :class:`deadline.client.job_bundle.submission.AssetReferences` instance

        :return: AssetReferences dataclass instance
        :rtype: :class:`deadline.client.job_bundle.submission.AssetReferences`
        """

        asset_references = super().get_asset_references()

        if self._transfer_files_strategy == TransferProjectFilesStrategy.S3:
            # add dependencies to attachments
            asset_references.input_filenames.update(self._get_mrq_job_dependency_paths())

            # required input directories
            asset_references.input_directories.update(
                RenderUnrealOpenJob.get_required_project_directories()
            )

        # add ue cmd args file
        if os.path.exists(self._extra_cmd_args_file_path):
            asset_references.input_filenames.add(self._extra_cmd_args_file_path)

        # add attachments from preset overrides
        if self.mrq_job:
            # input files
            asset_references.input_filenames.update(self._get_mrq_job_attachments_input_files())

            # input directories
            asset_references.input_directories.update(
                self._get_mrq_job_attachments_input_directories()
            )

            # output directories
            asset_references.output_directories.update(
                self._get_mrq_job_attachments_output_directories()
            )

            # Render output path
            asset_references.output_directories.add(self._get_mrq_job_output_directory())

        return asset_references


# UGS Jobs
class UgsRenderUnrealJob(RenderUnrealOpenJob):
    """Class for predefined UGS Render Job"""

    default_template_path = settings.UGS_RENDER_JOB_TEMPLATE_DEFAULT_PATH
