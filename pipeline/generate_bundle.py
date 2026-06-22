# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Generate a Deadline Cloud job bundle inside Unreal Engine.

This script is executed via UE's -ExecutePythonScript flag. It creates a minimal
OpenJob bundle (template.yaml, parameter_values.yaml, asset_references.yaml)
without making any Deadline Cloud API calls. The resulting bundle path is written
to a marker file so the parent test process can locate it.

Environment variable required:
    DEADLINE_CLOUD_INTEG_MARKER_FILE - path to write the bundle directory path to.
"""

import os
import traceback

import unreal

from pathlib import Path

# Ensure OPENJD_TEMPLATES_DIRECTORY is set before importing deadline modules
# (init_unreal.py normally does this, but -ExecutePythonScript may run first).
if "OPENJD_TEMPLATES_DIRECTORY" not in os.environ:
    plugin_content_python = Path(unreal.Paths.project_plugins_dir()).joinpath(
        "UnrealDeadlineCloudService", "Content", "Python"
    )
    os.environ["OPENJD_TEMPLATES_DIRECTORY"] = str(plugin_content_python / "openjd_templates")

from deadline.unreal_submitter import settings
from deadline.unreal_submitter.unreal_open_job.unreal_open_job import UnrealOpenJob
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
    UnrealOpenJobStep,
    UnrealOpenJobStepParameterDefinition,
)


def main():
    marker_file = os.environ.get("DEADLINE_CLOUD_INTEG_MARKER_FILE", "")
    if not marker_file:
        unreal.log_error("generate_bundle: DEADLINE_CLOUD_INTEG_MARKER_FILE env var is not set.")
        unreal.SystemLibrary.quit_editor()
        return

    try:
        templates_dir = settings.OPENJD_TEMPLATES_DIRECTORY
        job_template = f"{templates_dir}/custom/custom_job.yml"
        step_template = f"{templates_dir}/custom/custom_step.yml"

        if not os.path.isfile(job_template):
            raise FileNotFoundError(f"Job template not found: {job_template}")
        if not os.path.isfile(step_template):
            raise FileNotFoundError(f"Step template not found: {step_template}")

        # Build a minimal OpenJob with one custom step.
        open_job = UnrealOpenJob(
            name="IntegTestBundle",
            file_path=job_template,
            steps=[
                UnrealOpenJobStep(
                    name="IntegTestStep",
                    file_path=step_template,
                    extra_parameters=[
                        UnrealOpenJobStepParameterDefinition(
                            "ScriptPath", "PATH", ["/tmp/placeholder.py"]
                        )
                    ],
                )
            ],
        )

        bundle_path = open_job.create_job_bundle()
        unreal.log(f"generate_bundle: Bundle created at {bundle_path}")

        # Write bundle path to marker file for the test harness to read.
        os.makedirs(os.path.dirname(marker_file), exist_ok=True)
        with open(marker_file, "w", encoding="utf-8") as f:
            f.write(bundle_path)

        unreal.log(f"generate_bundle: Marker written to {marker_file}")

    except Exception as e:
        unreal.log_error(f"generate_bundle: Failed - {e}")
        unreal.log_error(traceback.format_exc())
        # Write error to marker so test harness can report the failure.
        try:
            os.makedirs(os.path.dirname(marker_file), exist_ok=True)
            with open(marker_file, "w", encoding="utf-8") as f:
                f.write(f"ERROR: {e}")
        except Exception as write_err:
            unreal.log_error(f"generate_bundle: Failed to write marker file: {write_err}")

    unreal.SystemLibrary.quit_editor()


if __name__ == "__main__":
    main()
