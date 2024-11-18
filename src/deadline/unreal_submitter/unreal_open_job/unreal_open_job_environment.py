import unreal
from openjd.model.v2023_09 import Environment, EnvironmentScript

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import UnrealOpenJobEntity
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_parameters_consistency import (
    ParametersConsistencyChecker,
)


class UnrealOpenJobEnvironment(UnrealOpenJobEntity):
    """
    Unreal Open Job Environment entity
    """

    def __init__(self, file_path: str, name: str = None, variables: dict = None):
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
            file_path=data_asset.path_to_template.file_path,
            name=data_asset.name,
            variables=data_asset.variables.variables,
        )

    def _check_parameters_consistency(self):

        result = ParametersConsistencyChecker.check_environment_variables_consistency(
            environment_template_path=self.file_path, environment_variables=self._variables
        )
        result.reason = f'OpenJob Environment "{self.name}": ' + result.reason

        return result

    def _build_template(self) -> Environment:
        environment_template_object = self.get_template_object()
        script = environment_template_object.get("script")
        return self.template_class(
            name=self.name,
            script=EnvironmentScript(**script) if script else None,
            variables=self._variables if self._variables else None,
        )


class UnrealOpenJobUgsEnvironment(UnrealOpenJobEnvironment):
    pass
