import os
import math
import unreal
from enum import IntEnum
from typing import Optional, Any
from dataclasses import dataclass, field, asdict

from openjd.model.v2023_09 import (
    StepScript,
    StepTemplate,
    TaskParameterType,
    HostRequirementsTemplate,
    TaskParameterList,
    StepParameterSpaceDefinition,
)

from openjd.model.v2023_09._model import StepDependency

from deadline.unreal_submitter import common
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (
    UnrealOpenJobEntity,
    OpenJobStepParameterNames,
    PARAMETER_DEFINITION_MAPPING,
    ParameterDefinitionDescriptor,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (
    UnrealOpenJobEnvironment,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step_host_requirements import (
    HostRequirements,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_parameters_consistency import (
    ParametersConsistencyChecker,
)
from deadline.unreal_logger import get_logger
from deadline.unreal_submitter import exceptions, settings


logger = get_logger()


@dataclass
class UnrealOpenJobStepParameterDefinition:

    name: str
    type: str
    range: list[Any] = field(default_factory=list)

    @classmethod
    def from_unreal_param_definition(cls, u_param: unreal.StepTaskParameterDefinition):
        python_class = PARAMETER_DEFINITION_MAPPING[u_param.type.name].python_class
        build_kwargs = dict(
            name=u_param.name,
            type=u_param.type.name,
            range=[python_class(p) for p in list(u_param.range)],
        )
        return cls(**build_kwargs)

    @classmethod
    def from_dict(cls, param_dict: dict):
        return cls(**param_dict)

    def to_dict(self):
        return asdict(self)


# Base Step implementation
class UnrealOpenJobStep(UnrealOpenJobEntity):
    """
    Unreal Open Job Step entity
    """

    def __init__(
        self,
        file_path: str = None,
        name: str = None,
        step_dependencies: list[str] = None,
        environments: list[UnrealOpenJobEnvironment] = None,
        extra_parameters: list[UnrealOpenJobStepParameterDefinition] = None,
        host_requirements: HostRequirements = HostRequirements(),
    ):
        """
        :param file_path: The file path of the step descriptor
        :type file_path: str

        :param name: The name of the step
        :type name: str

        :param step_dependencies: The list of step dependencies
        :type step_dependencies: list[str]

        :param environments: The list of environments
        :type environments: list
        """

        self._step_dependencies = step_dependencies or []

        self._environments = environments or []

        self._extra_parameters = extra_parameters or []

        self._host_requirements = host_requirements

        super().__init__(StepTemplate, file_path, name)

        self._create_missing_extra_parameters_from_template()

    @property
    def host_requirements(self):
        return self._host_requirements

    @host_requirements.setter
    def host_requirements(self, value):
        self._host_requirements = value

    @property
    def step_dependencies(self) -> list[str]:
        return self._step_dependencies

    @step_dependencies.setter
    def step_dependencies(self, value: list[str]):
        self._step_dependencies = value

    @property
    def environments(self) -> list[UnrealOpenJobEnvironment]:
        return self._environments

    @environments.setter
    def environments(self, value: list[UnrealOpenJobEnvironment]):
        self._environments = value

    @classmethod
    def from_data_asset(cls, data_asset: unreal.DeadlineCloudStep) -> "UnrealOpenJobStep":
        return cls(
            file_path=data_asset.path_to_template.file_path,
            name=data_asset.name,
            step_dependencies=list(data_asset.depends_on),
            environments=[
                UnrealOpenJobEnvironment.from_data_asset(env) for env in data_asset.environments
            ],
            extra_parameters=[
                UnrealOpenJobStepParameterDefinition.from_unreal_param_definition(param)
                for param in data_asset.get_step_parameters()
            ],
        )

    def _find_extra_parameter(
        self, parameter_name: str, parameter_type: str
    ) -> Optional[UnrealOpenJobStepParameterDefinition]:
        return next(
            (
                p
                for p in self._extra_parameters
                if p.name == parameter_name and p.type == parameter_type
            ),
            None,
        )

    def _create_missing_extra_parameters_from_template(self):
        try:
            extra_param_names = [p.name for p in self._extra_parameters]
            for p in self.get_template_object()["parameterSpace"]["taskParameterDefinitions"]:
                if p["name"] not in extra_param_names:
                    self._extra_parameters.append(UnrealOpenJobStepParameterDefinition.from_dict(p))
        except FileNotFoundError:
            pass

    def _update_extra_parameter(
        self, extra_parameter: UnrealOpenJobStepParameterDefinition
    ) -> bool:
        existed_parameter = self._find_extra_parameter(extra_parameter.name, extra_parameter.type)
        if existed_parameter:
            self._extra_parameters.remove(existed_parameter)
            self._extra_parameters.append(extra_parameter)
            return True
        return False

    def _check_parameters_consistency(self):
        result = ParametersConsistencyChecker.check_step_parameters_consistency(
            step_template_path=self.file_path,
            step_parameters=[p.to_dict() for p in self._extra_parameters],
        )

        result.reason = f'OpenJob Step "{self.name}": ' + result.reason

        return result

    def _build_step_parameter_definition_list(self) -> list:
        """
        Build the job parameter definition list from the step template object.
        """

        step_template_object = self.get_template_object()

        step_parameter_definition_list = TaskParameterList()

        yaml_params = step_template_object["parameterSpace"]["taskParameterDefinitions"]
        for yaml_p in yaml_params:
            override_param = next(
                (p for p in self._extra_parameters if p.name == yaml_p["name"]), None
            )
            if override_param:
                yaml_p["range"] = override_param.range

            param_descriptor: ParameterDefinitionDescriptor = PARAMETER_DEFINITION_MAPPING[
                yaml_p["type"]
            ]
            param_definition_cls = param_descriptor.task_parameter_openjd_class

            step_parameter_definition_list.append(param_definition_cls(**yaml_p))

        return step_parameter_definition_list

    def _build_template(self) -> StepTemplate:
        step_template_object = self.get_template_object()

        step_parameters = self._build_step_parameter_definition_list()

        if self._host_requirements and not self._host_requirements.run_on_all_worker_nodes:
            host_requirements_template = HostRequirementsTemplate(
                **self._host_requirements.as_dict()
            )
        else:
            host_requirements_template = None

        return self.template_class(
            name=self.name,
            script=StepScript(**step_template_object["script"]),
            parameterSpace=(
                StepParameterSpaceDefinition(
                    taskParameterDefinitions=step_parameters,
                    combination=step_template_object["parameterSpace"].get("combination"),
                )
                if step_parameters
                else None
            ),
            stepEnvironments=(
                [env.build_template() for env in self._environments] if self._environments else None
            ),
            dependencies=(
                [
                    StepDependency(dependsOn=step_dependency)
                    for step_dependency in self._step_dependencies
                ]
                if self._step_dependencies
                else None
            ),
            hostRequirements=host_requirements_template,
        )

    def get_asset_references(self):
        asset_references = super().get_asset_references()
        for environment in self._environments:
            asset_references = asset_references.union(environment.get_asset_references())

        return asset_references

    def update_extra_parameter(self, extra_parameter: UnrealOpenJobStepParameterDefinition):
        return self._update_extra_parameter(extra_parameter)


# Render Step
class RenderUnrealOpenJobStep(UnrealOpenJobStep):
    """
    Unreal Open Job Render Step entity
    """

    default_template_path = settings.RENDER_STEP_TEMPLATE_DEFAULT_PATH

    class RenderArgsType(IntEnum):
        NOT_SET = 0
        QUEUE_MANIFEST_PATH = 1
        RENDER_DATA = 2
        MRQ_ASSET = 3

    def __init__(
        self,
        file_path: str = None,
        name: str = None,
        step_dependencies: list[str] = None,
        environments: list = None,
        extra_parameters: list = None,
        host_requirements=None,
        mrq_job: unreal.MoviePipelineExecutorJob = None,
    ):
        """
        :param file_path: The file path of the step descriptor
        :type file_path: str

        :param name: The name of the step
        :type name: str

        :param step_dependencies: The list of step dependencies
        :type step_dependencies: list[str]

        :param environments: The list of environments
        :type environments: list

        :param extra_parameters: The list of extra parameters
        :type extra_parameters: list

        :param task_chunk_size: The task chunk size
        :type task_chunk_size: int

        :param mrq_job: MRQ Job object
        :type mrq_job: unreal.MoviePipelineExecutorJob
        """

        super().__init__(
            file_path, name, step_dependencies, environments, extra_parameters, host_requirements
        )

        self._mrq_job = mrq_job
        self._queue_manifest_path: Optional[str] = None
        self._render_args_type = self._get_render_arguments_type()

    @property
    def mrq_job(self):
        return self._mrq_job

    @mrq_job.setter
    def mrq_job(self, value: unreal.MoviePipelineExecutorJob):
        self._mrq_job = value

    def _get_chunk_ids_count(self) -> int:
        """
        Get parameters
        """

        if not self.mrq_job:
            raise exceptions.MrqJobIsMissingError("MRQ Job must be provided")

        enabled_shots = [shot for shot in self.mrq_job.shot_info if shot.enabled]

        task_chunk_size_param = self._find_extra_parameter(
            parameter_name=OpenJobStepParameterNames.TASK_CHUNK_SIZE, parameter_type="INT"
        )
        if task_chunk_size_param is None:
            raise ValueError(
                f'Render Step\'s parameter "{OpenJobStepParameterNames.TASK_CHUNK_SIZE}" '
                f"must be provided in extra parameters or template"
            )

        if len(task_chunk_size_param.range) == 0 or int(task_chunk_size_param.range[0]) <= 0:
            task_chunk_size = 1  # by default 1 chunk consist of 1 shot
        else:
            task_chunk_size = task_chunk_size_param.range[0]

        task_chunk_ids_count = math.ceil(len(enabled_shots) / task_chunk_size)

        return task_chunk_ids_count

    def _get_render_arguments_type(self) -> Optional["RenderUnrealOpenJobStep.RenderArgsType"]:
        parameter_names = [p.name for p in self._extra_parameters]
        for p in parameter_names:
            if p == OpenJobStepParameterNames.QUEUE_MANIFEST_PATH:
                return RenderUnrealOpenJobStep.RenderArgsType.QUEUE_MANIFEST_PATH
            if p == OpenJobStepParameterNames.MOVIE_PIPELINE_QUEUE_PATH:
                return RenderUnrealOpenJobStep.RenderArgsType.MRQ_ASSET
        if {
            OpenJobStepParameterNames.LEVEL_SEQUENCE_PATH,
            OpenJobStepParameterNames.LEVEL_PATH,
            OpenJobStepParameterNames.MRQ_JOB_CONFIGURATION_PATH,
        }.issubset(set(parameter_names)):
            return RenderUnrealOpenJobStep.RenderArgsType.RENDER_DATA

        return RenderUnrealOpenJobStep.RenderArgsType.NOT_SET

    def _build_template(self) -> StepTemplate:
        """
        Build the definition template entity
        """

        if self._render_args_type == RenderUnrealOpenJobStep.RenderArgsType.NOT_SET:
            raise exceptions.RenderArgumentsTypeNotSetError(
                "RenderOpenJobStep parameters are not valid. Expect one of the following:\n"
                f"- {OpenJobStepParameterNames.QUEUE_MANIFEST_PATH}\n"
                f"- {OpenJobStepParameterNames.MOVIE_PIPELINE_QUEUE_PATH}\n"
                f"- ({OpenJobStepParameterNames.LEVEL_SEQUENCE_PATH}, "
                f"{OpenJobStepParameterNames.LEVEL_PATH}, "
                f"{OpenJobStepParameterNames.MRQ_JOB_CONFIGURATION_PATH})\n"
            )

        task_chunk_id_param_definition = UnrealOpenJobStepParameterDefinition(
            OpenJobStepParameterNames.TASK_CHUNK_ID,
            TaskParameterType.INT.value,
            [i for i in range(self._get_chunk_ids_count())],
        )
        self._update_extra_parameter(task_chunk_id_param_definition)

        handler_param_definition = UnrealOpenJobStepParameterDefinition(
            OpenJobStepParameterNames.ADAPTOR_HANDLER, TaskParameterType.STRING.value, ["render"]
        )
        self._update_extra_parameter(handler_param_definition)

        if self.mrq_job:
            output_setting = self.mrq_job.get_configuration().find_setting_by_class(
                unreal.MoviePipelineOutputSetting
            )
            output_path = output_setting.output_directory.path
            path_context = common.get_path_context_from_mrq_job(self.mrq_job)
            output_path = output_path.format_map(path_context).rstrip("/")
            output_param_definition = UnrealOpenJobStepParameterDefinition(
                OpenJobStepParameterNames.OUTPUT_PATH, TaskParameterType.PATH.value, [output_path]
            )
            self._update_extra_parameter(output_param_definition)

            if self._render_args_type == RenderUnrealOpenJobStep.RenderArgsType.QUEUE_MANIFEST_PATH:
                manifest_param_definition = UnrealOpenJobStepParameterDefinition(
                    OpenJobStepParameterNames.QUEUE_MANIFEST_PATH,
                    TaskParameterType.PATH.value,
                    [self._save_manifest_file()],
                )
                self._update_extra_parameter(manifest_param_definition)

        step_entity = super()._build_template()

        return step_entity

    def _save_manifest_file(self):
        new_queue = unreal.MoviePipelineQueue()
        new_job = new_queue.duplicate_job(self.mrq_job)

        # In duplicated job remove empty auto-detected files since
        # we don't want them to be saved in manifest
        new_job.preset_overrides.job_attachments.input_files.auto_detected = (
            unreal.DeadlineCloudFileAttachmentsArray()
        )

        _, manifest_path = unreal.MoviePipelineEditorLibrary.save_queue_to_manifest_file(new_queue)
        serialized_manifest = unreal.MoviePipelineEditorLibrary.convert_manifest_file_to_string(
            manifest_path
        )

        movie_render_pipeline_dir = os.path.join(
            unreal.SystemLibrary.get_project_saved_directory(),
            "UnrealDeadlineCloudService",
            "RenderJobManifests",
        )
        os.makedirs(movie_render_pipeline_dir, exist_ok=True)

        render_job_manifest_path = unreal.Paths.create_temp_filename(
            movie_render_pipeline_dir, prefix="RenderJobManifest", extension=".utxt"
        )

        with open(render_job_manifest_path, "w") as manifest:
            logger.info(f"Saving Manifest file `{render_job_manifest_path}`")
            manifest.write(serialized_manifest)

        self._queue_manifest_path = unreal.Paths.convert_relative_path_to_full(
            render_job_manifest_path
        )

        return self._queue_manifest_path

    def get_asset_references(self):
        asset_references = super().get_asset_references()

        if self._queue_manifest_path:
            asset_references.input_filenames.add(self._queue_manifest_path)

        return asset_references


# UGS Steps
class UgsRenderUnrealOpenJobStep(RenderUnrealOpenJobStep):

    default_template_path = settings.UGS_RENDER_STEP_TEMPLATE_DEFAULT_PATH
