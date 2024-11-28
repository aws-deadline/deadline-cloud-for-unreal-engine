import os

from deadline.unreal_submitter import settings
from deadline.unreal_submitter.submitter import (
    UnrealOpenJobSubmitter,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (
    UnrealOpenJob,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
    UnrealOpenJobStep,
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


def main(script_path: str):
    custom_open_job = UnrealOpenJob(
        name="CustomJobFromPython",
        file_path=f"{settings.OPENJD_TEMPLATES_DIRECTORY}/custom/custom_job.yml",
        steps=[
            UnrealOpenJobStep(
                name="CustomStepFromPython",
                file_path=f"{settings.OPENJD_TEMPLATES_DIRECTORY}/custom/custom_step.yml",
                extra_parameters=[
                    UnrealOpenJobStepParameterDefinition("ScriptPath", "PATH", [script_path])
                ],
            ),
        ],
        environments=[LaunchEditorUnrealOpenJobEnvironment()]
    )

    submitter = UnrealOpenJobSubmitter()
    submitter.add_job(custom_open_job)

    submitted_job_ids = submitter.submit_jobs()
    for job_id in submitted_job_ids:
        logger.info(f"Job submitted: {job_id}")
