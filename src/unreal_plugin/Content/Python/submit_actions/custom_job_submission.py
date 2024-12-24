# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os
import argparse

# Required imports
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


# Add default location of predefined YAML templates to env to allow OpenJob entities
# load them without declaring full path to templates
if "OPENJD_TEMPLATES_DIRECTORY" not in os.environ:
    os.environ["OPENJD_TEMPLATES_DIRECTORY"] = (
        f"{os.path.dirname(os.path.dirname(__file__))}"
        f"/src/unreal_plugin/Content/Python/openjd_templates"
    )


def main(script_path: str):
    # Create default Unreal OpenJob entity to customize it
    custom_open_job = UnrealOpenJob(
        # Set its custom name, will be taken from template otherwise
        name="CustomJobFromPython",
        # Since UnrealOpenJob has no default template, we need to pass it
        file_path=f"{settings.OPENJD_TEMPLATES_DIRECTORY}/custom/custom_job.yml",
        steps=[
            # Set single Custom Step
            UnrealOpenJobStep(
                # Set its custom name, will be taken from template otherwise
                name="CustomStepFromPython",
                # Since UnrealOpenJobStep has no default template, we need to pass it
                file_path=f"{settings.OPENJD_TEMPLATES_DIRECTORY}/custom/custom_step.yml",
                extra_parameters=[
                    # Override ScriptPath parameter value
                    UnrealOpenJobStepParameterDefinition("ScriptPath", "PATH", [script_path])
                ],
            ),
        ],
        # Set single Launch UE Environment
        environments=[LaunchEditorUnrealOpenJobEnvironment()],
    )

    # Create Submitter for OpenJobs in silent mode (without UI notifications)
    submitter = UnrealOpenJobSubmitter(silent_mode=True)

    # Add Custom Unreal OpenJob to submission queue
    submitter.add_job(custom_open_job)

    # Sumit jobs and log their IDs
    submitted_job_ids = submitter.submit_jobs()
    for job_id in submitted_job_ids:
        logger.info(f"Job submitted: {job_id}")


if __name__ == "__main__":
    logger.info("Executing test script")

    parser = argparse.ArgumentParser(description="Submits test script")
    parser.add_argument("--script_path", type=str, help="Python script path")

    arguments = parser.parse_args()

    main(arguments.script_path)
