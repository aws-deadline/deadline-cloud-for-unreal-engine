import os
import unreal

from deadline.unreal_submitter.submitter import (
    UnrealRenderOpenJobSubmitter,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (
    RenderUnrealOpenJob,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
    RenderUnrealOpenJobStep,
    UnrealOpenJobStepParameterDefinition,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (
    LaunchEditorUnrealOpenJobEnvironment,
)
from deadline.unreal_logger import get_logger


logger = get_logger()


if "OPENJD_TEMPLATES_DIRECTORY" not in os.environ:
    os.environ["OPENJD_TEMPLATES_DIRECTORY"] = (
        f"{os.path.dirname(os.path.dirname(__file__))}"
        f"/src/unreal_plugin/Content/Python/openjd_templates"
    )


def main():
    render_job_submitter = UnrealRenderOpenJobSubmitter(silent_mode=True)

    # Get jobs from Render Queue or you can create your own
    queue = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem).get_queue()
    for job in queue.get_jobs():
        default_render_job = RenderUnrealOpenJob(
            steps=[
                RenderUnrealOpenJobStep(
                    extra_parameters=[
                        UnrealOpenJobStepParameterDefinition("ChunkSize", "INT", [10])
                    ]
                )
            ],
            environments=[LaunchEditorUnrealOpenJobEnvironment()],
            mrq_job=job,
        )

        render_job_submitter.add_job(default_render_job)

    submitted_job_ids = render_job_submitter.submit_jobs()
    for job_id in submitted_job_ids:
        logger.info(f"Job submitted: {job_id}")


if __name__ == "__main__":
    main()
