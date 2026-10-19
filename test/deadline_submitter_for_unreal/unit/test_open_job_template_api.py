# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


@pytest.mark.parametrize("contents", ["parameterDefinitions: [", "parameterDefinitions: [{}]"])
def test_failed_read_clears_previous_success(tmp_path, contents):
    unreal_mock = MagicMock()
    unreal_mock.uclass.return_value = lambda cls: cls
    unreal_mock.ufunction.return_value = lambda fn: fn
    unreal_mock.PythonYamlLibrary = type("PythonYamlLibrary", (), {})
    path = (
        Path(__file__).resolve().parents[3]
        / "src/unreal_plugin/Content/Python/open_job_template_api.py"
    )
    with patch.dict(sys.modules, {"unreal": unreal_mock}):
        spec = importlib.util.spec_from_file_location("open_job_template_api", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        library = module.PythonYamlLibraryImplementation()
        template = tmp_path / "job.yml"
        template.write_text(
            "parameterDefinitions:\n- name: Saved\n  type: STRING\n  default: value\n"
        )
        assert len(library.open_job_file(str(template))) == 1
        assert library.job_file_read_succeeded is True

        template.write_text(contents)
        with pytest.raises((yaml.YAMLError, KeyError)):
            library.open_job_file(str(template))
        assert library.job_file_read_succeeded is False
