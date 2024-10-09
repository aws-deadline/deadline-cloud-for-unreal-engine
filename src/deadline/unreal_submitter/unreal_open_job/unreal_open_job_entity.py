import os
import yaml
import json
import unreal
from pathlib import Path
from dataclasses import dataclass
from typing import Type, Union, Literal
from abc import ABC, abstractmethod

from openjd.model.v2023_09 import *
from openjd.model import DocumentType

from deadline.unreal_submitter import common


Template = Union[JobTemplate, StepTemplate, EnvironmentTemplate]
TemplateClass = Union[Type[JobTemplate], Type[StepTemplate], Type[EnvironmentTemplate]]


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

    def __init__(self, template_class: TemplateClass, file_path: Union[str, unreal.FilePath], name: str = None):
        """
        :param template_class: The template class for the entity
        :type template_class: TemplateClass
        
        :param file_path: The file path of the entity descriptor
        :type file_path: str
        
        :param name: The name of the entity
        :type name: str
        """

        template_path = (file_path.file_path if isinstance(file_path, unreal.FilePath) else file_path).replace('\\', '/')
        if not os.path.isabs(template_path):
            # Case when file under the project directory
            # and UE picker returns relative path (/Game/Developers/job_template.yml)
            template_path = f'{common.get_project_directory()}/{template_path}'

        self._template_class = template_class
        self._file_path = template_path
        self._name = name

    @property
    def template_class(self):
        return self._template_class

    @property
    def name(self) -> str:
        return self._name

    @property
    def file_path(self) -> str:
        return self._file_path

    def get_template_object(self) -> dict:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f'Descriptor file "{self.file_path}" not found')

        file_type = DocumentType.JSON if Path(self.file_path).suffix == '.json' else DocumentType.YAML

        with open(self.file_path, 'r') as f:
            template = json.load(f) if file_type == DocumentType.JSON else yaml.safe_load(f)
            if not self.name and not template.get('name'):
                raise ValueError(f'Descriptor file "{self.file_path}" has no "name" field')
            if self.name:
                template['name'] = self.name

        return template

    def build_template(self) -> Template:
        # TODO: Validate the template object
        template_object = self.get_template_object()
        return self.template_class(**template_object)


@dataclass
class ParameterDefinitionDescriptor:
    type_name: Literal['INT', 'FLOAT', 'STRING', 'PATH']
    job_parameter_openjd_class: type[
        Union[
            JobIntParameterDefinition,
            JobFloatParameterDefinition,
            JobStringParameterDefinition,
            JobPathParameterDefinition,
        ]
    ]
    job_parameter_attribute_name: Literal['int_value', 'float_value', 'string_value', 'path_value']
    task_parameter_openjd_class: type[
        Union[
            IntTaskParameterDefinition,
            FloatTaskParameterDefinition,
            StringTaskParameterDefinition,
            PathTaskParameterDefinition
        ]
    ]
    python_class: type[
        Union[
            int,
            float,
            str
        ]
    ]


PARAMETER_DEFINITION_MAPPING = {
    'INT': ParameterDefinitionDescriptor('INT', JobIntParameterDefinition, 'int_value', IntTaskParameterDefinition, int),
    'FLOAT': ParameterDefinitionDescriptor('FLOAT', JobFloatParameterDefinition, 'float_value', FloatTaskParameterDefinition, float),
    'STRING': ParameterDefinitionDescriptor('STRING', JobStringParameterDefinition, 'string_value', StringTaskParameterDefinition, str),
    'PATH': ParameterDefinitionDescriptor('PATH', JobPathParameterDefinition, 'path_value', PathTaskParameterDefinition, str)
}
