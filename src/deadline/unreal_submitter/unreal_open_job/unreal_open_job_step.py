import math
import unreal
from typing import Any, Literal, Optional

from openjd.model.v2023_09 import *
from openjd.model.v2023_09._model import StepDependency

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (
    UnrealOpenJobEntity,
    PARAMETER_DEFINITION_MAPPING
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import UnrealOpenJobEnvironment


class HostRequirements:
    """OpenJob host requirements representation"""

    def __init__(self, host_requirements):
        self.source_host_requirements = host_requirements
        self.requirements: dict = {}

        os_requirements = self._get_os_requirements()
        if os_requirements:
            # OS requirements are currently all amount type capabilities
            self.requirements["attributes"] = os_requirements

        hardware_requirements = self._get_hardware_requirements()
        if hardware_requirements:
            # hardware requirements are currently all amount
            self.requirements["amounts"] = hardware_requirements

    def _get_os_requirements(self) -> list[dict]:
        """
        Get requirements for OS family and CPU architecture

        :return: list of the OS requirements
        :rtype: list[dict]
        """
        requirements: list[dict] = []
        if self.source_host_requirements.operating_system:
            requirements.append(
                {
                    "name": "attr.worker.os.family",
                    "anyOf": [self.source_host_requirements.operating_system],
                }
            )
        if self.source_host_requirements.cpu_architecture:
            requirements.append(
                {
                    "name": "attr.worker.cpu.arch",
                    "anyOf": [self.source_host_requirements.cpu_architecture],
                }
            )
        return requirements

    def _get_hardware_requirements(self) -> list[dict[str, Any]]:
        """
        Get requirements for cpu, gpu and memory limits

        :return: list of the OS requirements
        :rtype: list[dict]
        """
        cpus = self._get_amount_requirement(
            self.source_host_requirements.cp_us, "amount.worker.vcpu"
        )
        memory = self._get_amount_requirement(
            self.source_host_requirements.memory, "amount.worker.memory", 1024
        )
        # TODO gpu amount
        # gpus = self._get_amount_requirement(self.source_host_requirements.gpus, "amount.worker.gpu")
        gpu_memory = self._get_amount_requirement(
            self.source_host_requirements.gp_us, "amount.worker.gpu.memory", 1024
        )
        scratch_space = self._get_amount_requirement(
            self.source_host_requirements.scratch_space, "amount.worker.disk.scratch"
        )
        requirements: list[dict[str, Any]] = [
            item for item in [cpus, memory, gpu_memory, scratch_space] if item is not None
        ]
        return requirements

    @staticmethod
    def _get_amount_requirement(source_interval, name: str, scaling_factor: int = 1) -> dict:
        """
        Helper method to get the amount of Host Requirement setting interval

        :param source_interval: Interval unreal setting
        :param name: AWS HostRequirements setting name
        :param scaling_factor: Multiplier number by which to scale the source_interval values

        :return: Amount requirement as dictionary
        :rtype: dict
        """
        requirement = {}
        if source_interval.min > 0 or source_interval.max > 0:
            requirement = {"name": name}
            if source_interval.min > 0:
                requirement["min"] = source_interval.min * scaling_factor
            if source_interval.max > 0:
                requirement["max"] = source_interval.max * scaling_factor
        return requirement

    def as_dict(self) -> dict:
        """
        Returns the HostRequirements as dictionary

        :return: Host Requirements as dictionary
        :rtype: dict
        """
        return self.requirements


class UnrealOpenJobStep(UnrealOpenJobEntity):
    """
    Unreal Open Job Step entity
    """

    def __init__(
            self,
            file_path: str,
            name: str = None,
            step_dependencies: list[str] = None,
            environments: list[UnrealOpenJobEnvironment] = None,
            extra_parameters: list[unreal.StepTaskParameterDefinition] = None,
            host_requirements: unreal.DeadlineCloudHostRequirementsStruct = None
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

        self._environments = environments

        self._extra_parameters = extra_parameters or []

        self._host_requirements = host_requirements

        super().__init__(StepTemplate, file_path, name)

    @property
    def host_requirements(self):
        return self._host_requirements

    @host_requirements.setter
    def host_requirements(self, value):
        self._host_requirements = value

    @classmethod
    def from_data_asset(cls, data_asset: unreal.DeadlineCloudStep) -> "UnrealOpenJobStep":
        return cls(
            file_path=data_asset.path_to_template,
            name=data_asset.name,
            step_dependencies=list(data_asset.depends_on),
            environments=[UnrealOpenJobEnvironment.from_data_asset(env) for env in data_asset.environments],
            extra_parameters=data_asset.get_step_parameters()
        )

    def _check_parameters_consistency(self):
        import open_job_template_api

        template = self.get_template_object()

        result = open_job_template_api.ParametersConsistencyChecker.check_parameters_consistency(
            yaml_parameters=[(p['name'], p['type']) for p in template['parameterSpace']['taskParameterDefinitions']],
            data_asset_parameters=[(p.name, p.type.name) for p in self._extra_parameters]
        )

        result.reason = f'OpenJob Step "{self.name}": ' + result.reason
        return result

    def _build_step_parameter_definition_list(self) -> list:
        """
        Build the job parameter definition list from the step template object.
        """
        
        step_template_object = self.get_template_object()

        step_parameter_definition_list = JobParameterDefinitionList()

        params = step_template_object['parameterSpace']['taskParameterDefinitions']
        for param in params:
            param_descriptor = PARAMETER_DEFINITION_MAPPING.get(param['type'])
            override_param = (
                next((p for p in self._extra_parameters if p.name == param['name']), None)
                if self._extra_parameters else None
            )
            if override_param:
                param_range = [param_descriptor.python_class(p) for p in list(override_param.range)]
                param.update(dict(name=override_param.name, range=param_range))

            param_definition_cls = param_descriptor.task_parameter_openjd_class
            unreal.log(f'STEP PARAM BUILD: {param}')
            step_parameter_definition_list.append(param_definition_cls(**param))

        return step_parameter_definition_list
        
    def _build_template(self) -> StepTemplate:
        step_template_object = self.get_template_object()

        step_parameters = self._build_step_parameter_definition_list()

        if not self._host_requirements.run_on_all_worker_nodes:
            host_requirements = HostRequirements(host_requirements=self._host_requirements)
            host_requirements_template = HostRequirementsTemplate(**(host_requirements.as_dict()))
        else:
            host_requirements_template = None

        return self.template_class(
            name=self.name,
            script=StepScript(**step_template_object['script']),
            parameterSpace=StepParameterSpaceDefinition(
                taskParameterDefinitions=step_parameters,
                combination=step_template_object['parameterSpace'].get('combination')
            ) if step_parameters else None,
            stepEnvironments=[env.build_template() for env in self._environments] if self._environments else None,
            dependencies=[
                StepDependency(dependsOn=step_dependency)
                for step_dependency in self._step_dependencies
            ] if self._step_dependencies else None,
            hostRequirements=host_requirements_template
        )


class RenderUnrealOpenJobStep(UnrealOpenJobStep):
    """
    Unreal Open Job Render Step entity
    """

    def __init__(
            self,
            file_path: str,
            name: str = None,
            step_dependencies: list[str] = None,
            environments: list = None,
            extra_parameters: list = None,
            host_requirements=None,
            task_chunk_size: int = 0,
            mrq_job: unreal.MoviePipelineExecutorJob = None
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
        
        self._task_chunk_size = task_chunk_size
        self._mrq_job = mrq_job
        self._queue_manifest_path = ''

        super().__init__(file_path, name, step_dependencies, environments, extra_parameters, host_requirements)

    @property
    def task_chunk_size(self):
        return self._task_chunk_size

    @task_chunk_size.setter
    def task_chunk_size(self, value: int):
        self._task_chunk_size = value

    @property
    def mrq_job(self):
        return self._mrq_job

    @mrq_job.setter
    def mrq_job(self, value: unreal.MoviePipelineExecutorJob):
        self._mrq_job = value

    @property
    def queue_manifest_path(self):
        return self._queue_manifest_path

    @queue_manifest_path.setter
    def queue_manifest_path(self, value):
        self._queue_manifest_path = value

    @staticmethod
    def validate_parameters(parameters: TaskParameterList) -> bool:
        """
        Validate the parameters
        
        :param parameters: The list of parameter entities
        :type parameters: list
        """
        
        param_names = [p.name for p in parameters]

        if 'QueueManifestPath' in param_names:
            return True
        elif 'MoviePipelineQueuePath' in param_names:
            return True
        elif {'LevelSequencePath', 'LevelPath', 'MoviePipelineConfigurationPath'}.issubset(set(param_names)):
            return True

        raise ValueError('RenderOpenJobStep parameters are not valid. Expect at least one of the following:\n'
                         '- QueueManifestPath\n'
                         '- MoviePipelineQueuePath\n'
                         '- LevelSequencePath, LevelPath, MoviePipelineConfigurationPath\n'
                         )

    @staticmethod
    def build_u_step_task_parameter(
            name: str,
            parameter_type: Literal['INT', 'FLOAT', 'STRING', 'PATH'],
            parameter_range: list[Any]
    ) -> unreal.StepTaskParameterDefinition:
        u_parameter = unreal.StepTaskParameterDefinition()
        u_parameter.name = name
        u_parameter.type = getattr(unreal.ValueType, parameter_type)
        u_parameter.range = unreal.Array(str)  # TODO think about auto typing the range (now its only string)
        u_parameter.range.extend(parameter_range)
        return u_parameter
        
    def _get_chunk_ids_count(self) -> int:
        """
        Get parameters
        """

        if not self.mrq_job:
            raise ValueError('MRQ Job must be provided')

        enabled_shots = [shot for shot in self.mrq_job.shot_info if shot.enabled]

        task_chunk_size_param = next((p for p in self._extra_parameters if p.name == 'TaskChunkSize'), None)
        unreal.log(f'TaskChunkSize PARAM VALUE: {task_chunk_size_param}')
        if task_chunk_size_param is None:
            raise ValueError('Render Step\'s parameter "TaskChunkSize " must be provided')

        if len(task_chunk_size_param.range) == 0 or int(task_chunk_size_param.range[0]) == 0:
            task_chunk_size = 1  # by default 1 chunk consist of 1 shot
        else:
            task_chunk_size = int(task_chunk_size_param.range[0])

        task_chunk_ids_count = math.ceil(len(enabled_shots) / task_chunk_size)
        return task_chunk_ids_count

    def _find_extra_parameter_by_name(self, parameter_name: str) -> Optional[unreal.StepTaskParameterDefinition]:
        return next((p for p in self._extra_parameters if p.name == parameter_name), None)

    def _update_extra_parameter(self, extra_parameter: unreal.StepTaskParameterDefinition):
        existed_parameter = self._find_extra_parameter_by_name(extra_parameter.name)
        if existed_parameter:
            self._extra_parameters.remove(existed_parameter)
        self._extra_parameters.append(extra_parameter)

    def _build_template(self) -> StepTemplate:
        """
        Build the definition template entity
        """

        task_chunk_id_param_definition = RenderUnrealOpenJobStep.build_u_step_task_parameter(
            'TaskChunkId', 'INT', [str(i) for i in range(self._get_chunk_ids_count())]
        )
        self._update_extra_parameter(task_chunk_id_param_definition)

        handler_param_definition = RenderUnrealOpenJobStep.build_u_step_task_parameter(
            'Handler', 'STRING', ['render']
        )
        self._update_extra_parameter(handler_param_definition)

        manifest_param_definition = RenderUnrealOpenJobStep.build_u_step_task_parameter(
            'QueueManifestPath', 'PATH', [self.queue_manifest_path]
        )
        self._update_extra_parameter(manifest_param_definition)

        step_entity = super()._build_template()
        
        RenderUnrealOpenJobStep.validate_parameters(
            step_entity.parameterSpace.taskParameterDefinitions
        )
        
        return step_entity
