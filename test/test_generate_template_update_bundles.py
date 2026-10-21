# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml


def test_template_update_fixtures_validate_with_openjd():
    from openjd.model import decode_job_template
    from openjd.model.v2023_09 import ExtensionName

    root = Path(__file__).parents[1]
    spec = importlib.util.spec_from_file_location(
        "generate_template_update_bundles", root / "pipeline/generate_template_update_bundles.py"
    )
    assert spec and spec.loader
    script = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"unreal": MagicMock()}):
        spec.loader.exec_module(script)
    stock = yaml.safe_load(
        (root / "src/unreal_plugin/Content/Python/openjd_templates/render_job.yml").read_text()
    )
    # Render jobs get their steps from step assets; supply one for schema validation.
    step = {"name": "Test", "script": {"actions": {"onRun": {"command": "echo"}}}}
    for saved, current in script.build_template_variants(stock, "5.8").values():
        for template in (saved, current):
            decode_job_template(
                template={**template, "steps": [step]},
                supported_extensions=[e.value for e in ExtensionName],
            )
