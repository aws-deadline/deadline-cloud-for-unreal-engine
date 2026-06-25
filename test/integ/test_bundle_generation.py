# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import yaml


def test_bundle_generation(build_plugin, create_test_project, run_unreal_bundle_only):
    """Launch UE headless, generate job bundle via ExecutePythonScript, validate YAML."""
    bundle_path = run_unreal_bundle_only

    assert bundle_path.exists(), f"Bundle path does not exist: {bundle_path}"

    template_file = bundle_path / "template.yaml"
    params_file = bundle_path / "parameter_values.yaml"
    assets_file = bundle_path / "asset_references.yaml"

    assert template_file.exists(), "template.yaml not found in bundle"
    assert params_file.exists(), "parameter_values.yaml not found in bundle"
    assert assets_file.exists(), "asset_references.yaml not found in bundle"

    # Validate template structure
    template = yaml.safe_load(template_file.read_text())
    assert template.get("specificationVersion") == "jobtemplate-2023-09"
    assert "name" in template
    assert "steps" in template
    assert len(template["steps"]) > 0

    # Validate each step has required fields
    for step in template["steps"]:
        assert "name" in step
        assert "script" in step or "parameterSpace" in step or "stepEnvironments" in step

    # Validate parameter values
    params = yaml.safe_load(params_file.read_text())
    assert "parameterValues" in params

    # Validate template is a valid OpenJD job template
    from openjd.model import decode_job_template
    from openjd.model._errors import DecodeValidationError

    try:
        decode_job_template(template=template)
    except DecodeValidationError as e:
        if "Unsupported extension" not in str(e):
            raise
