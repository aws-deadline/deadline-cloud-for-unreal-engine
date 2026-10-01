# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import logging

from deadline.client.api import get_queue_user_boto3_session
from deadline.job_attachments.download import (
    OutputDownloader,
    get_output_manifests_by_asset_root,
)
from deadline.job_attachments.models import JobAttachmentS3Settings

from conftest import (
    DEFAULT_ENV_ENTER_TIMEOUT_SECONDS,
    DEFAULT_ENV_EXIT_TIMEOUT_SECONDS,
    extract_job_info_from_test_output,
    get_openjd_templates_directory,
    openjd_templates_with_env_enter_timeout,
    read_launch_environment_template,
    wait_for_job_state,
    get_last_session_project_plugins,
    add_content_plugins_to_project,
    add_plugins_to_project,
)

logger = logging.getLogger(__name__)


def get_job_output_manifest_paths(deadline_client, farm_id, queue_id, job_id):
    """List the paths uploaded through a job's output attachment manifests."""
    queue = deadline_client.get_queue(farmId=farm_id, queueId=queue_id)
    queue_user_session = get_queue_user_boto3_session(
        deadline=deadline_client,
        farm_id=farm_id,
        queue_id=queue_id,
        queue_display_name=queue["displayName"],
    )
    manifests_by_root = get_output_manifests_by_asset_root(
        s3_settings=JobAttachmentS3Settings(**queue["jobAttachmentSettings"]),
        farm_id=farm_id,
        queue_id=queue_id,
        job_id=job_id,
        session=queue_user_session,
    )

    output_paths = []
    for root, manifests in manifests_by_root.items():
        normalized_root = root.replace("\\", "/").rstrip("/")
        for manifest in manifests:
            for entry in manifest.paths:
                normalized_path = entry.path.replace("\\", "/").lstrip("/")
                output_paths.append(f"{normalized_root}/{normalized_path}")
    return sorted(output_paths)


def test_create_job_with_worker_agent(
    deadline_client,
    build_plugin,
    create_readonly_test_project,
    run_unreal_test,
    reusable_queue_fleet_association,
    deadline_worker_agent,
    request,
):
    """
    Run CreateJob automation test from within Unreal with a local worker agent running.
    This test verifies that the job is processed by the local worker agent.
    """

    # The deadline_worker_agent fixture will start the worker agent before this test runs
    # and will stop it after the test completes

    _, uproject_file = create_readonly_test_project

    # Verify the LaunchUnrealEditor environment template used for submission
    # defines the default OpenJD action timeouts, so the job submitted below
    # runs with (and completes within) those defaults.
    templates_directory = get_openjd_templates_directory(request.config.getoption("--ueversion"))
    launch_environment_actions = read_launch_environment_template(templates_directory)["script"][
        "actions"
    ]
    assert launch_environment_actions["onEnter"]["timeout"] == DEFAULT_ENV_ENTER_TIMEOUT_SECONDS
    assert launch_environment_actions["onExit"]["timeout"] == DEFAULT_ENV_EXIT_TIMEOUT_SECONDS

    logger.info(f"Creating job from project {uproject_file}")
    success, output_lines = run_unreal_test("DeadlineCloud.Integration.CreateJob", uproject_file)
    assert success, "Create job test failed"

    # Extract job ID and farm ID from the output
    job_id, farm_id, queue_id = extract_job_info_from_test_output(output_lines)

    if job_id and farm_id and queue_id:
        success, status, message = wait_for_job_state(
            deadline_client=deadline_client,
            farm_id=farm_id,
            job_id=job_id,
            queue_id=queue_id,
            expected_states=["SUCCEEDED"],
            max_wait_time=600,
            wait_interval=10,
        )

        assert success, message

        output_paths = get_job_output_manifest_paths(
            deadline_client=deadline_client,
            farm_id=farm_id,
            queue_id=queue_id,
            job_id=job_id,
        )
        assert not any(
            "/saved/profiling/" in path.lower() for path in output_paths
        ), f"Profiling outputs were produced for a profiling-disabled job: {output_paths}"

        logger.info(f"Job {job_id} SUCCEEDED")
    else:
        logger.warning("Could not extract job ID or farm ID from test output")
        assert False, "Could not extract job information from test output"


