import os

from deadline.unreal_submitter.submitter import (
    UnrealOpenJobSubmitter,
    UnrealRenderOpenJobSubmitter,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (
    UnrealOpenJob,
    RenderUnrealOpenJob,
    UgsRenderUnrealJob,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
    UnrealOpenJobStep,
    RenderUnrealOpenJobStep,
    UgsRenderUnrealOpenJobStep,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (
    UnrealOpenJobEnvironment,
    LaunchEditorUnrealOpenJobEnvironment,
    UgsLaunchEditorUnrealOpenJobEnvironment,
    UgsSyncCmfUnrealOpenJobEnvironment,
    UgsSyncSmfUnrealOpenJobEnvironment,
)

from deadline.unreal_logger import get_logger

logger = get_logger()


if "OPENJD_TEMPLATES_DIRECTORY" not in os.environ:
    os.environ["OPENJD_TEMPLATES_DIRECTORY"] = (
        f"{os.path.dirname(__file__)}/src/unreal_plugin/Content/Python/openjd_templates"
    )

default_open_job = UnrealOpenJob(
    "",
    steps=[UnrealOpenJobStep("")],
    environments=[UnrealOpenJobEnvironment("")],
)


default_render_job = RenderUnrealOpenJob(
    steps=[RenderUnrealOpenJobStep()],
    environments=[LaunchEditorUnrealOpenJobEnvironment()],
)

customized_render_job = RenderUnrealOpenJob(
    steps=[
        UnrealOpenJobStep("", name="PreStep"),
        RenderUnrealOpenJobStep(name="RenderStep", step_dependencies=["PreStep"]),
        UnrealOpenJobStep("", name="PostStep", step_dependencies=["RenderStep"]),
    ],
    environments=[
        UnrealOpenJobEnvironment(
            "", name="CustomEnvironment", variables={"CUSTOM_VAR": "CustomValue"}
        ),
        LaunchEditorUnrealOpenJobEnvironment(),
    ],
)

ugs_cmf_render_job = UgsRenderUnrealJob(
    steps=[UgsRenderUnrealOpenJobStep()],
    environments=[UgsSyncCmfUnrealOpenJobEnvironment(), UgsLaunchEditorUnrealOpenJobEnvironment()],
)

ugs_smf_render_job = UgsRenderUnrealJob(
    steps=[UgsRenderUnrealOpenJobStep()],
    environments=[UgsSyncSmfUnrealOpenJobEnvironment(), UgsLaunchEditorUnrealOpenJobEnvironment()],
)


render_job_submitter = UnrealRenderOpenJobSubmitter(silent_mode=True)
render_job_submitter.add_job(default_render_job)
render_job_submitter.add_job(customized_render_job)
render_job_submitter.add_job(ugs_cmf_render_job)
render_job_submitter.add_job(ugs_smf_render_job)

submitted_job_ids = render_job_submitter.submit_jobs()
for job_id in submitted_job_ids:
    logger.info("Submitted Job id: {}".format(job_id))


open_job_submitter = UnrealOpenJobSubmitter(silent_mode=True)
open_job_submitter.add_job(default_open_job)

submitted_job_ids = open_job_submitter.submit_jobs()
for job_id in submitted_job_ids:
    logger.info("Submitted Job id: {}".format(job_id))

# TODO define paths for simple/custom jobs, steps, envs
