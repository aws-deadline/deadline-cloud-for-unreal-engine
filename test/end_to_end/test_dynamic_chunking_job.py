# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
End-to-end test for the bundled dynamic-chunking template pair
(``dynamic_chunking_render_job.yml`` + ``dynamic_chunking_render_step.yml``).

The test composes those shipped templates into one job, submits it to a real
worker, and verifies both scheduler chunking and adaptor rendering. Service-side
acceptance of the required ``Frames`` parameter and ``TASK_CHUNKING`` extension
is implicit in successful job creation.

The in-editor submission path and missing/empty ``Frames`` validation are
covered by submitter unit tests.
"""

import json
import logging
import os
from typing import Any

import yaml

from conftest import (
    cancel_job,
    extract_job_info_from_test_output,
    get_source_root,
    wait_for_job_state,
)

logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(
    get_source_root(),
    "src",
    "unreal_plugin",
    "Content",
    "Python",
    "openjd_templates",
    "dynamic_chunking",
)


def _compose_dynamic_chunking_job_template(job_name: str, queue_manifest_path: str) -> dict:
    """
    Compose a submittable OpenJD job template from the bundled dynamic-chunking
    job and step templates, the same way the submitter assembles them:
    the step template is attached under ``steps`` and the task parameter
    ranges the submitter would populate (Handler, QueueManifestPath) are
    filled in.

    Args:
        job_name: Name for the Deadline Cloud job. Following the repo's e2e
            convention (see ``run_unreal_test`` in conftest), each submitted
            job is named after the pytest test that created it so it can be
            traced back. Deadline Cloud job names are capped at 128 chars.
        queue_manifest_path: Donor job's serialized MRQ manifest path.

    Returns:
        The composed job template as a dict.
    """
    with open(os.path.join(TEMPLATES_DIR, "dynamic_chunking_render_job.yml")) as f:
        job_template = yaml.safe_load(f)
    with open(os.path.join(TEMPLATES_DIR, "dynamic_chunking_render_step.yml")) as f:
        step_template = yaml.safe_load(f)

    job_template["name"] = job_name[:128]

    # Fill the task parameter ranges that the submitter populates at
    # submission time. The DynamicChunking CHUNK[INT] parameter keeps its
    # "{{Param.Frames}}" range reference - that is resolved by the service.
    for task_param in step_template["parameterSpace"]["taskParameterDefinitions"]:
        if task_param["name"] == "Handler":
            task_param["range"] = ["render"]
        elif task_param["name"] == "QueueManifestPath":
            task_param["range"] = [queue_manifest_path]

    job_template["steps"] = [step_template]
    return job_template


def _load_launch_environment_template() -> dict:
    """
    Load the LaunchUnrealEditor job environment from the source tree.

    The dynamic-chunking job template has no ``jobEnvironments`` section (the
    in-editor flow attaches the environment from a separate Data Asset), so a
    direct-API submission must compose the environment in - without it there
    is no adaptor daemon for the render step's ``daemon run`` to talk to.
    """
    launch_env_path = os.path.join(
        get_source_root(),
        "src",
        "unreal_plugin",
        "Content",
        "Python",
        "openjd_templates",
        "launch_ue_environment.yml",
    )
    with open(launch_env_path) as f:
        return yaml.safe_load(f)


def test_dynamic_chunking_render_job_succeeds(
    deadline_client,
    build_plugin,
    create_readonly_test_project,
    run_unreal_test,
    reusable_queue_fleet_association,
    deadline_worker_agent,
    request,
):
    """
    Render a dynamic-chunking job end to end on a real worker, exercising the
    adaptor side of the change (dynamic_chunked_frames parsing and MRQ frame
    windows).

    The dynamic-chunking templates cannot yet be submitted from the editor
    (no Data Assets reference them), so this test uses a donor job:

    1. Submit a normal job through the editor's MRQ flow. This uploads the
       real Unreal project and serialized MRQ manifest as job attachments.
    2. Cancel the donor before a worker picks it up, and harvest its job
       attachments, parameter values, and the QueueManifestPath task value.
    3. Resubmit under the dynamic-chunking template pair with Frames="1-10"
       and ChunkSize=5, so the scheduler forms 2 chunks.
    4. Wait for SUCCEEDED and assert 10 tasks (one per frame - chunking is a
       dispatch-time grouping, not a task-count reduction) ran via exactly 2
       taskRun session actions - proof the scheduler chunked the range and
       the adaptor rendered each dynamic_chunked_frames window.
    """
    _, uproject_file = create_readonly_test_project

    # --- 1. Donor job: real attachments + manifest via the editor flow ---
    logger.info(f"Submitting donor job from project {uproject_file}")
    success, output_lines = run_unreal_test(
        "DeadlineCloud.Integration.CreateJob",
        uproject_file,
        job_name=f"{request.node.name}_donor",
    )
    assert success, "Donor job submission failed"

    donor_job_id, farm_id, queue_id = extract_job_info_from_test_output(output_lines)
    assert donor_job_id and farm_id and queue_id, "Could not extract donor job information"

    # Cancel the donor immediately - only its attachments/parameters are
    # needed, and the fixture's worker agent must not waste time rendering it.
    cancel_job(deadline_client, farm_id, queue_id, donor_job_id)

    donor_job = deadline_client.get_job(farmId=farm_id, queueId=queue_id, jobId=donor_job_id)
    donor_parameters = donor_job.get("parameters", {})
    donor_attachments = donor_job.get("attachments")
    assert donor_attachments, "Donor job has no job attachments to reuse"

    # QueueManifestPath is a task-level parameter on the donor's Render step.
    donor_steps = deadline_client.list_steps(
        farmId=farm_id, queueId=queue_id, jobId=donor_job_id
    ).get("steps", [])
    render_steps = [s for s in donor_steps if s.get("name") == "Render"]
    assert render_steps, f"Donor job has no Render step: {[s.get('name') for s in donor_steps]}"
    donor_tasks = deadline_client.list_tasks(
        farmId=farm_id, queueId=queue_id, jobId=donor_job_id, stepId=render_steps[0]["stepId"]
    ).get("tasks", [])
    assert donor_tasks, "Donor Render step has no tasks"
    queue_manifest_path = donor_tasks[0]["parameters"]["QueueManifestPath"]["path"]

    # --- 2. Compose the dynamic-chunking job ---
    job_template = _compose_dynamic_chunking_job_template(
        job_name=request.node.name, queue_manifest_path=queue_manifest_path
    )
    job_template["jobEnvironments"] = [_load_launch_environment_template()]

    # Carry over the donor's values for the parameters the two templates
    # share, so the render environment matches the known-good standard flow.
    dynamic_param_names = {p["name"] for p in job_template["parameterDefinitions"]}
    parameters = {
        name: value for name, value in donor_parameters.items() if name in dynamic_param_names
    }
    # Frames="1-10" with ChunkSize=5: per the TASK_CHUNKING RFC the parameter
    # space is the same as for a plain INT parameter - 10 frames = 10 tasks.
    # Chunking happens at DISPATCH time: the scheduler groups the tasks into
    # 2 contiguous chunks ("1-5", "6-10") and runs each chunk as a single
    # session action. Small range keeps the render short while still
    # exercising multi-chunk dispatch.
    parameters["Frames"] = {"string": "1-10"}
    parameters["ChunkSize"] = {"int": "5"}
    parameters["TargetRuntimeSeconds"] = {"int": "0"}
    expected_task_count = 10  # one task per frame; chunking does NOT reduce task count
    expected_chunk_count = 2  # ceil(10 frames / ChunkSize 5) dispatch chunks

    create_job_kwargs = dict(
        farmId=farm_id,
        queueId=queue_id,
        template=json.dumps(job_template),
        templateType="JSON",
        priority=50,
        parameters=parameters,
        attachments=donor_attachments,
    )
    if donor_job.get("storageProfileId"):
        create_job_kwargs["storageProfileId"] = donor_job["storageProfileId"]

    response = deadline_client.create_job(**create_job_kwargs)
    job_id = response.get("jobId")
    assert job_id, "CreateJob did not return a jobId"
    logger.info(f"Dynamic chunking render job created: {job_id}")

    try:
        # --- 3. Render on the fixture's worker agent ---
        success, status, message = wait_for_job_state(
            deadline_client=deadline_client,
            farm_id=farm_id,
            job_id=job_id,
            queue_id=queue_id,
            expected_states=["SUCCEEDED"],
            max_wait_time=900,
            wait_interval=10,
        )
        assert success, f"Dynamic chunking render job did not succeed: {message}"
        logger.info(f"Dynamic chunking render job {job_id} SUCCEEDED")

        # --- 4. Verify the scheduler actually chunked the frame range ---
        # The parameter space still has one task per frame (chunking is a
        # dispatch-time grouping, not a task-count reduction) ...
        steps = deadline_client.list_steps(farmId=farm_id, queueId=queue_id, jobId=job_id).get(
            "steps", []
        )
        render_step = next((s for s in steps if s.get("name") == "Render"), None)
        assert render_step, f"No Render step on the job: {[s.get('name') for s in steps]}"
        tasks = deadline_client.list_tasks(
            farmId=farm_id, queueId=queue_id, jobId=job_id, stepId=render_step["stepId"]
        ).get("tasks", [])
        assert len(tasks) == expected_task_count, (
            f"Expected {expected_task_count} tasks - one per frame in Frames=1-10 "
            f"(chunking does not reduce the task count) - got {len(tasks)}"
        )
        unsucceeded = [t["taskId"] for t in tasks if t.get("runStatus") != "SUCCEEDED"]
        assert not unsucceeded, f"Tasks did not succeed: {unsucceeded}"

        # ... while each chunk runs as a single taskRun session action, so a
        # 10-frame range with ChunkSize=5 dispatches exactly 2 taskRun actions.
        task_run_actions: list[dict[str, Any]] = []
        sessions = deadline_client.list_sessions(
            farmId=farm_id, queueId=queue_id, jobId=job_id
        ).get("sessions", [])
        for session in sessions:
            actions = deadline_client.list_session_actions(
                farmId=farm_id,
                queueId=queue_id,
                jobId=job_id,
                sessionId=session["sessionId"],
            ).get("sessionActions", [])
            task_run_actions.extend(a for a in actions if a.get("definition", {}).get("taskRun"))
        for action in task_run_actions:
            logger.info(
                "Chunk taskRun action %s parameters: %s",
                action["sessionActionId"],
                action["definition"]["taskRun"].get("parameters"),
            )
        assert len(task_run_actions) == expected_chunk_count, (
            f"Expected {expected_chunk_count} chunk dispatches (taskRun session actions) "
            f"for Frames=1-10 with ChunkSize=5, got {len(task_run_actions)}"
        )

        actual_chunk_windows = {
            action["definition"]["taskRun"]
            .get("parameters", {})
            .get("DynamicChunking", {})
            .get("chunkInt")
            for action in task_run_actions
        }
        expected_chunk_windows = {"1-5", "6-10"}
        assert actual_chunk_windows == expected_chunk_windows, (
            f"Expected dispatched DynamicChunking windows {expected_chunk_windows}, "
            f"got {actual_chunk_windows}"
        )
    finally:
        logger.info(f"Cleaning up: canceling job {job_id}")
        cancel_job(deadline_client, farm_id, queue_id, job_id)
