# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Generate Deadline Cloud job bundles for MRQ job template updates inside Unreal Engine.

This script is executed via UE's -ExecutePythonScript flag with -unattended. For each case
it saves job parameters against an older job template, updates the template YAML in place
and then builds a bundle with RenderUnrealOpenJob.from_mrq_job(...).create_job_bundle():

    - changed_apply_a/b: two MRQ jobs share one preset; direct
      ReconcileJobTemplateParameters(apply=True) simulates "Yes" on the update prompt
    - changed_decline: no apply simulates "No"; existing consistency validation must fail
    - added_only_decline: no apply; only a new parameter was added, so its YAML default is used
    - default_only: only a template default changed, so nothing is reconciled

No Deadline Cloud API calls are made. Bundles are moved out of the job history into the
artifacts directory, and the results are written to a JSON marker file.

Environment variables:
    DEADLINE_CLOUD_INTEG_MARKER_FILE - path of the JSON marker file to write.
    DEADLINE_CLOUD_INTEG_WORK_DIR - directory for temporary job template YAML files.
    DEADLINE_CLOUD_INTEG_ARTIFACTS_DIR - directory to move generated bundles into.
"""

import copy
import importlib
import json
import os
import re
import shutil
import traceback
from pathlib import Path
from typing import Any

import unreal
import yaml

PLUGIN_VERSION = "integ-template-updates"

ARTIST = "ArtistParam"
RETYPED = "RetypedParam"
LEGACY = "LegacyParam"
IGNORE_PLUGINS = "IgnorePlugins"
CONDA_PACKAGES = "CondaPackages"

DEFAULT_PRESET = "/UnrealDeadlineCloudService/OpenJD_DataAssets/Default/OpenJD_Default_RenderJob"
ASSET_DIR = "/Game/DeadlineIntegTemplateUpdates"

PRESET_VALUES = {ARTIST: "preset-value", RETYPED: "preset-string", LEGACY: "preset-legacy"}


def _parameter(name: str, type_: str, default: Any) -> dict:
    # OpenJD allows LINE_EDIT only for STRING; INT uses SPIN_BOX
    control = "SPIN_BOX" if type_ == "INT" else "LINE_EDIT"
    return {"name": name, "type": type_, "default": default, "userInterface": {"control": control}}


def build_template_variants(stock: dict, ue_version: str) -> dict:
    """
    Return {variant: (saved_template, current_template)} derived from the stock render job template.

    :param stock: Stock render_job.yml content
    :param ue_version: Current Unreal Engine version in x.y format
    """
    stock_parameters = stock["parameterDefinitions"]
    for name in (IGNORE_PLUGINS, CONDA_PACKAGES):
        if not any(p["name"] == name for p in stock_parameters):
            raise ValueError(f"Stock render job template has no {name} parameter")

    def template(parameters: list) -> dict:
        result = copy.deepcopy(stock)
        result["parameterDefinitions"] = copy.deepcopy(parameters)
        return result

    def without(parameters: list, *names: str) -> list:
        return [p for p in parameters if p["name"] not in names]

    # Saved Conda values must match this engine, or bundle creation opens a version dialog
    normalized = copy.deepcopy(stock_parameters)
    for p in normalized:
        if p["name"] == CONDA_PACKAGES:
            p["default"] = re.sub(
                r"unrealengine=\d+\.\d+", f"unrealengine={ue_version}", p["default"]
            )

    current = stock_parameters + [
        _parameter(ARTIST, "STRING", "template-default"),
        _parameter(RETYPED, "INT", 5),
    ]
    current_normalized = without(current, CONDA_PACKAGES) + [
        p for p in normalized if p["name"] == CONDA_PACKAGES
    ]
    changed_saved = without(current, IGNORE_PLUGINS, CONDA_PACKAGES, RETYPED) + [
        _parameter(RETYPED, "STRING", "old-string"),
        _parameter(LEGACY, "STRING", "legacy-default"),
    ]
    default_only_current = copy.deepcopy(current_normalized)
    for p in default_only_current:
        if p["name"] == ARTIST:
            p["default"] = "template-default-new"

    return {
        "changed": (template(changed_saved), template(current)),
        "added_only": (
            template(without(current_normalized, IGNORE_PLUGINS)),
            template(current_normalized),
        ),
        "default_only": (template(current_normalized), template(default_only_current)),
    }


def _enum_name(value) -> str:
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name
    return str(value).split(".")[-1].split(":")[0].strip("<> ")


def _snapshot(parameters) -> list:
    return [
        {
            "name": p.name,
            "type": _enum_name(p.type),
            "value": p.value,
            "control": _enum_name(p.user_interface_control),
        }
        for p in parameters
    ]


def _state(job) -> dict:
    return {
        "job": _snapshot(job.get_editor_property("job_template_overrides").parameters),
        "preset": _snapshot(job.job_preset.get_job_parameters()),
    }


def _write_yaml(path: Path, data: dict) -> str:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    return path.as_posix()


def _yaml_library():
    """Return the PythonYamlLibrary implementation the C++ code uses."""
    return unreal.get_default_object(
        importlib.import_module("open_job_template_api").PythonYamlLibraryImplementation
    )


def _read_template(path: str) -> list:
    """Read job parameters with the same ReadJobFile implementation the C++ check uses."""
    result = _yaml_library().read_job_file(path)
    if not result.succeeded:
        raise RuntimeError(f"ReadJobFile failed for {path}")
    return list(result.parameters)


def _render_inputs():
    """Return (level sequence, editor world) for valid MRQ jobs."""
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    sequences = [
        a
        for a in registry.get_assets_by_class(
            unreal.TopLevelAssetPath("/Script/LevelSequence", "LevelSequence"), True
        )
        if str(a.package_name).startswith("/Game/")
    ]
    if sequences:
        sequence = min(sequences, key=lambda a: str(a.package_name).count("/")).get_asset()
    else:
        sequence = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "TemplateUpdateSequence",
            ASSET_DIR,
            unreal.LevelSequence,
            unreal.LevelSequenceFactoryNew(),
        )
        sequence.set_playback_start(0)
        sequence.set_playback_end(24)
        unreal.EditorAssetLibrary.save_loaded_asset(sequence)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not sequence or not world:
        raise RuntimeError("No level sequence or editor world available for MRQ jobs")
    return sequence, world


def _new_job(queue, name: str, sequence, world):
    job = queue.allocate_new_job(unreal.MoviePipelineDeadlineCloudExecutorJob)
    job.job_name = name
    job.map = unreal.SoftObjectPath(world.get_path_name())
    job.sequence = unreal.SoftObjectPath(sequence.get_path_name())
    unreal.MoviePipelineEditorLibrary.ensure_job_has_default_settings(job)
    unreal.MoviePipelineLibrary.update_job_shot_list_from_sequence(sequence, job)
    return job


def _own_asset(asset, name: str):
    """Duplicate a referenced plugin asset and point it at the current plugin template."""
    from deadline.unreal_submitter import settings

    template_path = os.path.join(
        settings.OPENJD_TEMPLATES_DIRECTORY, os.path.basename(asset.path_to_template.file_path)
    ).replace("\\", "/")
    owned = unreal.EditorAssetLibrary.duplicate_loaded_asset(asset, f"{ASSET_DIR}/{name}")
    if not owned or not os.path.isfile(template_path):
        raise RuntimeError(f"Could not create {name} for template {template_path}")
    owned.set_editor_property("path_to_template", unreal.FilePath(file_path=template_path))
    return owned, template_path


def _own_environment(environment, name: str):
    """Test-owned environment initialized from its current YAML, like OpenEnvFile."""
    owned, template_path = _own_asset(environment, name)
    variables = owned.get_editor_property("variables")
    variables.set_editor_property(
        "variables",
        {v.name: v.value for v in _yaml_library().open_env_file(template_path).variables},
    )
    owned.set_editor_property("variables", variables)
    return owned


def _own_step(step, name: str):
    """Test-owned step initialized from its current YAML, like OpenStepFile."""
    owned, template_path = _own_asset(step, name)
    owned.set_step_parameters(list(_yaml_library().open_step_file(template_path).parameters))
    owned.set_editor_property(
        "environments",
        [_own_environment(e, f"{name}_Env{i}") for i, e in enumerate(step.environments) if e],
    )
    if step.host_requirements:
        host_requirements, host_path = _own_asset(step.host_requirements, f"{name}_HostReq")
        host_requirements.open_host_requirements_file(host_path)
        owned.set_editor_property("host_requirements", host_requirements)
    return owned


def _test_preset(name: str, template_path: str):
    """
    Return a test-owned copy of the plugin default preset saved against the given job template.
    Its steps and environments are test-owned too and match the current plugin YAML;
    the preset keeps the plugin asset's hidden parameter state.
    """
    preset = unreal.EditorAssetLibrary.duplicate_asset(DEFAULT_PRESET, f"{ASSET_DIR}/{name}_Preset")
    if not preset:
        raise RuntimeError(f"Could not duplicate default preset for {name}")
    preset.set_editor_property(
        "steps", [_own_step(s, f"{name}_Step{i}") for i, s in enumerate(preset.steps) if s]
    )
    preset.set_editor_property(
        "environments",
        [_own_environment(e, f"{name}_Env{i}") for i, e in enumerate(preset.environments) if e],
    )
    preset.set_editor_property("path_to_template", unreal.FilePath(file_path=template_path))
    parameters = _read_template(template_path)
    for p in parameters:
        if p.name in PRESET_VALUES and _enum_name(p.type) == "STRING":
            p.value = PRESET_VALUES[p.name]
    preset.set_job_parameters(parameters)
    unreal.EditorAssetLibrary.save_directory(ASSET_DIR, only_if_is_dirty=True, recursive=True)
    return preset


def _save_job_values(job, preset, values: dict) -> None:
    """
    Assign the preset like the Details panel does, so JobPresetChanged stores the preset's
    visible parameters (hidden-items state) as overrides, then store raw saved artist values.
    """
    job.set_editor_property("job_preset", preset)
    overrides = job.get_editor_property("job_template_overrides")
    parameters = list(overrides.parameters)
    if job.job_preset != preset or ARTIST not in [p.name for p in parameters]:
        raise RuntimeError("Assigning the preset did not reload the MRQ job overrides")
    for p in parameters:
        if p.name == "FramesPerTask":
            p.value = "12"  # Use real sequence frames even when the template has no camera cuts.
        if p.name in values:
            p.value = values[p.name]
    overrides.parameters = parameters
    job.set_editor_property("job_template_overrides", overrides)


def _create_bundle(job, name: str, artifacts_dir: Path) -> dict:
    from deadline.unreal_submitter.unreal_open_job.unreal_open_job import RenderUnrealOpenJob

    try:
        bundle_path = RenderUnrealOpenJob.from_mrq_job(job).create_job_bundle()
    except Exception as e:
        unreal.log_warning(f"generate_template_update_bundles: {name} bundle failed - {e}")
        return {"path": None, "error_type": type(e).__name__, "error": str(e)}
    # Keep job history clean: test_openjd_run uses its newest template
    destination = artifacts_dir / name
    shutil.rmtree(destination, ignore_errors=True)
    shutil.move(bundle_path, destination)
    return {"path": str(destination), "error_type": None, "error": None}


def _prepare_case(work_dir: Path, name: str, variant: tuple, render_inputs, job_values: dict):
    """Create jobs sharing one preset saved against the old template, then update the YAML."""
    saved_template, current_template = variant
    template_path = _write_yaml(work_dir / f"{name}.yml", saved_template)
    queue = unreal.MoviePipelineQueue()
    jobs = {job_name: _new_job(queue, job_name, *render_inputs) for job_name in job_values}
    preset = _test_preset(name, template_path)
    for job_name, job in jobs.items():
        _save_job_values(job, preset, job_values[job_name])
    records = {job_name: {"saved": _state(job), "results": {}} for job_name, job in jobs.items()}
    _write_yaml(Path(template_path), current_template)
    return queue, jobs, records, _read_template(template_path)


def _check_and_preview(queue, jobs: dict, records: dict, current: list) -> None:
    """Run the unattended queue check (no modal), then a preview, recording state after each."""
    check = unreal.MoviePipelineDeadlineCloudExecutorJob.check_for_template_updates(
        queue, PLUGIN_VERSION, True
    )
    for job_name, job in jobs.items():
        records[job_name]["results"]["unattended_check"] = check
        records[job_name]["after_check"] = _state(job)
    for job_name, job in jobs.items():
        records[job_name]["results"]["preview"] = job.reconcile_job_template_parameters(
            current, False
        )
        records[job_name]["after_preview"] = _state(job)


def run_cases(work_dir: Path, artifacts_dir: Path) -> dict:
    from deadline.unreal_submitter import settings
    from deadline.unreal_submitter.unreal_open_job.unreal_open_job import UnrealOpenJob

    # Register the Python implementations used by the C++ job if init_unreal has not run yet
    for module in ("job_library", "open_job_template_api"):
        importlib.import_module(module)

    ue_version = UnrealOpenJob.get_current_ue_version()
    with open(os.path.join(settings.OPENJD_TEMPLATES_DIRECTORY, "render_job.yml")) as f:
        variants = build_template_variants(yaml.safe_load(f), ue_version)
    render_inputs = _render_inputs()
    cases: dict = {}

    # "Yes": direct apply on both jobs that share one preset
    queue, jobs, records, current = _prepare_case(
        work_dir,
        "changed_apply",
        variants["changed"],
        render_inputs,
        {
            "changed_apply_a": {ARTIST: "artist-a", RETYPED: "artist-string", LEGACY: "artist-a"},
            "changed_apply_b": {ARTIST: "artist-b", RETYPED: "artist-string", LEGACY: "artist-b"},
        },
    )
    _check_and_preview(queue, jobs, records, current)
    job_a, job_b = jobs["changed_apply_a"], jobs["changed_apply_b"]
    records["changed_apply_a"]["results"]["apply"] = job_a.reconcile_job_template_parameters(
        current, True
    )
    # The shared preset is updated now, but job B still holds stale overrides
    records["changed_apply_b"]["results"]["preview_after_shared_apply"] = (
        job_b.reconcile_job_template_parameters(current, False)
    )
    records["changed_apply_b"]["results"]["apply"] = job_b.reconcile_job_template_parameters(
        current, True
    )
    for job_name, job in jobs.items():
        records[job_name]["results"]["preview_after_apply"] = job.reconcile_job_template_parameters(
            current, False
        )
        records[job_name]["after_apply"] = _state(job)
        records[job_name]["bundle"] = _create_bundle(job, job_name, artifacts_dir)
    cases.update(records)

    # "No" and unchanged definitions: leave saved data as is and submit
    for name, variant, values in (
        ("changed_decline", "changed", {ARTIST: "artist-decline", RETYPED: "x", LEGACY: "x"}),
        ("added_only_decline", "added_only", {ARTIST: "artist-added"}),
        ("default_only", "default_only", {ARTIST: "artist-default-only"}),
    ):
        queue, jobs, records, current = _prepare_case(
            work_dir, name, variants[variant], render_inputs, {name: values}
        )
        _check_and_preview(queue, jobs, records, current)
        records[name]["bundle"] = _create_bundle(jobs[name], name, artifacts_dir)
        cases.update(records)

    return {"ue_version": ue_version, "plugin_version": PLUGIN_VERSION, "cases": cases}


def main():
    marker_file = os.environ.get("DEADLINE_CLOUD_INTEG_MARKER_FILE", "")
    if not marker_file:
        unreal.log_error("generate_template_update_bundles: marker env var is not set.")
        unreal.SystemLibrary.quit_editor()
        return

    # Ensure OPENJD_TEMPLATES_DIRECTORY is set before importing deadline modules
    # (init_unreal.py normally does this, but -ExecutePythonScript may run first).
    if "OPENJD_TEMPLATES_DIRECTORY" not in os.environ:
        os.environ["OPENJD_TEMPLATES_DIRECTORY"] = str(
            Path(unreal.Paths.project_plugins_dir()).joinpath(
                "UnrealDeadlineCloudService", "Content", "Python", "openjd_templates"
            )
        )

    marker: dict = {"status": "error"}
    try:
        work_dir = Path(os.environ["DEADLINE_CLOUD_INTEG_WORK_DIR"])
        artifacts_dir = Path(os.environ["DEADLINE_CLOUD_INTEG_ARTIFACTS_DIR"])
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        marker.update(run_cases(work_dir, artifacts_dir))
        marker["status"] = "ok"
    except Exception as e:
        unreal.log_error(f"generate_template_update_bundles: Failed - {e}")
        unreal.log_error(traceback.format_exc())
        marker.update(error=str(e), traceback=traceback.format_exc())

    try:
        with open(marker_file, "w", encoding="utf-8") as f:
            json.dump(marker, f, indent=2)
    except Exception as e:
        unreal.log_error(f"generate_template_update_bundles: Failed to write marker: {e}")

    unreal.SystemLibrary.quit_editor()


if __name__ == "__main__":
    main()
