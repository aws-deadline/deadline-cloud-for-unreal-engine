import math
import json
import unreal

from openjd.model.v2023_09 import *

from src.deadline.unreal_submitter.unreal_open_job import UnrealOpenJobEntity, UnrealOpenJobEnvironment


class UnrealOpenJobStep(UnrealOpenJobEntity):

    def __init__(
            self,
            file_path: str,
            name: str = None,
            step_dependencies: list[str] = None,
            environments: list = None,
            extra_parameters=None,
    ):
        self._step_dependencies = step_dependencies

        self._environments = [
            UnrealOpenJobEnvironment(file_path=environment.path.file_path, name=environment.name)
            for environment in environments
        ]

        self._extra_parameters = extra_parameters

        super().__init__(StepTemplate, file_path, name)

    def build(self):
        step_template_object = self.get_template_object()
        # step_template = StepTemplate.model_validate_json(json.dumps(step_template_object))

        step_template = self.template_class(
            name=self.name,
            script=StepScript(
                actions=StepActions(
                    onRun=Action(
                        command=step_template_object['script']['actions']['onRun']['command'],
                        args=step_template_object['script']['actions']['onRun'].get('args', [])
                    )
                )
            )
        )

        return step_template

        # if self._environments:
        #     step_entity['stepEnvironments'] = [env.build() for env in self._environments]
        #
        # if self._step_dependencies:
        #     step_entity['dependencies'] = [
        #         {'dependsOn': step_dependency} for step_dependency in self._step_dependencies
        #     ]
        #
        # if self._extra_parameters:
        #     for param_definition in step_entity['parameterSpace']['taskParameterDefinitions']:
        #         param = next((p for p in self._extra_parameters if p.name == param_definition['name']), None)
        #         if param:
        #             param_definition.update({'range': [param.value]})
        #
        # return step_entity


class RenderUnrealOpenJobStep(UnrealOpenJobStep):

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

        self._task_chunk_size = task_chunk_size
        self._shots_count = shots_count

        RenderUnrealOpenJobStep.validate_parameters(extra_parameters)
        super().__init__(file_path, name, step_dependencies, environments, extra_parameters)

    @staticmethod
    def validate_parameters(parameters: list) -> bool:
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

    def build(self):
        step_entity = self.get_template_object()

        task_chunk_size = {'name': 'TaskChunkSize', 'type': 'INT', 'range': [self._task_chunk_size]}
        task_chunk_size_updated = False

        task_chunk_ids_count = math.ceil(self._shots_count / self._task_chunk_size)
        task_chunk_ids = [i for i in range(task_chunk_ids_count)]
        task_chunk_id = {'name': 'TaskChunkId', 'type': 'INT', 'range': task_chunk_ids}
        task_chunk_id_updated = False

        for param_definition in step_entity['parameterSpace']['taskParameterDefinitions']:
            if param_definition['name'] == task_chunk_size['name']:
                param_definition.update(task_chunk_size)
                task_chunk_size_updated = True

            if param_definition['name'] == task_chunk_id['name']:
                param_definition.update(task_chunk_id)
                task_chunk_id_updated = True

        if not task_chunk_size_updated:
            step_entity['parameterSpace']['taskParameterDefinitions'].append(task_chunk_size)
        if not task_chunk_id_updated:
            step_entity['parameterSpace']['taskParameterDefinitions'].append(task_chunk_id)

        return step_entity
