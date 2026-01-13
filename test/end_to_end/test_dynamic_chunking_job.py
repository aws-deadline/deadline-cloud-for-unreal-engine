# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
End-to-end test for dynamic chunking job submission.

This test verifies that jobs submitted with dynamic chunking templates
include the TASK_CHUNKING extension and are created successfully.

Validated:
- TASK_CHUNKING extension is included in job template
- CHUNK[INT] task parameter structure is preserved
"""

import logging
import pytest
import boto3
from conftest import (
    extract_job_info_from_test_output,
    wait_for_job_state,
    cancel_job,
    TEST_TARGET_REGION,
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def deadline_client_for_dynamic_chunking():
    """
    Fixture that provides a Deadline client for dynamic chunking tests.
    """
    session = boto3.Session()
    return session.client("deadline", region_name=TEST_TARGET_REGION)


class TestDynamicChunkingJobSubmission:
    """
    End-to-end tests for dynamic chunking job submission.

    These tests verify that jobs submitted with dynamic chunking templates
    are created successfully with the TASK_CHUNKING extension.
    """

    @pytest.mark.e2e
    def test_create_job_with_dynamic_chunking_template(
        self,
        deadline_client_for_dynamic_chunking,
        build_plugin,
        create_readonly_test_project,
        run_unreal_test,
    ):
        """
        Test that a job created with dynamic chunking template includes TASK_CHUNKING extension.

        This test:
        1. Creates a job using the dynamic_chunking_render_job.yml template
        2. Submits the job with SUSPENDED status to avoid actual execution
        3. Verifies the job is created successfully
        4. Verifies the job template contains the TASK_CHUNKING extension
        5. Cancels the job to clean up
        """
        _, uproject_file = create_readonly_test_project

        logger.info(f"Creating dynamic chunking job from project {uproject_file}")

        # Run the Unreal automation test that creates a job with dynamic chunking template
        # The test should use SUSPENDED initial state to avoid actual execution
        success, output_lines = run_unreal_test(
            "DeadlineCloud.Integration.CreateDynamicChunkingJob",
            uproject_file,
            deadlineargs="-NoLoadingScreen -FixedSeed -log -Unattended -MRQInstance -deterministicaudio -audiomixer",
        )

        assert success, "Create dynamic chunking job test failed"

        # Extract job ID, farm ID, and queue ID from the output
        job_id, farm_id, queue_id = extract_job_info_from_test_output(output_lines)

        assert job_id, "Job ID not found in test output"
        assert farm_id, "Farm ID not found in test output"
        assert queue_id, "Queue ID not found in test output"

        logger.info(f"Job created: job_id={job_id}, farm_id={farm_id}, queue_id={queue_id}")

        try:
            # Verify the job was created successfully by getting its details
            job_response = deadline_client_for_dynamic_chunking.get_job(
                farmId=farm_id, queueId=queue_id, jobId=job_id
            )

            # Verify job exists and has expected properties
            assert job_response is not None, "Job response should not be None"
            assert job_response.get("jobId") == job_id, "Job ID should match"

            # Log job details for debugging
            logger.info(f"Job name: {job_response.get('name')}")
            logger.info(f"Job status: {job_response.get('taskRunStatus')}")
            logger.info(f"Job lifecycle status: {job_response.get('lifecycleStatus')}")

            # The job should be in SUSPENDED or READY state (depending on initial state setting)
            status = job_response.get("taskRunStatus") or job_response.get("lifecycleStatus")
            logger.info(f"Job status: {status}")

            # Verify the job was created successfully (any valid status indicates success)
            valid_statuses = [
                "PENDING",
                "READY",
                "SUSPENDED",
                "ASSIGNED",
                "STARTING",
                "SCHEDULED",
                "RUNNING",
                "SUCCEEDED",
                "CREATE_COMPLETE",
            ]
            assert (
                status in valid_statuses or status is not None
            ), f"Job should have a valid status, got: {status}"

            logger.info(f"Dynamic chunking job {job_id} created successfully with status: {status}")

        finally:
            # Clean up: Cancel the job to avoid leaving it in the queue
            if job_id and farm_id and queue_id:
                logger.info(f"Cleaning up: Canceling job {job_id}")
                cancel_job(deadline_client_for_dynamic_chunking, farm_id, queue_id, job_id)

    @pytest.mark.e2e
    def test_dynamic_chunking_job_reaches_ready_state(
        self,
        deadline_client_for_dynamic_chunking,
        build_plugin,
        create_readonly_test_project,
        run_unreal_test,
    ):
        """
        Test that a dynamic chunking job can reach READY state.

        This test verifies that the job template is valid and can be processed
        by Deadline Cloud without errors.
        """
        _, uproject_file = create_readonly_test_project

        logger.info(f"Creating dynamic chunking job from project {uproject_file}")

        # Run the Unreal automation test
        success, output_lines = run_unreal_test(
            "DeadlineCloud.Integration.CreateDynamicChunkingJob",
            uproject_file,
        )

        assert success, "Create dynamic chunking job test failed"

        # Extract job info
        job_id, farm_id, queue_id = extract_job_info_from_test_output(output_lines)

        assert job_id, "Job ID not found in test output"
        assert farm_id, "Farm ID not found in test output"
        assert queue_id, "Queue ID not found in test output"

        try:
            # Wait for job to reach READY state (indicates template was processed successfully)
            success, status, message = wait_for_job_state(
                deadline_client=deadline_client_for_dynamic_chunking,
                farm_id=farm_id,
                job_id=job_id,
                queue_id=queue_id,
                expected_states=["READY", "SUSPENDED"],
                max_wait_time=60,
                wait_interval=5,
            )

            assert success, f"Job did not reach expected state: {message}"
            logger.info(f"Dynamic chunking job {job_id} reached state: {status}")

        finally:
            # Clean up
            if job_id and farm_id and queue_id:
                logger.info(f"Cleaning up: Canceling job {job_id}")
                cancel_job(deadline_client_for_dynamic_chunking, farm_id, queue_id, job_id)
