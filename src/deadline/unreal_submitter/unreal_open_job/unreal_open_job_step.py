import math
import json
import unreal

from openjd.model.v2023_09 import *

from src.deadline.unreal_submitter.unreal_open_job.\
    unreal_open_job_entity import UnrealOpenJobEntity
from src.deadline.unreal_submitter.unreal_open_job.\
    unreal_open_job_environment import UnrealOpenJobEnvironment


class UnrealOpenJobStep(UnrealOpenJobEntity):
    """
    Unreal Open Job Step entity
    """
    
    param_type_map = {
        'INT': IntTaskParameterDefinition,
        'FLOAT': FloatTaskParameterDefinition,
        'STRING': StringTaskParameterDefinition,
        'PATH': PathTaskParameterDefinition
    }

    def __init__(
            self,
            file_path: str,
            name: str = None,
            step_dependencies: list[str] = None,
            environments: list = None,
            extra_parameters=None,
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
        """
        
        self._step_dependencies = step_dependencies or []

        # TODO - Santi: Test this
        self._environments = []
        if environments:
            self._environments = [
                UnrealOpenJobEnvironment(file_path=environment.file_path, name=environment.name)
                for environment in environments
            ]

        # TODO - Santi: Ask about this
        self._extra_parameters = extra_parameters or []

        super().__init__(StepTemplate, file_path, name)
        
    @property
    def step_dependencies(self) -> list[str]:
        """
        Returns the list of step dependencies
        """
        
        return self._step_dependencies
    
    @property
    def environments(self) -> list[UnrealOpenJobEnvironment]:
        """
        Returns the list of environments
        """
        
        return self._environments
    
    @property
    def extra_parameters(self) -> list:
        """
        Returns the list of extra parameters
        """
        
        return self._extra_parameters

    def _build_step_parameter_definition_list(self) -> list:
        """
        Build the job parameter definition list from the step template object.
        """
        
        step_template_object = self.get_template_object()

        step_parameter_definition_list = JobParameterDefinitionList()

        params = step_template_object['parameterSpace']['taskParameterDefinitions']
        for param in params:
            override_param = (
                next((p for p in self.extra_parameters if p.get('name', '') == param['name']), None)
                if self.extra_parameters else None
            )
            if override_param:
                param.update(override_param)

            param_definition_cls = self.param_type_map.get(param['type'])
            if param_definition_cls:
                step_parameter_definition_list.append(
                    param_definition_cls(**param)
                )

        return step_parameter_definition_list
        
    def build(self) -> StepTemplate:
        step_template_object = self.get_template_object()
        
        if not self.name:
            self._name = step_template_object['name']
        
        step_creation_kwargs = {
            'name': self.name,
            'script': StepScript(
                actions=StepActions(
                    onRun=Action(
                        command=step_template_object['script']['actions']['onRun']['command'],
                        args=step_template_object['script']['actions']['onRun'].get('args', [])
                    )
                )
            ),
            'parameterSpace': StepParameterSpaceDefinition(
                taskParameterDefinitions=self._build_step_parameter_definition_list()
            )
        }
        
        if self._environments:
            step_creation_kwargs['environments'] = self._environments
        if self._step_dependencies:
            step_creation_kwargs['dependencies'] = self._step_dependencies

        step_template = self.template_class(**step_creation_kwargs)

        return step_template


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
            task_chunk_size: int = None,
            shots_count: int = None
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
        
        :param shots_count: The shots count
        :type shots_count: int
        """
        
        self._task_chunk_size = task_chunk_size
        self._shots_count = shots_count

        super().__init__(file_path, name, step_dependencies, environments, extra_parameters)

    @staticmethod
    def validate_parameters(parameters: list) -> bool:
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
        
    def get_parameters(self) -> dict:
        """
        Get parameters
        """
        
        if not self._task_chunk_size or not self._shots_count:
            raise ValueError('Task chunk size and shots count must be provided')
        
        step_object = self.get_template_object()

        task_chunk_size = {'name': 'TaskChunkSize', 'type': 'INT', 'range': [self._task_chunk_size]}
        task_chunk_size_updated = False

        task_chunk_ids_count = math.ceil(self._shots_count / self._task_chunk_size)
        task_chunk_ids = [i for i in range(task_chunk_ids_count)]
        task_chunk_id = {'name': 'TaskChunkId', 'type': 'INT', 'range': task_chunk_ids}
        task_chunk_id_updated = False

        for param_definition in step_object['parameterSpace']['taskParameterDefinitions']:
                
            if param_definition['name'] == task_chunk_size['name']:
                param_definition.update(task_chunk_size)
                task_chunk_size_updated = True

            if param_definition['name'] == task_chunk_id['name']:
                param_definition.update(task_chunk_id)
                task_chunk_id_updated = True

        if not task_chunk_size_updated:
            step_object['parameterSpace']['taskParameterDefinitions'].append(task_chunk_size)
        if not task_chunk_id_updated:
            step_object['parameterSpace']['taskParameterDefinitions'].append(task_chunk_id)

        return step_object['parameterSpace']['taskParameterDefinitions']
    
    def build(self) -> StepTemplate:
        """
        Build the definition template entity
        """
        
        for param in self.get_parameters():
            self.extra_parameters.append(param)
            
        step_entity = super().build()
        
        RenderUnrealOpenJobStep.validate_parameters(
            step_entity.parameterSpace.taskParameterDefinitions
        )
        
        return step_entity
