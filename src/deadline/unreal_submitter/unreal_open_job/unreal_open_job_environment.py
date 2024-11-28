import unreal
from openjd.model.v2023_09 import Environment, EnvironmentScript

from deadline.unreal_submitter import settings
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import UnrealOpenJobEntity
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_parameters_consistency import (
    ParametersConsistencyChecker,
)


# Base Environment implementation
class UnrealOpenJobEnvironment(UnrealOpenJobEntity):
    """
    Unreal Open Job Environment entity
    """

    def __init__(self, file_path: str = None, name: str = None, variables: dict[str, str] = None):
        """
        :param file_path: The file path of the environment descriptor
        :type file_path: str

        :param name: The name of the environment
        :type name: str
        """

        super().__init__(Environment, file_path, name)

        self._variables = variables or {}
        self._create_missing_variables_from_template()

    @property
    def variables(self) -> dict[str, str]:
        return self._variables

    @variables.setter
    def variables(self, value: dict[str, str]):
        self._variables = value

    @classmethod
    def from_data_asset(cls, data_asset: unreal.DeadlineCloudEnvironment):
        return cls(
            file_path=data_asset.path_to_template.file_path,
            name=data_asset.name,
            variables=data_asset.variables.variables,
        )

    def _create_missing_variables_from_template(self):
        try:
            template_variables = self.get_template_object().get("variables", {})
            for key, value in template_variables.items():
                if key not in self._variables:
                    self._variables[key] = value
        except FileNotFoundError:
            pass

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


# Launch Unreal Editor Environment
class LaunchEditorUnrealOpenJobEnvironment(UnrealOpenJobEnvironment):
    default_template_path = settings.LAUNCH_ENVIRONMENT_TEMPLATE_DEFAULT_PATH


# UGS Environments
class UnrealOpenJobUgsEnvironment(UnrealOpenJobEnvironment):
    pass


class UgsLaunchEditorUnrealOpenJobEnvironment(UnrealOpenJobUgsEnvironment):
    default_template_path = settings.UGS_LAUNCH_ENVIRONMENT_TEMPLATE_DEFAULT_PATH


class UgsSyncCmfUnrealOpenJobEnvironment(UnrealOpenJobUgsEnvironment):
    default_template_path = settings.UGS_SYNC_CMF_ENVIRONMENT_TEMPLATE_DEFAULT_PATH


class UgsSyncSmfUnrealOpenJobEnvironment(UnrealOpenJobUgsEnvironment):
    default_template_path = settings.UGS_SYNC_SMF_ENVIRONMENT_TEMPLATE_DEFAULT_PATH