def test_worker_agent_profiling_outputs_are_attached(
    deadline_client,
    build_plugin,
    create_readonly_test_project,
    run_unreal_test,
    reusable_queue_fleet_association,
    deadline_worker_agent,
    tmp_path,
):
    """
    Submit a profiling-enabled render and verify its Insights, CSV, and
    MemReport artifacts are uploaded as Deadline job outputs.
    """

    _, uproject_file = create_readonly_test_project

    success, output_lines = run_unreal_test(
        "DeadlineCloud.Integration.CreateJob",
        uproject_file,
        extra_test_params={"profiling": "all", "csv_capture_frames": 10},
    )
    assert success, "Profiling job submission failed"

    job_id, farm_id, queue_id = extract_job_info_from_test_output(output_lines)
    assert job_id and farm_id and queue_id, "Could not extract profiling job information"

    success, status, message = wait_for_job_state(
        deadline_client=deadline_client,
        farm_id=farm_id,
        job_id=job_id,
        queue_id=queue_id,
        expected_states=["SUCCEEDED"],
        max_wait_time=600,
        wait_interval=10,
    )
    assert success, message

    output_paths = get_job_output_manifest_paths(
        deadline_client=deadline_client,
        farm_id=farm_id,
        queue_id=queue_id,
        job_id=job_id,
    )
    profiling_paths = [path for path in output_paths if "/saved/profiling/" in path.lower()]

    assert any(
        "/deadlinecloud/" in path.lower() and path.lower().endswith(".utrace")
        for path in profiling_paths
    ), f"Insights trace missing from profiling outputs: {profiling_paths}"
    assert any(
        "/csv/" in path.lower() and path.lower().endswith(".csv") for path in profiling_paths
    ), f"CSV profile missing from profiling outputs: {profiling_paths}"
    assert any(
        "/memreports/" in path.lower() and path.lower().endswith(".memreport")
        for path in profiling_paths
    ), f"MemReport missing from profiling outputs: {profiling_paths}"

    queue = deadline_client.get_queue(farmId=farm_id, queueId=queue_id)
    queue_user_session = get_queue_user_boto3_session(
        deadline=deadline_client,
        farm_id=farm_id,
        queue_id=queue_id,
        queue_display_name=queue["displayName"],
    )
    profiling_output_downloader = OutputDownloader(
        s3_settings=JobAttachmentS3Settings(**queue["jobAttachmentSettings"]),
        farm_id=farm_id,
        queue_id=queue_id,
        job_id=job_id,
        session=queue_user_session,
        include_filters=["**/*.utrace", "**/*.csv", "**/*.memreport"],
    )
    profiling_output_dir = tmp_path / "profiling-outputs"
    for root in profiling_output_downloader.get_paths_by_root():
        profiling_output_downloader.set_root_path(root, str(profiling_output_dir))
    profiling_output_downloader.download()

    downloaded_traces = list(profiling_output_dir.rglob("*.utrace"))
    assert len(downloaded_traces) == 2
    assert any("startup-" in trace.name for trace in downloaded_traces)
    assert any("task-" in trace.name for trace in downloaded_traces)
    for trace in downloaded_traces:
        trace_data = trace.read_bytes()
        assert trace_data[:4] == b"2CRT"
        assert b"Memory" in trace_data and b"Alloc" in trace_data

    downloaded_csv_files = list(profiling_output_dir.rglob("*.csv"))
    assert len(downloaded_csv_files) == 1
    csv_lines = [
        line
        for line in downloaded_csv_files[0].read_text(errors="replace").splitlines()
        if line.strip()
    ]
    assert len(csv_lines) > 1
    assert any("," in line for line in csv_lines)

    downloaded_memreports = list(profiling_output_dir.rglob("*.memreport"))
    assert len(downloaded_memreports) == 1
    memreport = downloaded_memreports[0].read_text(errors="replace")
    assert 'MemReport: Begin command "Mem FromReport"' in memreport
    assert "Platform Memory Stats" in memreport
    assert 'MemReport: End command "Mem FromReport"' in memreport


def test_worker_agent_project_plugins(
    deadline_client,
    build_plugin,
    create_readonly_test_project,
    run_unreal_test,
    reusable_queue_fleet_association,
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
        success, status, message = wait_for_job_state(
            deadline_client=deadline_client,
            farm_id=farm_id,
            job_id=job_id,
            queue_id=queue_id,
            expected_states=["SUCCEEDED"],
            max_wait_time=600,
            wait_interval=10,
        )
        # The plugin assertions below need a completed session; if the job
        # didn't reach SUCCEEDED, the loaded-plugin log lines are unreliable.
        assert success, message

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


def test_worker_agent_environment_enter_timeout(
    deadline_client,
    build_plugin,
    create_readonly_test_project,
    run_unreal_test,
    reusable_queue_fleet_association,
    deadline_worker_agent,
    request,
):
    """
    Submit a job whose LaunchUnrealEditor environment onEnter timeout is far
    too short for the Unreal Editor to start on the worker, and verify the
    worker agent enforces the OpenJD action timeout by failing the job.
    """

    # The deadline_worker_agent fixture will start the worker agent before this test runs
    # and will stop it after the test completes

    _, uproject_file = create_readonly_test_project

    # The environment enter (adaptor daemon start + Unreal Editor launch) takes
    # far longer than this, so the worker agent must cancel the action when the
    # timeout elapses and fail the job.
    short_enter_timeout_seconds = 5

    with openjd_templates_with_env_enter_timeout(
        enter_timeout_seconds=short_enter_timeout_seconds,
        ue_version=request.config.getoption("--ueversion"),
    ):
        logger.info(
            f"Creating job with {short_enter_timeout_seconds}s environment enter timeout "
            f"from project {uproject_file}"
        )
        success, output_lines = run_unreal_test(
            "DeadlineCloud.Integration.CreateJob", uproject_file
        )
        assert success, "Create job test failed"

    # Extract job ID and farm ID from the output
    job_id, farm_id, queue_id = extract_job_info_from_test_output(output_lines)

    assert job_id and farm_id and queue_id, "Could not extract job information from test output"

    success, status, message = wait_for_job_state(
        deadline_client=deadline_client,
        farm_id=farm_id,
        job_id=job_id,
        queue_id=queue_id,
        expected_states=["FAILED"],
        max_wait_time=600,
        wait_interval=10,
    )

    assert success, (
        f"Expected job {job_id} to FAIL because the environment enter exceeds its "
        f"{short_enter_timeout_seconds}s timeout: {message}"
    )

    logger.info(f"Job {job_id} FAILED as expected due to environment enter timeout")
