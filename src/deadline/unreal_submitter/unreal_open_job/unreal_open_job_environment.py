from openjd.model.v2023_09 import EnvironmentTemplate

from src.deadline.unreal_submitter.unreal_open_job import UnrealOpenJobEntity


class UnrealOpenJobEnvironment(UnrealOpenJobEntity):

    def __init__(self, file_path: str, name: str = None):
        super().__init__(EnvironmentTemplate, file_path, name)


class LaunchEditorUnrealOpenJobEnvironment(UnrealOpenJobEnvironment):

    def __init__(
            self,
            file_path: str,
            name: str = None,
            unreal_executable: str = None,
            unreal_project_path: str = None,
            unreal_cmd_args: list[str] = None
    ):

        self.ue_executable = unreal_executable or 'UnrealEditor-Cmd.exe'

        ue_project_path = unreal_project_path or '%UNREAL_PROJECT_PATH%'

        self.ue_cmd_args = unreal_cmd_args or ['-log']
        self.ue_cmd_args.insert(0, ue_project_path)

        super().__init__(file_path, name)

    def build(self):
        environment_entity = super().build()

        launch_script = {
            'actions': {
                'onEnter': {
                    'command': self.ue_executable,
                    'args': self.ue_cmd_args
                }
            }
        }
        if environment_entity.get('script', {}):
            environment_entity['script'].update(launch_script)
        else:
            environment_entity['script'] = launch_script

        return environment_entity

