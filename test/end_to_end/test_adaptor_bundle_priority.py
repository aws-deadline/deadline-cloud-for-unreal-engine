# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
E2E test: Verify adaptor bundle takes priority over conda when both are available.

Submits a job with the adaptor bundle attached AND unrealengine-openjd in CondaPackages.
Confirms the job renders successfully and that the bundle was used instead of conda.
"""

import logging
import re

from conftest import (
    extract_job_info_from_test_output,
    get_session_log_events,
    wait_for_job_state,
)

logger = logging.getLogger(__name__)


def test_adaptor_bundle_priority_over_conda(
    deadline_client,
    build_plugin,
    create_readonly_test_project,
    run_unreal_test,
    deadline_worker_agent,
):
    """
    Submit a job with adaptor bundle attached AND unrealengine-openjd in CondaPackages.
    Verify bundle is used, not conda.
    """
    _, uproject_file = create_readonly_test_project

    deadlineargs = (
        "-NoLoadingScreen -FixedSeed -log -Unattended -MRQInstance "
        "-deterministicaudio -audiomixer "
        '-CondaPackages="unrealengine=5.7 unrealengine-openjd=0.6.*"'
    )

    logger.info("Submitting job with adaptor bundle AND unrealengine-openjd in CondaPackages")
    success, output_lines = run_unreal_test(
        "DeadlineCloud.Integration.CreateJob", uproject_file, deadlineargs=deadlineargs
    )
    assert success, "Create job test failed"

    job_id, farm_id, queue_id = extract_job_info_from_test_output(output_lines)
    assert job_id and farm_id and queue_id, "Could not extract job information from test output"

    success, status, message = wait_for_job_state(
        deadline_client=deadline_client,
        farm_id=farm_id,
        job_id=job_id,
        queue_id=queue_id,
        expected_states=["SUCCEEDED"],
        max_wait_time=600,
        wait_interval=10,
    )
    assert success, f"Job did not succeed: {message}"
    logger.info(f"Job {job_id} SUCCEEDED")

    log_messages = get_session_log_events(deadline_client, farm_id, queue_id, job_id)

    bundle_used = any(
        re.search(r"Using adaptor from job attachment bundle", msg) for msg in log_messages
    )
    assert (
        bundle_used
    ), "Expected bundle to be used but 'Using adaptor from job attachment bundle' not found in logs"

    conda_fallback_used = any(
        re.search(r"Adaptor found on PATH via conda, using as fallback", msg)
        for msg in log_messages
    )
    assert not conda_fallback_used, "Bundle should take priority but conda fallback was used"
    logger.info("Confirmed: bundle used, conda ignored")
