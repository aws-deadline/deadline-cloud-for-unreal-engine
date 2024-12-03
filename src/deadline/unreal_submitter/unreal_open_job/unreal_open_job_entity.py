import os
import yaml
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Type, Union, Literal, Optional

from openjd.model.v2023_09 import (
    JobTemplate,
    StepTemplate,
    Environment,
    JobIntParameterDefinition,
    JobFloatParameterDefinition,
    JobStringParameterDefinition,
    JobPathParameterDefinition,
    IntTaskParameterDefinition,
    FloatTaskParameterDefinition,
    StringTaskParameterDefinition,
    PathTaskParameterDefinition,
)

from deadline.client.job_bundle.submission import AssetReferences

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_parameters_consistency import (
    ParametersConsistencyCheckResult,
)
from deadline.unreal_submitter import exceptions, settings
from deadline.unreal_logger import get_logger


logger = get_logger()


Template = Union[JobTemplate, StepTemplate, Environment]
TemplateClass = Union[Type[JobTemplate], Type[StepTemplate], Type[Environment]]


class UnrealOpenJobEntityBase(ABC):
    """
    Base class for Unreal Open Job entities
    """

    @property
    @abstractmethod
    def template_class(self) -> TemplateClass:
        """
        Returns the template class for the entity
        """

    @property
    @abstractmethod
    def file_path(self) -> str:
        """
        Returns the file path of the entity descriptor
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the entity
        """

    @abstractmethod
    def get_template_object(self) -> dict:
        """
        Returns the template object from the entity descriptor
        """

    @abstractmethod
    def build_template(self) -> Template:
        """
        Builds the entity template
        """


