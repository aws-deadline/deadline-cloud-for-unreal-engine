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
import yaml


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


class JobTemplateReadResult(SimpleNamespace):
    def __init__(self):
        super().__init__(parameters=[], succeeded=False)


def u_parameter(name, param_type, value="", control="LINE_EDIT", allowed_values=None):
    parameter = ParameterDefinition()
    parameter.name = name
    parameter.type = ValueType[param_type]
    parameter.value = value
    parameter.user_interface_control = control
    parameter.allowed_values = allowed_values or []
    return parameter


def as_tuples(parameters):
    return [
        (p.name, p.type.name, p.value, p.user_interface_control, p.allowed_values)
        for p in parameters
    ]


@pytest.fixture
def template_api(monkeypatch):
    unreal = MagicMock()
    unreal.uclass.side_effect = lambda: lambda cls: cls
    unreal.ufunction.side_effect = lambda **kwargs: lambda fn: fn
    unreal.PythonYamlLibrary = type("PythonYamlLibrary", (), {})
    unreal.PythonParametersConsistencyChecker = type("PythonParametersConsistencyChecker", (), {})
    unreal.ParameterDefinition = ParameterDefinition
    unreal.JobTemplateReadResult = JobTemplateReadResult
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


@pytest.mark.parametrize(
    "contents, succeeded",
    [
        ("name: Empty\n", True),
        ("parameterDefinitions: []\n", True),
        (None, False),
        ("", False),
        ("- not a mapping", False),
        ("parameterDefinitions: [", False),
        ("parameterDefinitions: [{}]", False),
        ("parameterDefinitions:\n- name: Bad\n  type: UNKNOWN\n", False),
    ],
)
def test_read_job_file_result_per_call(template_api, tmp_path, contents, succeeded):
    library = template_api.PythonYamlLibraryImplementation()
    template = tmp_path / "job.yml"
    template.write_text("parameterDefinitions:\n- name: Saved\n  type: STRING\n  default: value\n")
    first = library.read_job_file(str(template))
    template.unlink() if contents is None else template.write_text(contents)
    second = library.read_job_file(str(template))

    assert (first.succeeded, [p.value for p in first.parameters]) == (True, ["value"])
    assert (second.succeeded, second.parameters) == (succeeded, [])
    assert not hasattr(library, "job_file_read_succeeded")
    if not succeeded and contents is not None:
        with pytest.raises((AttributeError, KeyError, ValueError, yaml.YAMLError)):
            library.open_job_file(str(template))


def test_reconcile_job_parameters_bridge(template_api):
    template_parameters = [
        u_parameter("Kept", "STRING", "new-default", "MULTILINE_EDIT"),
        u_parameter("Added", "STRING", "false", "DROPDOWN_LIST", ["false", "true"]),
        u_parameter("Retyped", "INT", "1"),
        u_parameter("InvalidInt", "INT", "2", "SPIN_BOX"),
        u_parameter("Empty", "STRING", "template-default"),
    ]
    saved_parameters = [
        u_parameter("Removed", "STRING", "old"),
        u_parameter("Empty", "STRING", ""),
        u_parameter("InvalidInt", "INT", "not-an-int"),
        u_parameter("Retyped", "STRING", "saved-string"),
        u_parameter("Kept", "STRING", "artist-value"),
    ]

    reconciled = template_api.ParametersConsistencyCheckerImplementation().reconcile_job_parameters(
        template_parameters, saved_parameters
    )

    assert as_tuples(reconciled) == [
        ("Kept", "STRING", "artist-value", "MULTILINE_EDIT", []),
        ("Added", "STRING", "false", "DROPDOWN_LIST", ["false", "true"]),
        ("Retyped", "INT", "1", "LINE_EDIT", []),
        ("InvalidInt", "INT", "not-an-int", "SPIN_BOX", []),
        ("Empty", "STRING", "", "LINE_EDIT", []),
    ]


@pytest.mark.parametrize(
    "contents, saved, expected",
    [
        # No definition differences: saved values must survive
        (
            "parameterDefinitions:\n"
            "- name: Mode\n  type: STRING\n  default: a\n  allowedValues: [a, b]\n"
            "- name: Count\n  type: INT\n  default: 1\n",
            [u_parameter("Count", "INT", "not-an-int"), u_parameter("Mode", "STRING", "b")],
            [
                ("Mode", "STRING", "b", "DROPDOWN_LIST", ["a", "b"]),
                ("Count", "INT", "not-an-int", "LINE_EDIT", []),
            ],
        ),
        ("name: Empty\n", [u_parameter("Removed", "STRING", "old")], []),
    ],
)
def test_fix_job_parameters_consistency_bridge(template_api, tmp_path, contents, saved, expected):
    template = tmp_path / "job.yml"
    template.write_text(contents)
    open_job = MagicMock()
    open_job.path_to_template.file_path = str(template)
    open_job.get_job_parameters.return_value = saved

    template_api.ParametersConsistencyCheckerImplementation().fix_job_parameters_consistency(
        open_job
    )

    (fixed,), _ = open_job.set_job_parameters.call_args
    assert as_tuples(fixed) == expected
