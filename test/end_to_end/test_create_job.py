# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import logging
from conftest import (
    extract_job_info_from_test_output,
    wait_for_job_state,
    cancel_job,
)

logger = logging.getLogger(__name__)


def test_create_job(
    deadline_client, build_plugin, create_readonly_test_project, run_unreal_test, request
):
    """Run CreateJob automation test from within Unreal and monitor job status until READY, then cancel it"""

    _, uproject_file = create_readonly_test_project

    logger.info(f"Creating job from project {uproject_file}")
    success, output_lines = run_unreal_test("DeadlineCloud.Integration.CreateJob", uproject_file)
    assert success, "Create job test failed"

    # Extract job ID and farm ID from the output
    job_id, farm_id, queue_id = extract_job_info_from_test_output(output_lines)

    assert job_id
    assert farm_id
    assert queue_id

    # For checking if a job is in READY state:
    success, status, message = wait_for_job_state(
        deadline_client=deadline_client,
        farm_id=farm_id,
        job_id=job_id,
        queue_id=queue_id,
        expected_states=["READY"],
        max_wait_time=30,
        wait_interval=5,
    )
    assert success, message

    if request.config.getoption("--no-cancel"):
        logger.info(f"Job {job_id} is in READY state, skipping cancel (--no-cancel)")
    else:
        # Once the job is in READY state, cancel it since test_worker_agent.py will handle the full job execution
        logger.info(f"Job {job_id} is in READY state, canceling it...")
        cancel_job(deadline_client, farm_id, queue_id, job_id)