class UnrealOpenJobEntity(UnrealOpenJobEntityBase):
    """
    Base class for Unreal Open Job entities

    :cvar default_template_path: Path of the YAML template relative to settings.OPENJD_TEMPLATES_DIRECTORY
    """

    default_template_path: Optional[str] = None

    def __init__(self, template_class: TemplateClass, file_path: str = None, name: str = None):
        """
        :param template_class: The template class for the entity
        :type template_class: TemplateClass

        :param file_path: The file path of the entity descriptor
        :type file_path: str

        :param name: The name of the entity
        :type name: str
        """

        self._template_class = template_class
        self._file_path: Optional[str] = None

        if file_path is not None:
            template_path = file_path
        else:
            template_path = "{templates_dir}/{template_path}".format(
                templates_dir=settings.OPENJD_TEMPLATES_DIRECTORY,
                template_path=self.default_template_path,
            )

        if os.path.exists(template_path):
            self._file_path = template_path.replace("\\", "/")
        else:
            self._file_path = file_path

        if name is not None:
            self._name = name
        else:
            default_name = f"Untitled-{self.template_class.__name__}"
            try:
                self._name = self.get_template_object().get("name", default_name)
            except (FileNotFoundError, AttributeError):
                self._name = default_name

    @property
    def template_class(self):
        """Returns the OpenJD template class of the entity"""
        return self._template_class

    @property
    def name(self):
        """Returns the name of the entity"""
        return self._name

    @property
    def file_path(self):
        """Returns the file path of the entity"""
        return self._file_path

    def _build_template(self) -> Template:
        """
        Base method to build OpenJD model from YAML template

        :return: Template instance (JobTemplate, StepTemplate, Environment)
        :rtype: Template
        """
        template_object = self.get_template_object()
        return self.template_class(**template_object)

    def _validate_parameters(self) -> bool:
        """
        Validate parameters of the entity by checking parameters consistency

        :raises exceptions.ParametersAreNotConsistentError: When parameters are not consistent

        :return: True if parameters are consistent, False otherwise
        :rtype: bool
        """
        result = self._check_parameters_consistency()
        if not result.passed:
            raise exceptions.ParametersAreNotConsistentError(result.reason)
        return True

    def _check_parameters_consistency(self) -> ParametersConsistencyCheckResult:
        """
        Base implementation of checking entity parameters consistency

        :return: Parameters consistency check result that indicates variables consistent or not
        :rtype: ParametersConsistencyCheckResult
        """
        return ParametersConsistencyCheckResult(True, "Parameters are consistent")

    def build_template(self) -> Template:
        """
        Base implementation of building entity template.
        Calls _build_template() that can be overridden in child classes

        :return: Template instance (JobTemplate, StepTemplate, Environment)
        :rtype: Template
        """
        self._validate_parameters()
        return self._build_template()

    def get_template_object(self) -> dict:
        """
        Read the template YAML file and return it as a dict

        :return: Template descriptor
        :rtype: dict
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f'Descriptor file "{self.file_path}" not found')

        with open(self.file_path, "r") as f:
            template = yaml.safe_load(f)

        return template

    def get_asset_references(self) -> AssetReferences:
        """
        Return asset references to include to upload list on submission

        :return: AssetReferences instance
        :rtype: AssetReferences
        """
        return AssetReferences()


@dataclass
class ParameterDefinitionDescriptor:
    """
    Data class for converting C++, OpenJD and generic Python classes between each other

    :cvar type_name: OpenJD type (INT, FLOAT, STRING, PATH)
    :cvar job_parameter_openjd_class: OpenJD class for int, float, string, path Job parameter
    :cvar task_parameter_openjd_class: OpenJD class for int, float, string, path Step parameter
    :cvar python_class: Appropriate python class (int, float, string, path)
    """

    type_name: Literal["INT", "FLOAT", "STRING", "PATH"]
    job_parameter_openjd_class: type[
        Union[
            JobIntParameterDefinition,
            JobFloatParameterDefinition,
            JobStringParameterDefinition,
            JobPathParameterDefinition,
        ]
    ]
    job_parameter_attribute_name: Literal["int_value", "float_value", "string_value", "path_value"]
    task_parameter_openjd_class: type[
        Union[
            IntTaskParameterDefinition,
            FloatTaskParameterDefinition,
            StringTaskParameterDefinition,
            PathTaskParameterDefinition,
        ]
    ]
    python_class: type[Union[int, float, str]]


PARAMETER_DEFINITION_MAPPING = {
    "INT": ParameterDefinitionDescriptor(
        "INT", JobIntParameterDefinition, "int_value", IntTaskParameterDefinition, int
    ),
    "FLOAT": ParameterDefinitionDescriptor(
        "FLOAT", JobFloatParameterDefinition, "float_value", FloatTaskParameterDefinition, float
    ),
    "STRING": ParameterDefinitionDescriptor(
        "STRING", JobStringParameterDefinition, "string_value", StringTaskParameterDefinition, str
    ),
    "PATH": ParameterDefinitionDescriptor(
        "PATH", JobPathParameterDefinition, "path_value", PathTaskParameterDefinition, str
    ),
}


class OpenJobParameterNames:
    """
    Class that contains default Job parameter names that can be used during the submission.
    These parameters can be automatically updated during the submission if no value is provided.

    :cvar UNREAL_PROJECT_PATH: Full local Unreal project path
    :cvar UNREAL_PROJECT_NAME: Unreal project name
    :cvar UNREAL_PROJECT_RELATIVE_PATH: Unreal project path relative to P4 workspace root
    :cvar UNREAL_EXTRA_CMD_ARGS: Extra command line arguments to launch Unreal with
    :cvar UNREAL_EXTRA_CMD_ARGS_FILE: Path to file containing extra command line arguments
                                      to launch Unreal with
    :cvar UNREAL_EXECUTABLE_RELATIVE_PATH: UE executable path relative to P4 workspace root
    :cvar PERFORCE_STREAM_PATH: P4 stream path, e.g. //MyProject/Mainline
    :cvar PERFORCE_CHANGELIST_NUMBER: P4 changelist to sync workspace to
    """

    UNREAL_PROJECT_PATH = "ProjectFilePath"
    UNREAL_PROJECT_NAME = "ProjectName"
    UNREAL_PROJECT_RELATIVE_PATH = "ProjectRelativePath"
    UNREAL_EXTRA_CMD_ARGS = "ExtraCmdArgs"
    UNREAL_EXTRA_CMD_ARGS_FILE = "ExtraCmdArgsFile"
    UNREAL_EXECUTABLE_RELATIVE_PATH = "ExecutableRelativePath"
    UNREAL_MRQ_JOB_DEPENDENCIES_DESCRIPTOR = "MrqJobDependenciesDescriptor"

    PERFORCE_STREAM_PATH = "PerforceStreamPath"
    PERFORCE_CHANGELIST_NUMBER = "PerforceChangelistNumber"
    PERFORCE_WORKSPACE_SPECIFICATION_TEMPLATE = "PerforceWorkspaceSpecificationTemplate"


class OpenJobStepParameterNames:
    """
    Class that contains default OpenJD step parameter names that can be used during the submission.
    These parameters can be automatically updated during the submission if no value is provided.

    :cvar QUEUE_MANIFEST_PATH: Local path to file that contains serialized MoviePipelineQueue
    :cvar MOVIE_PIPELINE_QUEUE_PATH: Unreal path to MoviePipelineQueue asset
    :cvar LEVEL_SEQUENCE_PATH: Unreal path to LevelSequence asset
    :cvar LEVEL_PATH: Unreal path to Level asset
    :cvar MRQ_JOB_CONFIGURATION_PATH: Unreal path to MoviePipelinePrimaryConfig asset
    :cvar OUTPUT_PATH: Local path where Unreal Render Executor will place output files

    :cvar ADAPTOR_HANDLER: Handler name to run the jobs on Adaptor (render/custom)
    :cvar TASK_CHUNK_SIZE: Count of the shots per OpenJD Step's Task
    :cvar TASK_CHUNK_ID: Chunk number that should be rendered at OpenJD Step's Task
    """

    QUEUE_MANIFEST_PATH = "QueueManifestPath"
    MOVIE_PIPELINE_QUEUE_PATH = "MoviePipelineQueuePath"
    LEVEL_SEQUENCE_PATH = "LevelSequencePath"
    LEVEL_PATH = "LevelPath"
    MRQ_JOB_CONFIGURATION_PATH = "MrqJobConfigurationPath"
    OUTPUT_PATH = "OutputPath"

    ADAPTOR_HANDLER = "Handler"
    TASK_CHUNK_SIZE = "ChunkSize"
    TASK_CHUNK_ID = "ChunkId"
