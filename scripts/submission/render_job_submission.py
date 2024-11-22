import os
import unreal
from deadline.unreal_submitter.submitter import (
    UnrealRenderOpenJobSubmitter,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (
    RenderUnrealOpenJob,
    UnrealOpenJobParameterDefinition
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
    RenderUnrealOpenJobStep,
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

queue = unreal.get_editor_subsystem()
default_render_job = RenderUnrealOpenJob(
    steps=[RenderUnrealOpenJobStep()],
    environments=[LaunchEditorUnrealOpenJobEnvironment()],
    extra_parameters=[
        UnrealOpenJobParameterDefinition("Executable", "FLOAT", 1.0)
    ],
    mrq_job=
)


render_job_submitter = UnrealRenderOpenJobSubmitter(silent_mode=True)
render_job_submitter.add_job(default_render_job)
from pprint import pprint
for job in render_job_submitter._jobs:
    pprint(job.build_template())

