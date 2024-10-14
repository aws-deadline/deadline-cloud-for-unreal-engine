import unreal

from openjd.model.v2023_09 import *

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import UnrealOpenJobEntity


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
