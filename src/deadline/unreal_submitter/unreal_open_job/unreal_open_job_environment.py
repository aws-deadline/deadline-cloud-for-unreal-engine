from openjd.model.v2023_09 import *

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
        
        super().__init__(EnvironmentTemplate, file_path, name)
        
    def build(self) -> EnvironmentTemplate:
        environment_template_object = self.get_template_object()
        return self.template_class(
            environment=Environment(
                name=self.name,
                script=EnvironmentScript(**environment_template_object['script']),
                variables=environment_template_object.get('variables')
            )

        )
