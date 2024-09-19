import re
import unreal

from openjd.model.v2023_09 import *

from src.deadline.unreal_submitter import common
from src.deadline.unreal_submitter.unreal_open_job\
    .unreal_open_job_entity import UnrealOpenJobEntity
from src.deadline.unreal_submitter.unreal_open_job\
    .unreal_open_job_step import UnrealOpenJobStep, RenderUnrealOpenJobStep
from src.deadline.unreal_submitter.unreal_open_job\
    .unreal_open_job_environment import UnrealOpenJobEnvironment, LaunchEditorUnrealOpenJobEnvironment


SPECIFICATION_VERSION = 'jobtemplate-2023-09'


class UnrealOpenJob(UnrealOpenJobEntity):
    """
    Open Job for Unreal Engine
    """

    param_type_map = {
        'INT': JobIntParameterDefinition,
        'FLOAT': JobFloatParameterDefinition,
        'STRING': JobStringParameterDefinition,
        'PATH': JobPathParameterDefinition
    }

    def __init__(
        self,
        file_path: str,
        name: str = None,
        steps: list = None,
        environments: list = None,
        extra_parameters: list = None
    ):
        """
        :file_path Path to the open job template file
        :type file_path str
        
        :name Name of the job
        :type name str
        
        :steps List of steps to be executed by deadline cloud
        :type steps list
        
        :environments List of environments to be used by deadline cloud
        :type environments list
        
        :extra_parameters List of additional parameters to be added to the job
        :type extra_parameters list
        """

        self._extra_parameters = extra_parameters or []

        super().__init__(JobTemplate, file_path, name)

        self._steps = self._create_steps(steps)
        self._environments= self._create_environments(environments)

    def _create_steps(self, steps: list = None) -> list[UnrealOpenJobStep]:
        """
        Create a list of steps to be executed by deadline cloud
        
        :steps List of steps to be executed by deadline cloud
        :type steps list
        
        :return List of steps to be executed by deadline cloud
        :rtype list[UnrealOpenJobStep]
        """
        
        if not steps:
            return []
        return [
            UnrealOpenJobStep(
                file_path=step.file_path,
                name=step.name,
                step_dependencies=step.step_dependencies or [],
                environments=step.environments,
                extra_parameters=step.extra_parameters
            )
            for step in steps
        ]

    def _create_environments(self, environments: list = None) -> list[UnrealOpenJobEnvironment]:
        """
        Create a list of environments to be used by deadline cloud
        """
        
        if not environments:
            return []
        return [UnrealOpenJobEnvironment(file_path=env.file_path, name=env.name) for env in environments]

    def _build_job_parameter_definition_list(self) -> JobParameterDefinitionList:
        """
        Build a list of job parameter definitions
        """
        
        job_template_object = self.get_template_object()

        job_parameter_definition_list = JobParameterDefinitionList()

        params = job_template_object['parameterDefinitions']
        for param in params:
            override_param = (
                next((p for p in self._extra_parameters if p.get('name', '') == param['name']), None)
                if self._extra_parameters else None
            )
            if override_param:
                param.update(override_param)

            param_definition_cls = self.param_type_map.get(param['type'])
            if param_definition_cls:
                job_parameter_definition_list.append(
                    param_definition_cls(**param)
                )

        return job_parameter_definition_list

    def build(self) -> JobTemplate:
        parameter_definitions = self._build_job_parameter_definition_list()
        steps = [s.build() for s in self._steps]
        environments = [e.build() for e in self._environments]
        
        job_template = self.template_class(
            specificationVersion=SPECIFICATION_VERSION,
            name=self.name,
            parameterDefinitions=parameter_definitions,
            steps=steps,
            jobEnvironments=environments
        )

        return job_template


class RenderUnrealOpenJob(UnrealOpenJob):
    """
    Unreal Open Job for rendering Unreal Engine projects
    """

    # TODO map C++ class instead of env name
    job_environment_map = {
        'LaunchUnrealEditor': LaunchEditorUnrealOpenJobEnvironment
    }

    # TODO map C++ class instead of step name
    job_step_map = {
        'RenderStep': RenderUnrealOpenJobStep
    }

    def __init__(
            self,
            file_path: str,
            name: str = None,
            steps: list = None,
            environments: list = None,
            extra_parameters: list = None,
            mrq_job: unreal.MoviePipelineExecutorJob = None,
            executable: str = None,
            extra_cmd_args: str = None,
            changelist_number: int = None,
            task_chunk_size: int = None,
            task_shot_count: int = None
    ):
        self._mrq_job = mrq_job
        self._executable = executable
        self._extra_cmd_args = extra_cmd_args
        self._changelist_number = changelist_number
        self._task_chunk_size = task_chunk_size
        self._task_shot_count = task_shot_count

        super().__init__(file_path, name, steps, environments, extra_parameters)

    def _create_steps(self, steps: list = None) -> list[UnrealOpenJobStep]:
        created_steps = []
        for step in steps:
            job_step_cls = self.job_step_map.get(step.name, UnrealOpenJobStep)
            creation_kwargs = dict(
                file_path=step.file_path,
                name=step.name,
                step_dependencies=step.step_dependencies,
                environments=step.environments,
                extra_parameters=step.extra_parameters,
            )
            if job_step_cls == RenderUnrealOpenJobStep:
                creation_kwargs['task_chunk_size'] = self._task_chunk_size
                creation_kwargs['shots_count'] = self._task_shot_count

            created_steps.append(job_step_cls(**creation_kwargs))

        return created_steps

    def _create_environments(self, environments: list = None) -> list[UnrealOpenJobEnvironment]:
        created_environments = []
        for env in environments:
            job_env_cls = self.job_environment_map.get(env.name, UnrealOpenJobEnvironment)
            creation_kwargs = dict(file_path=env.file_path, name=env.name)

            if job_env_cls == LaunchEditorUnrealOpenJobEnvironment:
                # TODO check for C++ class instead of env name
                workspace_creation_step = next((env for env in environments if env.name in ['UGS', 'P4']), None)
                creation_kwargs['unreal_executable'] = self._executable
                creation_kwargs['unreal_project_path'] = common.get_project_file_path() if not workspace_creation_step else None
                creation_kwargs['unreal_cmd_args'] = self._get_ue_cmd_args()

            created_environments.append(job_env_cls(**creation_kwargs))

        return created_environments

    def _get_ue_cmd_args(self):
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

        if self._extra_cmd_args:
            extra_cmds_args = re.sub(
                pattern=".*(?P<cmds>-execcmds=[\s\S]+[\'\"])",
                repl="", string=self._extra_cmd_args
            )
            if extra_cmds_args:
                cmd_args.extend(extra_cmds_args.split(' '))

        # remove duplicates
        cmd_args = list(set(cmd_args))

        return cmd_args
