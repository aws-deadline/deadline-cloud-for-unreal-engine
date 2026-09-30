# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Regression tests for the plugin's pre-GUI hook library.

Target: ``src/unreal_plugin/Content/Python/pre_gui_hook_library.py`` ``_build_output`` — the single
place that names ``FDeadlineCloudPreGuiHookOutput`` UStruct properties. UnrealEngine's Python
bindings strip the leading ``b`` from ``bool`` UPROPERTYs (``bRan`` -> ``ran``), and a wrong name
(e.g. ``b_ran``) raises "Failed to find property" only inside a real editor. Because these unit
tests mock ``unreal`` (a plain ``MagicMock`` would silently accept any name), we install a STRICT
fake output struct that rejects any name not on the real struct — so a property-naming regression
(the ``b_ran`` bug that made the pre-GUI hook silently no-op in the live panel) fails here.
"""

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# FDeadlineCloudPreGuiHookOutput's real UE Python property names (bool UPROPERTYs lose the leading
# 'b'). Mirrors DeadlineCloudPreGuiHookLibrary.h; verified against UE 5.7's get_editor_property.
_VALID_OUTPUT_PROPS = {
    "ran",
    "has_name",
    "name",
    "has_description",
    "description",
    "has_priority",
    "priority",
    "has_initial_state",
    "initial_state",
    "has_max_failed_tasks_count",
    "maximum_failed_tasks_count",
    "has_max_retries_per_task",
    "maximum_retries_per_task",
    "parameters",
    "unapplied_keys",
}


class _StrictStruct:
    """Stand-in for a UStruct that rejects unknown property names, like UE editor-property access."""

    def __init__(self, valid_props):
        self._valid = valid_props
        self._props = {}

    def set_editor_property(self, name, value):
        if name not in self._valid:
            raise Exception(f"Failed to find property '{name}' for attribute '{name}'")
        self._props[name] = value

    def get_editor_property(self, name):
        if name not in self._valid:
            raise Exception(f"Failed to find property '{name}' for attribute '{name}'")
        return self._props.get(name)


@pytest.fixture
def pre_gui_hook_library():
    """Import Content/Python/pre_gui_hook_library.py with ``unreal`` mocked + a strict output struct."""
    plugin_py = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "src",
            "unreal_plugin",
            "Content",
            "Python",
        )
    )

    unreal_mock = MagicMock()
    # uclass()/ufunction(...) become identity decorators so the real module-level functions and the
    # implementation class survive import unchanged.
    unreal_mock.uclass.return_value = lambda cls: cls
    unreal_mock.ufunction.return_value = lambda fn: fn
    # The implementation class subclasses this, so it must be a real class, not a MagicMock instance.
    unreal_mock.DeadlineCloudPreGuiHookLibrary = type(
        "DeadlineCloudPreGuiHookLibrary", (object,), {}
    )
    # Every _build_output() constructs one of these; the strict struct is the regression trap.
    unreal_mock.DeadlineCloudPreGuiHookOutput.side_effect = lambda: _StrictStruct(
        _VALID_OUTPUT_PROPS
    )
    # ParameterDefinition stays loose — only the output struct's property names are under test.
    unreal_mock.ParameterDefinition.side_effect = MagicMock

    saved_unreal = sys.modules.get("unreal")
    saved_mod = sys.modules.pop("pre_gui_hook_library", None)
    sys.modules["unreal"] = unreal_mock
    if plugin_py not in sys.path:
        sys.path.insert(0, plugin_py)
    try:
        import pre_gui_hook_library as mod

        yield mod
    finally:
        sys.modules.pop("pre_gui_hook_library", None)
        if saved_mod is not None:
            sys.modules["pre_gui_hook_library"] = saved_mod
        if saved_unreal is not None:
            sys.modules["unreal"] = saved_unreal
        else:
            sys.modules.pop("unreal", None)


def test_build_output_noop_sets_ran_false(pre_gui_hook_library):
    # No settings => clean no-op the C++ side treats as "leave the panel alone".
    out = pre_gui_hook_library._build_output()
    assert out.get_editor_property("ran") is False
    assert out.get_editor_property("has_name") is None
    assert out.get_editor_property("has_priority") is None


def test_build_output_maps_name_description_and_shared_settings(pre_gui_hook_library):
    # This call raises inside _build_output if any set_editor_property name is wrong (the b_ran bug).
    settings = SimpleNamespace(name="PREGUI RAN", description="populated by pre-GUI hook")
    shared_values = {
        "deadline:priority": 88,
        "deadline:targetTaskRunStatus": "SUSPENDED",
        "deadline:maxFailedTasksCount": 3,
        "deadline:maxRetriesPerTask": 5,
    }

    out = pre_gui_hook_library._build_output(settings, shared_values)

    assert out.get_editor_property("ran") is True
    assert out.get_editor_property("has_name") is True
    assert out.get_editor_property("name") == "PREGUI RAN"
    assert out.get_editor_property("has_description") is True
    assert out.get_editor_property("description") == "populated by pre-GUI hook"
    assert out.get_editor_property("has_priority") is True
    assert out.get_editor_property("priority") == 88
    assert out.get_editor_property("has_initial_state") is True
    assert out.get_editor_property("initial_state") == "SUSPENDED"
    assert out.get_editor_property("has_max_failed_tasks_count") is True
    assert out.get_editor_property("maximum_failed_tasks_count") == 3
    assert out.get_editor_property("has_max_retries_per_task") is True
    assert out.get_editor_property("maximum_retries_per_task") == 5


def test_build_output_only_sets_fields_the_hook_provided(pre_gui_hook_library):
    # Hook set only the name -> priority/description flags stay False (bHas* gating).
    settings = SimpleNamespace(name="OnlyName", description=None)
    out = pre_gui_hook_library._build_output(settings, {})
    assert out.get_editor_property("has_name") is True
    assert out.get_editor_property("has_description") is None
    assert out.get_editor_property("has_priority") is None


def test_build_output_routes_unknown_deadline_key_to_unapplied(pre_gui_hook_library):
    settings = SimpleNamespace(name=None, description=None)
    out = pre_gui_hook_library._build_output(settings, {"deadline:someUnknownSetting": "x"})
    assert out.get_editor_property("ran") is True
    assert out.get_editor_property("unapplied_keys") == ["deadline:someUnknownSetting"]


def test_build_output_routes_plain_key_to_template_parameter(pre_gui_hook_library):
    settings = SimpleNamespace(name=None, description=None)
    out = pre_gui_hook_library._build_output(settings, {"MyTemplateParam": "v"})
    params = out.get_editor_property("parameters")
    assert params is not None
    assert len(params) == 1


def test_build_output_routes_submitter_managed_param_to_unapplied(pre_gui_hook_library):
    # A submitter-managed parameter (resolved from the machine at submit time) must NOT be baked onto the
    # job by a hook — it is routed to unapplied_keys instead of becoming a template parameter, so it cannot
    # clobber the machine-resolved value (#8). A non-managed param alongside it still becomes a template
    # parameter.
    settings = SimpleNamespace(name=None, description=None)
    out = pre_gui_hook_library._build_output(
        settings,
        {"ProjectFilePath": "C:/stale/wrong.uproject", "MyTemplateParam": "v"},
    )
    assert "ProjectFilePath" in list(out.get_editor_property("unapplied_keys"))
    params = out.get_editor_property("parameters")
    assert params is not None and len(params) == 1  # only MyTemplateParam became a template param


def test_build_output_routes_dynamic_chunking_and_conda_params_to_unapplied(pre_gui_hook_library):
    # Frames / TargetRuntimeSeconds / RangeConstraint (dynamic chunking) and CondaPackages are resolved by
    # the submitter at submit time (from the MRQ playback range / UE version) via a fill-if-unset builder;
    # a hook value would make that builder short-circuit and bake a stale one — e.g. a hook-set Frames
    # suppresses the computed MRQ range and renders whatever the hook guessed. They must route to
    # unapplied_keys, not become template parameters. Regression guard that the frozenset stays in sync
    # with the job-level auto-resolved names in OpenJobParameterNames.
    for managed in ("Frames", "TargetRuntimeSeconds", "RangeConstraint", "CondaPackages"):
        assert managed in pre_gui_hook_library._SUBMITTER_MANAGED_PARAMETER_NAMES
        settings = SimpleNamespace(name=None, description=None)
        out = pre_gui_hook_library._build_output(settings, {managed: "1-100"})
        assert managed in list(out.get_editor_property("unapplied_keys")), managed
        params = out.get_editor_property("parameters")
        assert params is None or all(
            p.get_editor_property("name") != managed for p in params
        ), managed
