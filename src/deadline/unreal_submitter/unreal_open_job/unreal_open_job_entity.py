import os
import yaml
import json
from pathlib import Path
from typing import Type, Union
from abc import ABC, abstractmethod

from openjd.model.v2023_09 import *
from openjd.model import DocumentType


Template = Union[JobTemplate, StepTemplate, EnvironmentTemplate]
TemplateClass = Union[Type[JobTemplate], Type[StepTemplate], Type[EnvironmentTemplate]]


class UnrealOpenJobEntityBase(ABC):
    
    @property
    @abstractmethod
    def template_class(self) -> TemplateClass:
        pass

    @property
    @abstractmethod
    def file_path(self) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def get_template_object(self) -> dict:
        pass

    @abstractmethod
    def build(self) -> Template:
        pass


class UnrealOpenJobEntity(UnrealOpenJobEntityBase):

    def __init__(self, template_class: TemplateClass, file_path: str, name: str = None):
        self._template_class = template_class
        self._file_path = file_path
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

    def build(self) -> Template:
        raise NotImplementedError
        