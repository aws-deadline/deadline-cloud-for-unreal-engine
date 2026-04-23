# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import logging
import re

from conftest import (
    extract_job_info_from_test_output,
    get_session_log_events,
    wait_for_job_state,
    get_last_session_project_plugins,
    add_content_plugins_to_project,
    add_plugins_to_project,
)

logger = logging.getLogger(__name__)


def test_create_job_with_worker_agent(
    deadline_client,
    build_plugin,
    create_readonly_test_project,
    run_unreal_test,
    deadline_worker_agent,
):
    """
    Run CreateJob automation test from within Unreal with a local worker agent running.
    This test verifies that the job is processed by the local worker agent.
    """

    # The deadline_worker_agent fixture will start the worker agent before this test runs
    # and will stop it after the test completes

    _, uproject_file = create_readonly_test_project

    logger.info(f"Creating job from project {uproject_file}")
    success, output_lines = run_unreal_test("DeadlineCloud.Integration.CreateJob", uproject_file)
    assert success, "Create job test failed"

    # Extract job ID and farm ID from the output
    job_id, farm_id, queue_id = extract_job_info_from_test_output(output_lines)

    if job_id and farm_id and queue_id:

        # Wait for job completion
        success, status, message = wait_for_job_state(
            deadline_client=deadline_client,
            farm_id=farm_id,
            job_id=job_id,
            queue_id=queue_id,
            expected_states=["SUCCEEDED"],
            max_wait_time=600,
            wait_interval=10,
        )

        assert success

        logger.info(f"Job {job_id} SUCCEEDED")

        # Verify adaptor bundle was used (T1)
        log_messages = get_session_log_events(deadline_client, farm_id, queue_id, job_id)
        bundle_used = any(
            re.search(r"Using adaptor from job attachment bundle", msg) for msg in log_messages
        )
        assert bundle_used, "Expected adaptor bundle to be used but log message not found"
        logger.info("Confirmed: adaptor bundle was used")

        # Verify AdaptorSetup onEnter ran exactly once — env persists across steps (T6)
        bundle_setup_count = sum(
            1 for msg in log_messages if "Using adaptor from job attachment bundle" in msg
        )
        assert (
            bundle_setup_count == 1
        ), f"Expected AdaptorSetup onEnter once but found {bundle_setup_count} times"
        logger.info("Confirmed: AdaptorSetup onEnter ran exactly once")

        # Verify CondaPackages does not contain unrealengine-openjd (T7)
        job = deadline_client.get_job(farmId=farm_id, queueId=queue_id, jobId=job_id)
        conda_value = job.get("parameters", {}).get("CondaPackages", {}).get("string", "")
        assert (
            "unrealengine-openjd" not in conda_value
        ), f"CondaPackages should not contain unrealengine-openjd but got: '{conda_value}'"
        logger.info(f"Confirmed: CondaPackages='{conda_value}' (no unrealengine-openjd)")
    else:
        logger.warning("Could not extract job ID or farm ID from test output")
        assert False, "Could not extract job information from test output"


def test_worker_agent_project_plugins(
    deadline_client,
    build_plugin,
    create_readonly_test_project,
    run_unreal_test,
    deadline_worker_agent,
):

    # The deadline_worker_agent fixture will start the worker agent before this test runs
    # and will stop it after the test completes

    _, uproject_file = create_readonly_test_project

    # Add content plugins
    # 1,3 enabled by default and 2,4 disabled by default
    add_content_plugins_to_project(_, ["EmptyContentPlugin1", "EmptyContentPlugin3"], True)
    add_content_plugins_to_project(_, ["EmptyContentPlugin2", "EmptyContentPlugin4"], False)

    # Disable plugin 1 and enable plugin 2 in the project
    add_plugins_to_project(uproject_file, ["EmptyContentPlugin1"], False)
    add_plugins_to_project(uproject_file, ["EmptyContentPlugin2"], True)

    # As a result, we end up with two active plugins(2,3) and two inactive ones(1,4) via different paths

    logger.info(f"Creating job from project {uproject_file}")
    success, output_lines = run_unreal_test("DeadlineCloud.Integration.CreateJob", uproject_file)
    assert success, "Create job test failed"

    # Extract job ID and farm ID from the output
    job_id, farm_id, queue_id = extract_job_info_from_test_output(output_lines)

    if job_id and farm_id and queue_id:

        # Wait for job completion
        wait_for_job_state(
            deadline_client=deadline_client,
            farm_id=farm_id,
            job_id=job_id,
            queue_id=queue_id,
            expected_states=["SUCCEEDED"],
            max_wait_time=600,
            wait_interval=10,
        )

        # Verify which project plugins were loaded by the worker
        worker_project_plugins = get_last_session_project_plugins(
            deadline_client=deadline_client,
            farm_id=farm_id,
            queue_id=queue_id,
            job_id=job_id,
        )

        logger.info(f"Worker project plugins: {worker_project_plugins}")

        # The worker should have loaded EmptyContentPlugin2 and EmptyContentPlugin3 only
        assert "EmptyContentPlugin1" not in worker_project_plugins
        assert "EmptyContentPlugin2" in worker_project_plugins
        assert "EmptyContentPlugin3" in worker_project_plugins
        assert "EmptyContentPlugin4" not in worker_project_plugins

    else:
        logger.warning("Could not extract job ID or farm ID from test output")
        assert False, "Could not extract job information from test output"
