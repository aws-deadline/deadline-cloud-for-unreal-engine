import openjd.model.v2023_09 as openjd_model

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import UnrealOpenJobEntity


class UnrealOpenJobEnvironment(UnrealOpenJobEntity):
    """
    Unreal Open Job Environment entity
    """

    def __init__(self, file_path: str, name: str = None):
        """
        :param file_path: The file path of the environment descriptor
        :type file_path: str
        
        :param name: The name of the environment
        :type name: str
        """
        
        super().__init__(openjd_model.Environment, file_path, name)
        
    def build(self) -> openjd_model.Environment:
        environment_template_object = self.get_template_object()
        
        if not self.name:
            self._name = environment_template_object.get('name')
            
        environment_creation_kwargs = {
            'name': self.name
        }
        
        if environment_template_object.get('script', {}):
            environment_creation_kwargs['script'] = openjd_model.EnvironmentScript(
                **environment_template_object['script']
            )
            
        if environment_template_object.get('variables', {}):
            environment_creation_kwargs['variables'] = environment_template_object['variables']
            
        return self.template_class(**environment_creation_kwargs)


class LaunchEditorUnrealOpenJobEnvironment(UnrealOpenJobEnvironment):
    """
    Unreal Open Job Environment entity for launching Unreal Editor
    """

    def __init__(
            self,
            file_path: str,
            name: str = None,
            unreal_executable: str = None,
            unreal_project_path: str = None,
            unreal_cmd_args: list[str] = None
    ):
        """
        :param file_path: The file path of the environment descriptor
        :type file_path: str
        
        :param name: The name of the environment
        :type name: str
        
        :param unreal_executable: The Unreal Editor executable
        :type unreal_executable: str
        
        :param unreal_project_path: The Unreal project path
        :type unreal_project_path: str
        
        :param unreal_cmd_args: The Unreal command line arguments
        :type unreal_cmd_args: list[str]
        """

        self.ue_executable = unreal_executable or 'UnrealEditor-Cmd.exe'

        ue_project_path = unreal_project_path or '%UNREAL_PROJECT_PATH%'

        self.ue_cmd_args = unreal_cmd_args or ['-log']
        self.ue_cmd_args.insert(0, ue_project_path)

        super().__init__(file_path, name)

    def build(self) -> openjd_model.Environment:
        environment_object = self.get_template_object()

        launch_script = {
            'actions': {
                'onEnter': {
                    'command': self.ue_executable,
                    'args': self.ue_cmd_args
                }
            }
        }
        if environment_object.get('script', {}):
            environment_object['script'].update(launch_script)
        else:
            environment_object['script'] = launch_script

        environment_creation_kwargs = {
            'name': self.name,
            'script': openjd_model.EnvironmentScript(
                **environment_object['script']
            )
        }
        
        if environment_object.get('variables', {}):
            environment_creation_kwargs['variables'] = environment_object['variables']
            
        return self.template_class(**environment_creation_kwargs)
