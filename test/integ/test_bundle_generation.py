# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path

import pytest
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


ARTIST = "ArtistParam"
RETYPED = "RetypedParam"
LEGACY = "LegacyParam"
IGNORE_PLUGINS = "IgnorePlugins"
CONDA_PACKAGES = "CondaPackages"


def _by_name(parameters):
    return {p["name"]: p for p in parameters}


def _load_bundle(case):
    """Load a generated bundle and validate it with OpenJD."""
    from openjd.model import decode_job_template
    from openjd.model.v2023_09 import ExtensionName

    bundle = case["bundle"]
    assert bundle["error_type"] is None, f"Bundle creation failed: {bundle}"
    bundle_path = Path(bundle["path"])
    template = yaml.safe_load((bundle_path / "template.yaml").read_text())
    values = yaml.safe_load((bundle_path / "parameter_values.yaml").read_text())["parameterValues"]
    assert (bundle_path / "asset_references.yaml").exists()

    decode_job_template(template=template, supported_extensions=[e.value for e in ExtensionName])

    definitions = _by_name(template["parameterDefinitions"])
    values_by_name = {v["name"]: v["value"] for v in values}
    for name, value in values_by_name.items():
        if name.startswith("deadline:"):
            continue
        assert name in definitions, f"Value for undefined parameter {name}"
        definition = definitions[name]
        if definition["type"] == "INT":
            int(value)
        if "allowedValues" in definition:
            assert str(value) in [str(v) for v in definition["allowedValues"]]
    return definitions, values_by_name


def _assert_saved_state_preserved(case):
    assert case["after_check"] == case["saved"], "Unattended check changed saved parameters"
    assert case["after_preview"] == case["saved"], "Preview changed saved parameters"


@pytest.mark.parametrize("job_name, artist_value", [("a", "artist-a"), ("b", "artist-b")])
def test_template_update_apply_updates_job_and_shared_preset(
    run_template_update_bundles, job_name, artist_value
):
    """Yes: direct apply updates each MRQ job and the shared preset, then the bundle builds."""
    case = run_template_update_bundles["cases"][f"changed_apply_{job_name}"]
    ue_version = run_template_update_bundles["ue_version"]
    results = case["results"]

    assert results["unattended_check"] is False, "Unattended check must not apply updates"
    _assert_saved_state_preserved(case)
    assert results["preview"] is True
    assert results["apply"] is True
    assert results["preview_after_apply"] is False, "Apply must be idempotent"
    if job_name == "b":
        assert results["preview_after_shared_apply"] is True

    job = _by_name(case["after_apply"]["job"])
    assert LEGACY not in job
    assert job[ARTIST]["value"] == artist_value
    assert job[RETYPED]["type"] == "INT" and job[RETYPED]["value"] == "5"
    assert job[IGNORE_PLUGINS]["value"] == "false"
    assert job[IGNORE_PLUGINS]["control"] == "DROPDOWN_LIST"
    assert f"unrealengine={ue_version}" in job[CONDA_PACKAGES]["value"]

    preset = _by_name(case["after_apply"]["preset"])
    assert LEGACY not in preset
    assert preset[ARTIST]["value"] == "preset-value"
    assert preset[RETYPED]["type"] == "INT" and preset[RETYPED]["value"] == "5"
    assert IGNORE_PLUGINS in preset and CONDA_PACKAGES in preset

    definitions, values = _load_bundle(case)
    assert LEGACY not in definitions and LEGACY not in values
    assert definitions[RETYPED]["type"] == "INT"
    assert IGNORE_PLUGINS in definitions and CONDA_PACKAGES in definitions
    assert values[ARTIST] == artist_value
    assert str(values[RETYPED]) == "5"
    assert values[IGNORE_PLUGINS] == "false"
    assert f"unrealengine={ue_version}" in values[CONDA_PACKAGES]


def test_template_update_decline_keeps_existing_consistency_failure(run_template_update_bundles):
    """No: saved parameters are kept and existing validation rejects removed/retyped ones."""
    case = run_template_update_bundles["cases"]["changed_decline"]

    assert case["results"]["unattended_check"] is False
    assert case["results"]["preview"] is True
    _assert_saved_state_preserved(case)
    assert _by_name(case["saved"]["job"])[ARTIST]["value"] == "artist-decline"

    bundle = case["bundle"]
    assert bundle["path"] is None
    assert bundle["error_type"] == "ParametersAreNotConsistentError"
    assert LEGACY in bundle["error"] and RETYPED in bundle["error"]


def test_template_update_decline_added_only_uses_yaml_default(run_template_update_bundles):
    """No with only an added parameter: submission still works using the YAML default."""
    case = run_template_update_bundles["cases"]["added_only_decline"]

    assert case["results"]["unattended_check"] is False
    assert case["results"]["preview"] is True
    _assert_saved_state_preserved(case)
    assert IGNORE_PLUGINS not in _by_name(case["saved"]["preset"])

    definitions, values = _load_bundle(case)
    assert IGNORE_PLUGINS in definitions
    assert values[IGNORE_PLUGINS] == "false"
    assert values[ARTIST] == "artist-added"


def test_template_update_default_only_preserves_artist_value(run_template_update_bundles):
    """Matching definitions with a changed default are not a migration and keep artist values."""
    case = run_template_update_bundles["cases"]["default_only"]

    assert case["results"]["unattended_check"] is True
    assert case["results"]["preview"] is False
    _assert_saved_state_preserved(case)

    _, values = _load_bundle(case)
    assert values[ARTIST] == "artist-default-only"
