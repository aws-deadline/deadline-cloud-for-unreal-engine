import unreal
from typing import Any

from openjd.model.v2023_09 import *

from deadline.unreal_submitter import common
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (
    UnrealOpenJobEntity,
    OpenJobParameterNames
)


class UnrealOpenJobEnvironment(UnrealOpenJobEntity):
    """
    Unreal Open Job Environment entity
    """

    def __init__(self, file_path: str, name: str = None,  variables: dict = None):
        """
        :param file_path: The file path of the environment descriptor
        :type file_path: str
        
        :param name: The name of the environment
        :type name: str
        """
        
        super().__init__(Environment, file_path, name)

        self._variables = variables or {}

    @classmethod
    def from_data_asset(cls, data_asset: unreal.DeadlineCloudEnvironment):
        return cls(
            file_path=data_asset.path_to_template,
            name=data_asset.name,
            variables=data_asset.variables.variables
        )

    def _check_parameters_consistency(self):
        import open_job_template_api

        template = self.get_template_object()

        result = open_job_template_api.ParametersConsistencyChecker.check_parameters_consistency(
            yaml_parameters=[(k, 'VARIABLE') for k in template['variables'].keys()],
            data_asset_parameters=[(k, 'VARIABLE') for k in self._variables.keys()]
        )

        result.reason = f'OpenJob Environment "{self.name}": ' + result.reason
        return result

    def _build_template(self) -> Environment:
        environment_template_object = self.get_template_object()
        script = environment_template_object.get('script')
        return self.template_class(
            name=self.name,
            script=EnvironmentScript(**script) if script else None,
            variables=self._variables
        )

    @staticmethod
    def get_used_job_parameter_values() -> list[dict[str, Any]]:
        """ Returns a list of OpenJob parameter values that can be used in this environment """
        return []


class UnrealOpenJobUgsEnvironment(UnrealOpenJobEnvironment):

    @staticmethod
    def get_used_job_parameter_values() -> list[dict[str, Any]]:

        from perforce_api import PerforceApi
        perforce = PerforceApi()

        client_root = perforce.get_client_root()
        unreal_project_path = common.get_project_file_path().replace('\\', '/')

        unreal_project_relative_path = unreal_project_path.replace(client_root, '')

        return [
            {'name': OpenJobParameterNames.PERFORCE_STREAM_PATH, 'value': perforce.get_stream_path()},
            {'name': OpenJobParameterNames.UNREAL_PROJECT_NAME, 'value': common.get_project_name()},
            {'name': OpenJobParameterNames.UNREAL_PROJECT_RELATIVE_PATH, 'value': unreal_project_relative_path},
            {'name': OpenJobParameterNames.PERFORCE_CHANGELIST_NUMBER, 'value': str(perforce.get_latest_changelist_number()) or 'latest'},
            {'name': OpenJobParameterNames.UNREAL_EXECUTABLE_RELATIVE_PATH, 'value': ''}  # TODO
        ]

