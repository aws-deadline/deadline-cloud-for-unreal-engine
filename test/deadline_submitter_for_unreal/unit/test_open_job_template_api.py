# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import copy
import importlib.util
import sys
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest


class ValueType(Enum):
    STRING = "STRING"
    PATH = "PATH"
    INT = "INT"
    FLOAT = "FLOAT"


class ParameterDefinition(SimpleNamespace):
    def __init__(self):
        super().__init__(value="", allowed_values=[], user_interface_control="LINE_EDIT")

    def copy(self):
        return copy.deepcopy(self)


@pytest.fixture
def template_api(monkeypatch):
    unreal = MagicMock()
    unreal.uclass.side_effect = lambda: lambda cls: cls
    unreal.ufunction.side_effect = lambda **kwargs: lambda fn: fn
    unreal.PythonYamlLibrary = type("PythonYamlLibrary", (), {})
    unreal.PythonParametersConsistencyChecker = type("PythonParametersConsistencyChecker", (), {})
    unreal.ParameterDefinition = ParameterDefinition
    unreal.ValueType = ValueType
    unreal.UserInterfaceControl = SimpleNamespace(
        **{
            control: control
            for control in (
                "LINE_EDIT",
                "MULTILINE_EDIT",
                "DROPDOWN_LIST",
                "CHECK_BOX",
                "HIDDEN",
                "CHOOSE_INPUT_FILE",
                "CHOOSE_OUTPUT_FILE",
                "CHOOSE_DIRECTORY",
                "SPIN_BOX",
            )
        }
    )
    monkeypatch.setitem(sys.modules, "unreal", unreal)
    path = (
        Path(__file__).resolve().parents[3]
        / "src/unreal_plugin/Content/Python/open_job_template_api.py"
    )
    spec = importlib.util.spec_from_file_location("dropdown_template_api_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "param_type, choices, default",
    [
        ("STRING", ["false", "true"], "false"),
        ("STRING", ["", "submit", "shelve"], ""),
        ("INT", [0, 1, 2], 0),
        ("FLOAT", [0.5, 1.5], 0.5),
        ("PATH", ["first/path", "second/path"], "first/path"),
    ],
)
def test_dropdown_metadata_and_value(template_api, param_type, choices, default):
    parameter = (
        template_api.PythonYamlLibraryImplementation.job_parameter_to_u_parameter_definition(
            {
                "name": "Choice",
                "type": param_type,
                "allowedValues": choices,
                "default": default,
                "userInterface": {"control": "DROPDOWN_LIST"},
            }
        )
    )
    assert parameter.user_interface_control == "DROPDOWN_LIST"
    assert parameter.allowed_values == [str(choice) for choice in choices]
    assert parameter.value == str(default)


@pytest.mark.parametrize("control", [None, "LINE_EDIT", "UNKNOWN"])
def test_text_parameter_remains_text_input(template_api, control):
    definition: dict[str, Any] = dict(name="Text", type="STRING", default="default", value="edited")
    if control is not None:
        definition["userInterface"] = {"control": control}
    parameter = (
        template_api.PythonYamlLibraryImplementation.job_parameter_to_u_parameter_definition(
            definition
        )
    )
    assert parameter.user_interface_control == "LINE_EDIT"
    assert parameter.allowed_values == []
    assert parameter.value == "edited"


@pytest.mark.parametrize("param_type", ["STRING", "PATH", "INT", "FLOAT"])
@pytest.mark.parametrize("user_interface", [None, {}, {"label": "Choice"}])
def test_allowed_values_default_to_dropdown(template_api, param_type, user_interface):
    definition = dict(name="Choice", type=param_type, allowedValues=["0", "1"], default="0")
    if user_interface is not None:
        definition["userInterface"] = user_interface
    parameter = (
        template_api.PythonYamlLibraryImplementation.job_parameter_to_u_parameter_definition(
            definition
        )
    )
    assert parameter.user_interface_control == "DROPDOWN_LIST"
    assert parameter.allowed_values == ["0", "1"]
    assert parameter.value == "0"


@pytest.mark.parametrize(
    "file_name, name, choices, default",
    [
        ("render_job.yml", "IgnorePlugins", ["false", "true"], "false"),
        ("p4/p4_render_job.yml", "SubmitMode", ["", "submit", "shelve"], ""),
    ],
)
def test_shipped_dropdown_choices(template_api, file_name, name, choices, default):
    template = (
        Path(__file__).resolve().parents[3]
        / "src/unreal_plugin/Content/Python/openjd_templates"
        / file_name
    )
    parameters = template_api.PythonYamlLibraryImplementation().open_job_file(str(template))
    parameter = next(param for param in parameters if param.name == name)
    assert parameter.user_interface_control == "DROPDOWN_LIST"
    assert parameter.allowed_values == choices
    assert parameter.value == default
