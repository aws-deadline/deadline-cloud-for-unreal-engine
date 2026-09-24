# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Generate a one-frame Perforce render job bundle inside Unreal Engine."""

import os
import traceback
from pathlib import Path

import unreal

MAP_PATH = "/Game/DMXTemplate/Maps/Fixtures.Fixtures"
SEQUENCE_PATH = "/Game/DMXTemplate/Sequences/LS_FixtureDemo.LS_FixtureDemo"

# -ExecutePythonScript can run before the plugin's init_unreal.py.
if "OPENJD_TEMPLATES_DIRECTORY" not in os.environ:
    plugin_python_dir = Path(unreal.Paths.engine_plugins_dir()).joinpath(
        "UnrealDeadlineCloudService", "Content", "Python"
    )
    os.environ["OPENJD_TEMPLATES_DIRECTORY"] = str(plugin_python_dir / "openjd_templates")

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (  # noqa: E402
    P4RenderUnrealOpenJob,
    UnrealOpenJobParameterDefinition,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (  # noqa: E402
    P4LaunchEditorUnrealOpenJobEnvironment,
    P4SyncCmfUnrealOpenJobEnvironment,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (  # noqa: E402
    P4RenderUnrealOpenJobStep,
)


def _create_mrq_job(run_id: str):
    for asset_path in (MAP_PATH, SEQUENCE_PATH):
        if unreal.EditorAssetLibrary.load_asset(asset_path) is None:
            raise RuntimeError(f"Unable to load asset: {asset_path}")

    queue = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem).get_queue()
    queue.delete_all_jobs()

    mrq_job = queue.allocate_new_job(unreal.MoviePipelineDeadlineCloudExecutorJob)

    mrq_job.job_name = f"PerforceE2E-{run_id}"
    mrq_job.map = unreal.SoftObjectPath(MAP_PATH)
    mrq_job.sequence = unreal.SoftObjectPath(SEQUENCE_PATH)

    configuration = mrq_job.get_configuration()
    output_setting = configuration.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    output_setting.use_custom_playback_range = True
    output_setting.custom_start_frame = 0
    output_setting.custom_end_frame = 1
    output_setting.file_name_format = "{sequence_name}.{frame_number}"

    output_directory = unreal.DirectoryPath()
    output_directory.set_editor_property(
        "path",
        str(
            Path(unreal.SystemLibrary.get_project_saved_directory()) / "MovieRenders" / run_id
        ).replace("\\", "/"),
    )
    output_setting.output_directory = output_directory

    configuration.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    configuration.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
    return mrq_job


def main() -> None:
    marker = os.environ.get("DEADLINE_CLOUD_INTEG_MARKER_FILE")
    if not marker:
        unreal.log_error("generate_perforce_bundle: DEADLINE_CLOUD_INTEG_MARKER_FILE is not set.")
        unreal.SystemLibrary.quit_editor()
        return
    marker_path = Path(marker)

    try:
        run_id = os.environ.get("DEADLINE_P4_E2E_RUN_ID", "PerforceE2E")
        ue_version = os.environ.get("DEADLINE_P4_E2E_UE_VERSION")
        if not ue_version:
            raise RuntimeError("DEADLINE_P4_E2E_UE_VERSION is not set")
        worker_root = os.environ.get(
            "DEADLINE_P4_TEST_WORKER_ROOT", "C:/deadline/perforce-workers"
        ).replace("\\", "/")

        mrq_job = _create_mrq_job(run_id)
        render_step = P4RenderUnrealOpenJobStep()
        open_job = P4RenderUnrealOpenJob(
            name=f"PerforceE2E-{run_id}",
            extra_parameters=[
                UnrealOpenJobParameterDefinition(name="SubmitMode", type="STRING", value="submit"),
                UnrealOpenJobParameterDefinition(
                    name="CondaPackages",
                    type="STRING",
                    value=f"unrealengine={ue_version} unrealengine-openjd=0.7.*",
                ),
                UnrealOpenJobParameterDefinition(name="FramesPerTask", type="INT", value=1),
            ],
            steps=[render_step],
            environments=[
                P4SyncCmfUnrealOpenJobEnvironment(
                    variables={
                        "P4_CLIENTS_ROOT_DIRECTORY": worker_root,
                        "AWS_SECRET_P4INFO": "",
                    }
                ),
                P4LaunchEditorUnrealOpenJobEnvironment(),
            ],
            mrq_job=mrq_job,
        )
        render_step.open_job = open_job

        bundle_path = open_job.create_job_bundle()
        marker_path.write_text(bundle_path, encoding="utf-8")
        unreal.log(f"generate_perforce_bundle: Bundle created at {bundle_path}")
    except Exception as error:
        unreal.log_error(f"generate_perforce_bundle: Failed - {error}")
        unreal.log_error(traceback.format_exc())
        try:
            marker_path.write_text(f"ERROR: {error}", encoding="utf-8")
        except Exception as marker_error:
            unreal.log_error(f"generate_perforce_bundle: Failed to write marker: {marker_error}")
    finally:
        unreal.SystemLibrary.quit_editor()


if __name__ == "__main__":
    main()
