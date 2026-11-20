# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import importlib
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

_SETTINGS_DIR = os.path.join(os.path.dirname(__file__), "../../../src/unreal_plugin/Content/Python")


class _FakeUnrealModule(types.ModuleType):
    """``unreal`` with real classes where settings.py needs them, and mocks elsewhere."""

    def __getattr__(self, name: str) -> MagicMock:
        value = MagicMock(name=f"unreal.{name}")
        setattr(self, name, value)
        return value


class _AwsEntity:
    def __init__(self) -> None:
        self.id = ""
        self.name = ""


@pytest.fixture
def settings_module():
    """Import settings.py against a minimal fake ``unreal`` module."""
    fake_unreal = _FakeUnrealModule("unreal")
    fake_unreal.UnrealAwsEntity = _AwsEntity  # type: ignore[attr-defined]
    fake_unreal.DeadlineCloudSettingsLibrary = type(  # type: ignore[attr-defined]
        "DeadlineCloudSettingsLibrary", (), {}
    )
    fake_unreal.uclass = lambda *a, **k: (lambda cls: cls)  # type: ignore[attr-defined]
    fake_unreal.ufunction = lambda *a, **k: (lambda fn: fn)  # type: ignore[attr-defined]
    with patch.dict(sys.modules, {"unreal": fake_unreal}):
        sys.path.insert(0, _SETTINGS_DIR)
        try:
            sys.modules.pop("settings", None)
            module = importlib.import_module("settings")
            yield module
        finally:
            sys.path.remove(_SETTINGS_DIR)
            sys.modules.pop("settings", None)


def test_get_farms_keeps_farms_without_display_name(settings_module):
    """Farms reached only through a queue or fleet membership come back without a name."""
    farms = [
        {"farmId": "farm-1", "displayName": "Render Farm", "region": "us-west-2"},
        {"farmId": "farm-2", "region": "us-west-2"},
    ]
    library = settings_module.DeadlineCloudSettingsLibraryImplementation.__new__(
        settings_module.DeadlineCloudSettingsLibraryImplementation
    )
    with patch.object(settings_module.api, "list_farms", MagicMock(return_value={"farms": farms})):
        result = library.get_farms()
    assert [(e.id, e.name) for e in result] == [
        ("farm-1", "Render Farm"),
        ("farm-2", "farm-2"),
    ]
