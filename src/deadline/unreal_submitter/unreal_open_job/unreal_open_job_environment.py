import unreal
import yaml

from openjd.model.v2023_09 import *
from openjd.model import decode_environment_template

from deadline.unreal_submitter import settings
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
        
        super().__init__(Environment, file_path, name)

    @classmethod
    def from_data_asset(cls, data_asset: unreal.DeadlineCloudEnvironment):
        return cls(
            file_path=data_asset.path_to_template,
            name=data_asset.name
        )

    # TODO investigate why EnvironmentTemplate call validation method
    #   openjd.model.v2023_09._model.Environment._validate_has_script_or_variables
    #   twice: on Environment creation and on EnvironmentTemplate creation.
    #   In first case validation passed.
    #   In second - fails because EnvironmentTemplate values passed to method instead of Environment one
    def build_template(self) -> Environment:
        environment_template_object = self.get_template_object()
        script = environment_template_object.get('script')
        return self.template_class(
            name=self.name,
            script=EnvironmentScript(**script) if script else None,
            variables=environment_template_object.get('variables')
        )

