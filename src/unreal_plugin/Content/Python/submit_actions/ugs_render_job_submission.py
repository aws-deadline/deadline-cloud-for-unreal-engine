# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os
import unreal

# Required imports
from deadline.unreal_submitter.submitter import (
    UnrealRenderOpenJobSubmitter,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (
    UgsRenderUnrealJob,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
    UgsRenderUnrealOpenJobStep,
    UnrealOpenJobStepParameterDefinition,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (
    UgsLaunchEditorUnrealOpenJobEnvironment,
    UgsSyncCmfUnrealOpenJobEnvironment,
)
from deadline.unreal_logger import get_logger


logger = get_logger()


# Add default location of predefined YAML templates to env to allow OpenJob entities
# load them without declaring full path to templates
if "OPENJD_TEMPLATES_DIRECTORY" not in os.environ:
    os.environ["OPENJD_TEMPLATES_DIRECTORY"] = (
        f"{os.path.dirname(os.path.dirname(__file__))}"
        f"/src/unreal_plugin/Content/Python/openjd_templates"
    )


def main():
    # Create Submitter for Render OpenJobs in silent mode (without UI notifications)
    render_job_submitter = UnrealRenderOpenJobSubmitter(silent_mode=True)

    # Get jobs from Render Queue or you can create your own
    queue = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem).get_queue()

    # From each MRQ job create Render Unreal OpenJob
    for job in queue.get_jobs():
        default_render_job = UgsRenderUnrealJob(
            # Set single Render step
            steps=[
                UgsRenderUnrealOpenJobStep(
                    extra_parameters=[
                        # Override ChunkSize parameter value
                        UnrealOpenJobStepParameterDefinition("ChunkSize", "INT", [10])
                    ]
                )
            ],
            # Set environments exactly in that order:
            # 1. Environment for syncing UGS workspace before render
            # 2. Environment for launch UE
            environments=[
                UgsSyncCmfUnrealOpenJobEnvironment(),
                UgsLaunchEditorUnrealOpenJobEnvironment(),
            ],
            # Set MRQ Job to retrieve render data and OpenJob overrides from
            mrq_job=job,
        )

        # Add Render Unreal OpenJob to submission queue
        render_job_submitter.add_job(default_render_job)

    # Sumit jobs and log their IDs
    submitted_job_ids = render_job_submitter.submit_jobs()
    for job_id in submitted_job_ids:
        logger.info(f"Job submitted: {job_id}")


if __name__ == "__main__":
    main()
