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
from deadline.unreal_submitter import exceptions
from deadline.unreal_logger import get_logger


logger = get_logger()


Template = Union[JobTemplate, StepTemplate, Environment]
TemplateClass = Union[Type[JobTemplate], Type[StepTemplate], Type[Environment]]


OPENJD_TEMPLATES_DIRECTORY = "OPENJD_TEMPLATES_DIRECTORY"


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
                templates_dir=os.getenv(OPENJD_TEMPLATES_DIRECTORY),
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
        return self._template_class

    @property
    def name(self):
        return self._name

    @property
    def file_path(self):
        return self._file_path

    def _build_template(self) -> Template:
        template_object = self.get_template_object()
        return self.template_class(**template_object)

    def _validate_parameters(self) -> bool:
        result = self._check_parameters_consistency()
        if not result.passed:
            raise exceptions.ParametersAreNotConsistentError(result.reason)
        return True

    def _check_parameters_consistency(self) -> ParametersConsistencyCheckResult:
        return ParametersConsistencyCheckResult(True, "Parameters are consensual")

    def build_template(self) -> Template:
        self._validate_parameters()
        return self._build_template()

    def get_template_object(self) -> dict:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f'Descriptor file "{self.file_path}" not found')

        with open(self.file_path, "r") as f:
            template = yaml.safe_load(f)

        return template

    def get_asset_references(self) -> AssetReferences:
        return AssetReferences()


@dataclass
class ParameterDefinitionDescriptor:
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

    UNREAL_PROJECT_PATH = "ProjectFilePath"
    UNREAL_PROJECT_NAME = "ProjectName"
    UNREAL_PROJECT_RELATIVE_PATH = "ProjectRelativePath"
    UNREAL_EXTRA_CMD_ARGS = "ExtraCmdArgs"
    UNREAL_EXTRA_CMD_ARGS_FILE = "ExtraCmdArgsFile"
    UNREAL_EXECUTABLE_RELATIVE_PATH = "ExecutableRelativePath"

    PERFORCE_STREAM_PATH = "PerforceStreamPath"
    PERFORCE_CHANGELIST_NUMBER = "PerforceChangelistNumber"


class OpenJobStepParameterNames:

    QUEUE_MANIFEST_PATH = "QueueManifestPath"
    MOVIE_PIPELINE_QUEUE_PATH = "MoviePipelineQueuePath"
    LEVEL_SEQUENCE_PATH = "LevelSequencePath"
    LEVEL_PATH = "LevelPath"
    MRQ_JOB_CONFIGURATION_PATH = "MrqJobConfigurationPath"
    OUTPUT_PATH = "OutputPath"

    ADAPTOR_HANDLER = "Handler"
    TASK_CHUNK_SIZE = "ChunkSize"
    TASK_CHUNK_ID = "ChunkId"
