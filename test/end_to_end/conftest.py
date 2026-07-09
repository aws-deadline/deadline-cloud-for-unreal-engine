# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Add repository root to path at the very beginning of the file
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

# Now all other imports, including those from your project
import boto3
import botocore
import deadline.client.config as config
import json
import logging
import psutil
import pytest
import re
import shutil
import signal
import subprocess
import tempfile
import time
from scripts.build_plugin import find_engine_root

# Import typing information
from botocore.client import BaseClient
from typing import Any, Callable, Dict, Generator, List, Tuple, Optional

# Configure logger to make resource reuse/creation messages stand out
logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """
    Configure logging to display INFO level messages to console with timestamp.
    Sets up a console handler with appropriate formatting for test output.
    """
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatter with timestamp
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s", datefmt="%H:%M:%S")
    console_handler.setFormatter(formatter)

    # Configure the root logger so all module loggers inherit this configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add the console handler to the root logger
    root_logger.addHandler(console_handler)


# Set up logging when this module is imported
setup_logging()

# Add the repository root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))


# Default configuration for customer managed fleets
DEFAULT_MIN_CMF_CONFIGURATION: Dict[str, Any] = {
    "customerManaged": {
        "mode": "NO_SCALING",
        "workerCapabilities": {
            "vCpuCount": {"min": 1},
            "memoryMiB": {"min": 1024},
            "osFamily": "WINDOWS",
            "cpuArchitectureType": "x86_64",
        },
    }
}

# Constants for IAM roles and resource names
DEADLINE_UNREAL_QUEUE_TEST_ROLE: str = "DeadlineUnrealQueueTestRole"
DEADLINE_UNREAL_FLEET_TEST_ROLE: str = "DeadlineUnrealFleetTestRole"
DEADLINE_UNREAL_TEST_QUEUE_NAME: str = "deadline-unreal-test-queue"
DEADLINE_UNREAL_TEST_FLEET_NAME: str = "deadline-unreal-test-fleet"


def get_config_var(key: str, default: str) -> str:
    """
    Get a configuration variable from environment variables with a default fallback.

    Args:
        key: The environment variable name to look up
        default: The default value to use if the environment variable is not set

    Returns:
        The value of the environment variable or the default value
    """
    var = os.environ.get(key, default)
    logger.info(f"Using {var} for {key}")
    return var


# Target AWS region for all tests
TEST_TARGET_REGION: str = get_config_var("TEST_TARGET_REGION", "us-west-2")


@pytest.fixture(scope="session")
def region() -> str:
    """
    Fixture that provides the AWS region for tests.

    Returns:
        The AWS region string to use for all tests
    """
    return TEST_TARGET_REGION


def delete_farm_resource_log_group_util(
    farm_id: str,
    resource_id: str,
) -> None:
    """
    Set retention policy on CloudWatch log groups for farm resources.

    Args:
        farm_id: The farm ID containing the resource
        resource_id: The resource ID (queue or fleet) to set retention policy for
    """
    cwl_client = boto3.client("logs", TEST_TARGET_REGION)
    log_group_name = f"/aws/deadline/{farm_id}/{resource_id}"
    retention_number_of_days = 7
    try:
        cwl_client.put_retention_policy(
            logGroupName=log_group_name, retentionInDays=retention_number_of_days
        )
    except Exception as e:
        logger.warning(f"put_retention_policy exception {str(e)}")


def cancel_pending_jobs(deadline_client: BaseClient, farm_id: str, queue_id: str) -> None:
    """
    Cancel any jobs in the queue that are in a pending or running state.

    Args:
        deadline_client: Boto3 Deadline client
        farm_id: The farm ID
        queue_id: The queue ID to clean up
    """
    try:
        # List all jobs in the queue
        logger.info(f"Checking for pending jobs in queue {queue_id}...")
        response = deadline_client.list_jobs(farmId=farm_id, queueId=queue_id)
        jobs = response.get("jobs", response.get("items", []))

        # States that need cancellation
        active_states = ["PENDING", "READY", "ASSIGNED", "STARTING", "SCHEDULED", "RUNNING"]
        jobs_to_cancel = []

        for job in jobs:
            job_id = job.get("jobId")
            status = job.get("taskRunStatus")

            if status in active_states:
                logger.info(f"Found active job {job_id} with status {status} - will cancel")
                jobs_to_cancel.append(job_id)

        # Cancel any active jobs
        for job_id in jobs_to_cancel:
            cancel_job(deadline_client, farm_id, queue_id, job_id)

        if not jobs_to_cancel:
            logger.info(f"No active jobs found in queue {queue_id}")
        else:
            logger.info(f"Canceled {len(jobs_to_cancel)} active jobs in queue {queue_id}")

    except Exception as e:
        logger.warning(f"Error checking for jobs to cancel: {str(e)}")
        import traceback

        logger.warning(f"Traceback: {traceback.format_exc()}")


def cancel_job(deadline_client: BaseClient, farm_id: str, queue_id: str, job_id: str) -> bool:
    """
    Cancel a specific job in Deadline Cloud.

    Args:
        deadline_client: Boto3 Deadline client
        farm_id: The farm ID containing the job
        queue_id: The queue ID containing the job
        job_id: The job ID to cancel
    Returns:
        bool: True if cancellation was successful, False otherwise
    """
    logger.info(f"Canceling job {job_id}...")
    try:
        deadline_client.update_job(
            farmId=farm_id, queueId=queue_id, jobId=job_id, targetTaskRunStatus="CANCELED"
        )
        logger.info(f"Successfully canceled job {job_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to cancel job {job_id}: {str(e)}")
        return False


def pytest_addoption(parser) -> None:
    """
    Add custom command line options to pytest.

    Args:
        parser: The pytest command line parser
    """
    parser.addoption(
        "--nobuild", action="store_true", default=False, help="Skip build_plugin fixture"
    )
    parser.addoption(
        "--ueversion", action="store", default=None, help="Specify Unreal Engine version (e.g. 5.4)"
    )
    parser.addoption(
        "--cleanup",
        action="store_true",
        default=False,
        help="Clean up resources (queues, fleets, associations) after tests",
    )
    parser.addoption(
        "--farm-id",
        action="store",
        default=None,
        help="Use a specific farm ID instead of reading from deadline config",
    )
    parser.addoption(
        "--queue-id",
        action="store",
        default=None,
        help="Use a specific queue ID instead of creating/reusing a test queue",
    )
    parser.addoption(
        "--no-cancel",
        action="store_true",
        default=False,
        help="Don't cancel the job after it reaches READY state",
    )
    parser.addoption(
        "--conda-channel",
        action="store",
        default=None,
        help="Override the CondaChannels default in the render job template",
    )
    parser.addoption(
        "--render-offscreen",
        action="store_true",
        default=False,
        help="Use -RenderOffScreen instead of -nullrhi (requires GPU)",
    )
    parser.addoption(
        "--no-prerun-checks",
        action="store_true",
        default=False,
        help=(
            "Skip all session-start (pre-run) validation checks. Use on hosts "
            "where the checks produce known false positives (e.g. a host with "
            "a legitimate production deadline-worker-agent service running)."
        ),
    )


def _record_leftover(
    proc_info: Dict[str, Any], cmdline_display: str, category: str
) -> Dict[str, Any]:
    return {
        "pid": proc_info["pid"],
        # psutil sets unreadable attrs to None (the key is present), so
        # .get(default) doesn't fall back — use `or` instead.
        "name": proc_info.get("name") or "unknown",
        "cmdline_short": cmdline_display,
        "category": category,
    }


def _categorize_process(
    name_lower: str, cmdline_list: List[str], cmdline_unreadable: bool
) -> Optional[str]:
    """Return the leftover category for a process, or None if it doesn't match."""
    # Worker agent: name match is reliable enough to flag without cmdline,
    # so a worker owned by another user (LOCAL_SYSTEM, etc.) is still caught.
    if name_lower in ("deadline-worker-agent.exe", "deadline-worker-agent"):
        return "deadline-worker-agent"

    if name_lower in ("unrealeditor-cmd.exe", "unrealeditor-cmd"):
        # Distinguish a worker-launched UE from a developer's manual UE
        # via the OpenJD session-temp path layout. Without cmdline we
        # can't apply the guard, so we skip rather than risk a false flag.
        if cmdline_unreadable:
            return None
        for arg in cmdline_list[1:]:
            arg_lower = arg.lower()
            # "openjd/" / "openjd\\" not just "openjd" — otherwise an
            # unrelated path containing "openjdk" would false-flag.
            if "openjd/" in arg_lower or "openjd\\" in arg_lower or "session-" in arg_lower:
                return "UnrealEditor-Cmd (worker session)"
        return None

    # Python process: name "python" alone is too generic; require an
    # explicit module/path match in the args.
    if cmdline_unreadable:
        return None
    is_python = name_lower.startswith("python") or name_lower in ("py.exe", "py")
    if is_python:
        for arg in cmdline_list[1:]:
            arg_lower = arg.lower()
            if (
                "deadline.unreal_adaptor" in arg_lower
                or "/unreal_adaptor/" in arg_lower
                or "\\unreal_adaptor\\" in arg_lower
            ):
                return "UnrealAdaptor"

    return None


def _find_leftover_processes() -> List[Dict[str, Any]]:
    """Iterate running processes and return records for any matching a
    leftover category (see _categorize_process)."""
    leftover: List[Dict[str, Any]] = []

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline")
            cmdline_unreadable = cmdline is None
            cmdline_list = cmdline or []
            if cmdline_unreadable:
                cmdline_display = "<cmdline unreadable; insufficient privileges>"
            elif not cmdline_list:
                cmdline_display = "<no cmdline>"
            else:
                cmdline_display = " ".join(cmdline_list)[:160]
            name_lower = (proc.info.get("name") or "").lower()

            category = _categorize_process(name_lower, cmdline_list, cmdline_unreadable)
            if category is not None:
                leftover.append(_record_leftover(proc.info, cmdline_display, category))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return leftover


def pytest_sessionstart(session) -> None:
    """Abort the E2E session if a UE editor, Unreal adaptor, or
    deadline-worker-agent is already running on this host. Such processes
    hold file locks, occupy ports, and (for the worker-agent) can pick up
    jobs the new run is trying to submit.

    Detection only — the hook never terminates anything. Killing a
    production deadline-worker-agent on a CMF host is too costly an
    accident to risk for the convenience of automated cleanup.
    """
    if session.config.getoption("--no-prerun-checks"):
        logger.info("--no-prerun-checks passed; skipping pre-run validation")
        return

    leftover = _find_leftover_processes()
    if not leftover:
        logger.info("No conflicting processes found")
        return

    msg_lines = [
        "",
        "=" * 70,
        "ABORTING: A UE editor, Unreal adaptor, or deadline-worker-agent is",
        "already running on this host. The E2E suite cannot run safely while",
        "any of these processes are active.",
        "",
        "Detected:",
        "",
    ]
    for proc_info in leftover:
        msg_lines.append(
            f"  [{proc_info['category']}] PID {proc_info['pid']} - {proc_info['name']}"
        )
        msg_lines.append(f"    {proc_info['cmdline_short']}")
        msg_lines.append("")

    msg_lines.append("To resolve, either:")
    msg_lines.append("  Stop these processes, then re-run the suite:")
    msg_lines.append("    - Task Manager (Ctrl+Shift+Esc): find by PID -> End Task")
    msg_lines.append("    - Or, in an elevated shell:  taskkill /PID <pid> /F")
    msg_lines.append("    - For a running worker service:  net stop DeadlineWorker")
    msg_lines.append("  Or re-run with --no-prerun-checks to bypass this check.")
    msg_lines.append("=" * 70)

    full_msg = "\n".join(msg_lines)
    logger.error(full_msg)
    # returncode=3 = pytest "internal error / setup failure".
    pytest.exit(full_msg, returncode=3)


def get_source_root() -> str:
    """
    Return the path of the root of the deadline-cloud-for-unreal-engine source.

    Assumes it's 2 folders up from the directory this file lives in.

    Returns:
        The absolute path to the repository root directory
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    root_dir = os.path.dirname(parent_dir)
    return root_dir


def get_build_script_args() -> List[str]:
    """
    Return the arguments to pass to the build script for a test installation.

    Returns:
        List of command line arguments for the build script
    """
    return ["--install", "--test", "--worker"]


def add_content_plugins_to_project(project_path: str, plugins: List[str], enabled: bool) -> None:
    """
    Add the provided list of content plugins to the uproject at the given project_path.

    Args:
        project_path: Path to .uproject file to add plugins to
        plugins: List of string names of content plugins to add to the project
        enabled: Whether to enable or disable the plugins
    """
    for plugin_name in plugins:
        create_minimal_plugin_structure(
            project_path, plugin_name, enabled, friendly_name=plugin_name
        )


def create_minimal_plugin_structure(
    project_path: str,
    plugin_name: str,
    enabled: bool,
    friendly_name: Optional[str] = None,
    description: str = "Auto-generated plugin",
) -> None:
    plugins_root = os.path.join(project_path, "Plugins")
    plugin_root = os.path.join(plugins_root, plugin_name)
    content_dir = os.path.join(plugin_root, "Content")
    resources_dir = os.path.join(plugin_root, "Resources")

    os.makedirs(plugins_root, exist_ok=True)
    os.makedirs(plugin_root, exist_ok=True)
    os.makedirs(content_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)

    uplugin = {
        "FileVersion": 3,
        "Version": 1,
        "VersionName": "1.0",
        "FriendlyName": friendly_name,
        "Description": description,
        "Category": "Content",
        "CreatedBy": "Auto Script",
        "CreatedByURL": "",
        "DocsURL": "",
        "MarketplaceURL": "",
        "SupportURL": "",
        "CanContainContent": True,
        "IsBetaVersion": False,
        "Installed": False,
        "EnabledByDefault": enabled,
        "Modules": [],
        "Plugins": [],
    }

    uplugin_path = os.path.join(plugin_root, f"{plugin_name}.uplugin")
    with open(uplugin_path, "w", encoding="utf-8") as f:
        json.dump(uplugin, f, indent=2)


def add_plugins_to_project(project_path: str, plugins: List[str], enabled: bool) -> None:
    """
    Add the provided list of plugins to the uproject at the given project_path.

    Args:
        project_path: Path to .uproject file to add plugins to
        plugins: List of string names of plugins to add to the project
        enabled: Whether to enable or disable the plugins
    """
    # Read the current .uproject file
    with open(project_path, "r") as f:
        project_data = json.load(f)

    # Make sure Plugins list exists
    if "Plugins" not in project_data:
        project_data["Plugins"] = []

    # Add each plugin if not already present
    for plugin_name in plugins:
        plugin_entry = {"Name": plugin_name, "Enabled": enabled}
        if plugin_entry not in project_data["Plugins"]:
            project_data["Plugins"].append(plugin_entry)

    # Write back the modified file
    with open(project_path, "w") as f:
        json.dump(project_data, f, indent=2)


@pytest.fixture(scope="session")
def iam_client(session: boto3.Session, region: str) -> BaseClient:
    """
    Fixture that provides an IAM client.

    Args:
        session: The boto3 session
        region: The AWS region

    Returns:
        An IAM client
    """
    return session.client("iam", region_name=region)


@pytest.fixture(scope="session")
def sts_client(session: boto3.Session, region: str) -> BaseClient:
    """
    Fixture that provides an STS client.

    Args:
        session: The boto3 session
        region: The AWS region

    Returns:
        An STS client
    """
    return session.client("sts", region_name=region)


@pytest.fixture(scope="session")
def queue_role_arn(iam_client: BaseClient, sts_client: BaseClient) -> str:
    """
    Fixture that provides an IAM role ARN for Deadline Cloud queues.

    First tries to get the test role, then tries to create it if it doesn't exist,
    and falls back to the current execution role if neither is possible.

    Args:
        iam_client: The IAM client
        sts_client: The STS client

    Returns:
        The ARN of the IAM role to use for queues
    """
    # First try to get the test role
    try:
        response = iam_client.get_role(RoleName=DEADLINE_UNREAL_QUEUE_TEST_ROLE)
        return response["Role"]["Arn"]
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")

        # If not found, try to create it
        if error_code == "NoSuchEntity":
            try:
                logger.info(f"Creating IAM role: {DEADLINE_UNREAL_QUEUE_TEST_ROLE}")

                role_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "credentials.deadline.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }

                # Create the role
                create_role_response = iam_client.create_role(
                    RoleName=DEADLINE_UNREAL_QUEUE_TEST_ROLE,
                    Description=DEADLINE_UNREAL_QUEUE_TEST_ROLE,
                    AssumeRolePolicyDocument=json.dumps(role_policy),
                )

                # Create inline policy
                policy_document = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "logs:GetLogEvents",
                            ],
                            "Resource": "arn:aws:logs:*:*:*:/aws/deadline/*",
                        },
                        {
                            # For synchronizing job attachments
                            "Effect": "Allow",
                            "Action": [
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:ListBucket",
                                "s3:GetBucketLocation",
                            ],
                            "Resource": [
                                "arn:aws:s3:::deadline-unreal-test-*",
                                "arn:aws:s3:::deadline-unreal-test-*/*",  # For operations on objects within the bucket
                            ],
                        },
                    ],
                }

                iam_client.put_role_policy(
                    RoleName=DEADLINE_UNREAL_QUEUE_TEST_ROLE,
                    PolicyName=f"{DEADLINE_UNREAL_QUEUE_TEST_ROLE}Policy",
                    PolicyDocument=json.dumps(policy_document),
                )

                # IAM changes can take time to propagate
                time.sleep(20)

                return create_role_response["Role"]["Arn"]
            except botocore.exceptions.ClientError:
                # If we can't create the role either, fall back to current role
                logger.warning("Could not create test role, falling back to current execution role")

        # For AccessDenied or any other error after failed creation attempts, try current role
        logger.info("No permission to manage IAM roles, using current execution role")

        # Get the current execution role using STS
        caller_identity = sts_client.get_caller_identity()
        current_role_arn = caller_identity.get("Arn")

        # Log appropriate message based on whether we're using a role or user
        if ":assumed-role/" in current_role_arn:
            logger.info(f"Using current execution role: {current_role_arn}")
        else:
            logger.warning(
                "Not running as an IAM role, tests may fail if permissions are insufficient"
            )

        return current_role_arn


# Terminal non-success states for a Deadline Cloud job (per the GetJob API).
# Default failure_states for wait_for_job_state(). Update if the API gains new
# terminal failure states.
TERMINAL_FAILURE_STATES: Tuple[str, ...] = ("FAILED", "CANCELED", "NOT_COMPATIBLE")


def wait_for_job_state(
    deadline_client: BaseClient,
    farm_id: str,
    job_id: str,
    queue_id: str,
    expected_states: Optional[List[str]] = None,
    failure_states: Optional[List[str]] = None,
    max_wait_time: int = 600,
    wait_interval: int = 10,
    status_interval: int = 5,
) -> Tuple[bool, Optional[str], str]:
    """
    Monitor a Deadline Cloud job until it reaches an expected state, hits a
    failure state, or times out.

    Args:
        deadline_client: Boto3 Deadline client
        farm_id: The farm ID containing the job
        job_id: The job ID to monitor
        queue_id: The queue ID containing the job
        expected_states: List of states to consider as successful (e.g. ["READY", "SUCCEEDED"])
                        If None, defaults to ["SUCCEEDED"]
        failure_states: Terminal states that fail the wait immediately. None
                        defaults to TERMINAL_FAILURE_STATES; [] disables fail-fast.
        max_wait_time: Maximum time to wait in seconds (default: 600)
        wait_interval: Time between status checks in seconds (default: 10)
        status_interval: Time between status output messages in seconds (default: 5)

    Returns:
        tuple: (success, status, message)
            - success: Boolean indicating if job reached expected state
            - status: Final job status
            - message: Descriptive message about the outcome
    """
    # Default expected states if not provided
    if expected_states is None:
        expected_states = ["SUCCEEDED"]

    if failure_states is None:
        effective_failure_states: List[str] = list(TERMINAL_FAILURE_STATES)
    else:
        effective_failure_states = list(failure_states)

    # Drop states the caller is explicitly waiting for (e.g. a test that
    # cancels its own job and waits for CANCELED).
    excluded = [s for s in effective_failure_states if s in expected_states]
    if excluded:
        logger.debug(f"Excluded {excluded} from failure_states because they are in expected_states")
    effective_failure_states = [s for s in effective_failure_states if s not in expected_states]

    logger.info(
        f"Monitoring job {job_id} in farm {farm_id}, queue {queue_id} for state(s) {expected_states}"
    )

    elapsed_time = 0
    status = None
    last_status_output = 0
    last_logged_status = None

    while elapsed_time < max_wait_time:
        try:
            # Get job status
            job_response = deadline_client.get_job(farmId=farm_id, queueId=queue_id, jobId=job_id)

            # Debug: Print the full response structure at the beginning
            if elapsed_time == 0:
                logger.debug(
                    f"Initial job response structure: {json.dumps(job_response, default=str)}"
                )

            # Extract status - first try taskRunStatus, then fall back to status
            status = job_response.get("taskRunStatus")
            if status is None:
                status = job_response.get("status")

            # Output status at regular intervals
            if elapsed_time - last_status_output >= status_interval:
                # Get task information if available from taskRunStatusCounts
                tasks_info = ""
                if "taskRunStatusCounts" in job_response:
                    status_counts = job_response["taskRunStatusCounts"]
                    total_tasks = sum(count for count in status_counts.values())
                    completed_tasks = sum(
                        status_counts.get(status, 0)
                        for status in ["SUCCEEDED", "FAILED", "CANCELED"]
                    )
                    tasks_info = f" - Tasks: {completed_tasks}/{total_tasks} completed"

                # If status is still None, log the response keys to help debug
                if status is None:
                    logger.info(
                        f"Job {job_id} status: Unknown - Response keys: {list(job_response.keys())} (Elapsed: {elapsed_time}s)"
                    )
                    logger.debug(f"Full response: {json.dumps(job_response, default=str)}")
                else:
                    logger.info(
                        f"Job {job_id} status: {status}{tasks_info} (Elapsed: {elapsed_time}s)"
                    )

                last_status_output = elapsed_time
                last_logged_status = status
            # Only log status changes to avoid duplicate log entries
            elif status != last_logged_status:
                logger.info(f"Job {job_id} status changed: {status}")
                last_logged_status = status

            # Fail-fast on a terminal failure before checking expected, so we
            # don't wait out max_wait_time on a job that's already failed.
            if status in effective_failure_states:
                error_msg = f"Job {job_id} reached failure state: {status}"
                logger.error(error_msg)
                return False, status, error_msg

            if status in expected_states:
                logger.info(f"Job {job_id} reached expected state: {status}")
                return True, status, f"Job {job_id} reached expected state: {status}"

            # Wait before checking again
            time.sleep(wait_interval)
            elapsed_time += wait_interval

        except Exception as e:
            error_msg = f"Error checking job status: {str(e)}"
            logger.error(error_msg)
            return False, "ERROR", error_msg

    timeout_msg = f"Timeout waiting for job {job_id} to reach state(s) {expected_states}. Last status: {status}"
    logger.warning(timeout_msg)
    return False, status, timeout_msg


def extract_job_info_from_test_output(
    output_lines: List[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract job ID, farm ID, and queue ID from test output lines.

    Args:
        output_lines: List of output lines from the test

    Returns:
        tuple: (job_id, farm_id, queue_id) - Any may be None if not found
    """
    job_id = None
    farm_id = None
    queue_id = None

    # Use sets to track which IDs we've already logged to avoid duplicates
    logged_ids = set()

    for line in output_lines:
        # Look for the job ID in the log message
        job_id_match = re.search(
            r"Found job creation log message with job ID: (job-[a-zA-Z0-9]+)", line
        )
        if job_id_match:
            job_id = job_id_match.group(1)
            if job_id not in logged_ids:
                logger.info(f"Extracted job ID: {job_id}")
                logged_ids.add(job_id)

        # Look for farm ID in the output
        farm_id_match = re.search(r"farm_id=([a-zA-Z0-9-]+)", line)
        if farm_id_match:
            farm_id = farm_id_match.group(1)
            if farm_id not in logged_ids:
                logger.info(f"Extracted farm ID: {farm_id}")
                logged_ids.add(farm_id)

        # Look for queue ID in the output
        queue_id_match = re.search(r"queue_id=([a-zA-Z0-9-]+)", line)
        if queue_id_match:
            queue_id = queue_id_match.group(1)
            if queue_id not in logged_ids:
                logger.info(f"Extracted queue ID: {queue_id}")
                logged_ids.add(queue_id)

    return job_id, farm_id, queue_id


@pytest.fixture
def run_unreal_test(request, reusable_farm_id, reusable_queue_id) -> Callable:
    """
    Fixture that provides a function to run Unreal Engine automation tests.

    Args:
        request: The pytest request object
        reusable_farm_id: The farm ID
        reusable_queue_id: The queue ID

    Returns:
        A callable function that runs Unreal Engine automation tests
    """

    def _run_unreal_test(
        test_path: str, uproject_file: str, deadlineargs: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Runs an Unreal Engine automation test and determines success or failure by analyzing output patterns
        rather than relying on the process return code.

        Args:
            test_path: Automation test path (e.g. "DeadlineCloud.Integration.CreateJob")
            uproject_file: Path to the uproject file
            deadlineargs: Optional arguments to pass to Deadline, defaults to basic settings if None

        Returns:
            Tuple of (success, output_lines) where success is a boolean indicating whether the test passed,
            and output_lines is a list of all output lines from the test
        """
        if deadlineargs is None:
            deadlineargs = "-NoLoadingScreen -FixedSeed -log -Unattended -MRQInstance -deterministicaudio -audiomixer"

        logger.info(f"Running unreal test with farm {reusable_farm_id} queue {reusable_queue_id}")

        # Populate the Deadline config so the plugin's startup precache warms the
        # credential/S3 session; -testparams alone does not write these defaults.
        config.set_setting("defaults.farm_id", reusable_farm_id)
        config.set_setting("defaults.queue_id", reusable_queue_id)

        test_params_str = f"-testparams=farm_id={reusable_farm_id};queue_id={reusable_queue_id}"

        engine_root = find_engine_root(request.config.getoption("--ueversion"))

        unrealeditor_cmd_path = os.path.join(engine_root, "Engine", "Binaries", "Win64")
        rhi_flag = (
            "-RenderOffScreen" if request.config.getoption("--render-offscreen") else "-nullrhi"
        )
        test_args = [
            os.path.join(unrealeditor_cmd_path, "UnrealEditor-Cmd.exe"),
            uproject_file,
            f"-ExecCmds=Automation RunTests {test_path}",
            "-stdout",
            "-unattended",
            rhi_flag,
            "-nosplash",
            "-nosound",
            "-nocontentbrowser",
            "-nopause",
            "-testexit=Automation Test Queue Empty",
            f"-deadlineargs={deadlineargs}",
        ]

        # Add test params if provided
        if test_params_str:
            test_args.append(test_params_str)

        logger.info(f"Running Unreal test: {test_path}")
        logger.debug(f"Calling subprocess with args {test_args}")

        # Start the process and capture output while displaying it
        process = subprocess.Popen(
            test_args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,  # Line buffered
        )

        # Collect all output
        full_output = []

        # Process and display output in real-time
        if process.stdout:
            for line in process.stdout:
                # Print to console in real-time (keeping this for immediate feedback)
                sys.stdout.write(line)
                sys.stdout.flush()
                # Store for later analysis
                full_output.append(line)
        else:
            logger.warning("Process stdout is None, cannot capture output")

        # Wait for process to complete and get return code
        return_code = process.wait()

        # Join all output lines
        output_text = "".join(full_output)

        # Check if the process executed successfully
        success = True
        if return_code != 0:
            logger.error(f"Unreal Editor process failed with code {return_code}")
            success = False

        # Check for test failure patterns in the output
        failure_pattern = f"Result={{Fail}} Name={{[^}}]*}} Path={{{test_path}}}"
        if re.search(failure_pattern, output_text):
            logger.error(f"Test {test_path} failed")
            success = False

        # Check for success pattern
        success_pattern = f"Result={{Success}} Name={{[^}}]*}} Path={{{test_path}}}"
        if re.search(success_pattern, output_text):
            logger.info(f"Test {test_path} passed")
            success = True
        else:
            # If neither pattern is found, something went wrong
            if not re.search(failure_pattern, output_text):
                logger.warning(f"Could not determine test result for {test_path}")
                success = False

        # Emit full UE output on failure; real-time stdout is swallowed by pytest-xdist capture
        if not success:
            logger.error(
                "Full Unreal Engine output for failed test %s:\n%s", test_path, output_text
            )

        # Return both success status and output lines
        return success, full_output

    return _run_unreal_test


@pytest.fixture(scope="session")
def build_plugin(request) -> None:
    """
    Fixture to run the scripts/build_plugin.py script at most once per test session.

    Guarantees the latest version of the code has been built and installed.

    Args:
        request: The pytest request object
    """
    if request.config.getoption("--nobuild"):
        logger.info("Skipping build_plugin")
    else:
        # build_plugin.py lives in the scripts subfolder relative to the root of the repository
        script_path = os.path.join(get_source_root(), "scripts", "build_plugin.py")
        if not os.path.exists(script_path):
            pytest.fail(f"Could not find build_plugin.py at {script_path}")

        build_args = ["python", script_path]
        build_args.extend(get_build_script_args())

        passthrough_args = ["--ueversion"]

        for arg in passthrough_args:
            logger.debug(f"Checking arg {arg}")
            if request.config.getoption(arg):
                logger.debug(f"Found arg {arg}: {request.config.getoption(arg)}")
                build_args.append(
                    f"{arg}={request.config.getoption(arg)}" if arg.startswith("--") else arg
                )
            else:
                logger.debug(f"Arg {arg} not present")

        # Run the script and capture the output
        result = subprocess.run(build_args, text=True)
        assert result.returncode == 0


@pytest.fixture(scope="session", autouse=True)
def apply_conda_channel_override(request) -> Generator[None, None, None]:
    """Override conda channel for render jobs via environment variable.

    Sets DEADLINE_CONDA_CHANNELS env var which the plugin reads at submission time.
    Only sets when --conda-channel is explicitly passed. Restores the prior value
    (or unsets it) at session teardown so the env doesn't leak across sessions.
    """
    conda_channel = request.config.getoption("--conda-channel")
    if not conda_channel:
        yield
        return

    prior = os.environ.get("DEADLINE_CONDA_CHANNELS")
    os.environ["DEADLINE_CONDA_CHANNELS"] = conda_channel
    logger.info(f"Set DEADLINE_CONDA_CHANNELS={conda_channel}")
    try:
        yield
    finally:
        if prior is None:
            os.environ.pop("DEADLINE_CONDA_CHANNELS", None)
        else:
            os.environ["DEADLINE_CONDA_CHANNELS"] = prior


@pytest.fixture(scope="session")
def create_readonly_test_project(request) -> Generator[Tuple[str, str], None, None]:
    """
    Create a test Unreal Engine project for testing.

    Creates a copy of a template project and adds required plugins.

    Args:
        request: The pytest request object

    Yields:
        Tuple containing (project_directory_path, project_file_path)
    """
    project_base = os.path.expanduser("~/Documents/UnrealProjects/TestProjects")
    os.makedirs(project_base, exist_ok=True)

    # Create a directory with a unique name under the project base folder
    # Using a default temporary directory will cause Unreal build failures
    temp_dir = tempfile.TemporaryDirectory(dir=project_base).name
    logger.info(f"Created project folder: {temp_dir}")

    engine_root = find_engine_root(request.config.getoption("--ueversion"))
    # Source path for the template
    source_path = os.path.join(engine_root, r"Templates\TP_DMXBP")
    if not os.path.exists(source_path):
        pytest.fail(f"Could not find source template at {source_path}")

    # Destination will be temp_dir/TP_DMXBP
    dest_path = os.path.abspath(os.path.join(temp_dir, "TP_DMXBP"))

    # Recursively copy the directory
    shutil.copytree(source_path, dest_path)
    logger.info(f"Created project dir {dest_path}")

    # Add our plugins
    project_path = os.path.join(dest_path, "TP_DMXBP.uproject")
    add_plugins_to_project(
        project_path,
        ["UnrealDeadlineCloudService", "MovieRenderPipeline"],
        True,
    )

    yield dest_path, project_path


@pytest.fixture(scope="session")
def session() -> boto3.Session:
    """
    Fixture that provides a boto3 session.

    Returns:
        A boto3 session
    """
    return boto3.Session()


@pytest.fixture(scope="session")
def s3_client(session: boto3.Session) -> BaseClient:
    """
    Fixture that provides an S3 client.

    Args:
        session: The boto3 session

    Returns:
        An S3 client
    """
    client = session.client("s3", region_name=TEST_TARGET_REGION)
    return client


@pytest.fixture(scope="session")
def reusable_s3_bucket(
    s3_client: BaseClient, sts_client: BaseClient, request
) -> Generator[str, None, None]:
    """
    Create or reuse an S3 bucket for job attachments.

    The bucket name follows the pattern 'deadline-unreal-test-{account_id}-{region}'.

    Args:
        s3_client: The S3 client
        sts_client: The STS client
        request: The pytest request object

    Yields:
        The name of the S3 bucket
    """
    # Get AWS account ID
    account_id = sts_client.get_caller_identity()["Account"]

    # Create bucket name with account ID and region to ensure uniqueness
    bucket_name = f"deadline-unreal-test-{account_id}-{TEST_TARGET_REGION}"

    # Check if bucket already exists
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info(f"✓ Found existing S3 bucket: {bucket_name}")
    except botocore.exceptions.ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "404" or error_code == "NoSuchBucket":
            # Bucket doesn't exist, create it
            logger.info(f"Creating new S3 bucket: {bucket_name}...")

            # Different create_bucket syntax based on region
            if TEST_TARGET_REGION == "us-east-1":
                s3_client.create_bucket(Bucket=bucket_name)
            else:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": TEST_TARGET_REGION},
                )

            # Add lifecycle policy to delete objects after 7 days
            lifecycle_config = {
                "Rules": [
                    {
                        "ID": "DeleteAfter7Days",
                        "Status": "Enabled",
                        "Expiration": {"Days": 7},
                        "Filter": {"Prefix": ""},
                    }
                ]
            }
            s3_client.put_bucket_lifecycle_configuration(
                Bucket=bucket_name, LifecycleConfiguration=lifecycle_config
            )

            logger.info(f"✓ Created new S3 bucket: {bucket_name} with 7-day lifecycle policy")
        else:
            # Some other error occurred
            raise

    yield bucket_name

    # Only clean up if --cleanup flag is provided
    if request.config.getoption("--cleanup"):
        try:
            # First delete all objects in the bucket
            logger.info(f"Cleaning up S3 bucket {bucket_name}...")

            # List and delete all objects
            paginator = s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket_name):
                if "Contents" in page:
                    objects = [{"Key": obj["Key"]} for obj in page["Contents"]]
                    if objects:
                        s3_client.delete_objects(Bucket=bucket_name, Delete={"Objects": objects})

            # Now delete the bucket
            s3_client.delete_bucket(Bucket=bucket_name)
            logger.info(f"✓ Successfully deleted S3 bucket {bucket_name}")
        except Exception as e:
            logger.warning(f"Exception during S3 bucket cleanup: {str(e)}")
    else:
        logger.info("Skipping S3 bucket cleanup (use --cleanup to clean up resources)")


@pytest.fixture(scope="session")
def deadline_client(session: boto3.Session) -> BaseClient:
    """
    Fixture that provides a Deadline Cloud client.

    Args:
        session: The boto3 session

    Returns:
        A Deadline Cloud client
    """
    endpoint_url = os.environ.get("DEADLINE_ENDPOINT", None)
    client = session.client("deadline", region_name=TEST_TARGET_REGION, endpoint_url=endpoint_url)
    logger.info(f"Created deadline client for region {TEST_TARGET_REGION}")
    return client


def create_fleet_util(
    deadline_client: BaseClient,
    worker_role_arn: str,
    wait_for_active: bool = True,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Helper method to create one Fleet.

    Args:
        deadline_client: The client used to call deadline API
        worker_role_arn: The ARN of the IAM role to use for the fleet
        wait_for_active: Whether to return the result until Fleet is in ACTIVE status
        **kwargs: Additional parameters to pass to the create_fleet API

    Returns:
        The response from the get_fleet API call
    """
    if "minWorkerCount" not in kwargs:
        kwargs["minWorkerCount"] = 0

    if "maxWorkerCount" not in kwargs:
        kwargs["maxWorkerCount"] = 5

    if "roleArn" not in kwargs:
        kwargs["roleArn"] = worker_role_arn

    if "configuration" not in kwargs:
        kwargs["configuration"] = DEFAULT_MIN_CMF_CONFIGURATION

    response = deadline_client.create_fleet(**kwargs)

    if wait_for_active:
        waiter = deadline_client.get_waiter("fleet_active")
        waiter.wait(farmId=kwargs["farmId"], fleetId=response["fleetId"])

    response = deadline_client.get_fleet(farmId=kwargs["farmId"], fleetId=response["fleetId"])
    return response


DEADLINE_UNREAL_TEST_FARM_NAME: str = "deadline-unreal-test-farm"


@pytest.fixture(scope="session")
def reusable_farm_id(request) -> Generator[str, None, None]:
    """
    Fixture that provides a farm ID.

    Uses --farm-id CLI option if provided, otherwise reads from deadline config.

    Yields:
        The farm ID to use for tests
    """
    farm_id = request.config.getoption("--farm-id")
    if farm_id:
        logger.info(f"Using farm_id {farm_id} from --farm-id option")
    else:
        farm_id = config.get_setting("defaults.farm_id")
        if farm_id:
            logger.info(f"Using farm_id {farm_id} from defaults.farm_id")
        else:
            raise Exception(
                "Please provide --farm-id or configure defaults.farm_id in deadline config"
            )

    yield farm_id


@pytest.fixture(scope="session")
def worker_role_arn(iam_client: BaseClient, sts_client: BaseClient, reusable_farm_id: str) -> str:
    """
    Fixture that provides an IAM role ARN for Deadline Cloud fleets.

    First tries to get the test role, then tries to create it if it doesn't exist,
    and falls back to the current execution role if neither is possible.

    Args:
        iam_client: The IAM client
        sts_client: The STS client
        reusable_farm_id: The farm ID to use for tests

    Returns:
        The ARN of the IAM role to use for fleets
    """
    try:
        response = iam_client.get_role(RoleName=DEADLINE_UNREAL_FLEET_TEST_ROLE)
        return response["Role"]["Arn"]
    except botocore.exceptions.ClientError:

        role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "credentials.deadline.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }

        try:
            # Create the role
            logger.info(f"Creating IAM role: {DEADLINE_UNREAL_FLEET_TEST_ROLE}")
            create_role_response = iam_client.create_role(
                RoleName=DEADLINE_UNREAL_FLEET_TEST_ROLE,
                Description=DEADLINE_UNREAL_FLEET_TEST_ROLE,
                AssumeRolePolicyDocument=json.dumps(role_policy),
            )

            # Create inline policy
            policy_document = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "logs:GetLogEvents",
                        ],
                        "Resource": "arn:aws:logs:*:*:*:/aws/deadline/*",
                    },
                    {
                        # For synchronizing job attachments
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:ListBucket",
                            "s3:GetBucketLocation",
                        ],
                        "Resource": [
                            "arn:aws:s3:::deadline-unreal-test-*",
                            "arn:aws:s3:::deadline-unreal-test-*/*",  # For operations on objects within the bucket
                        ],
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "deadline:AssumeFleetRoleForWorker",
                            "deadline:UpdateWorker",
                            "deadline:UpdateWorkerSchedule",
                            "deadline:BatchGetJobEntity",
                            "deadline:AssumeQueueRoleForWorker",
                        ],
                        "Resource": "*",
                    },
                    {
                        "Sid": "CreateLogStream",
                        "Effect": "Allow",
                        "Action": ["logs:CreateLogStream"],
                        "Resource": f"arn:aws:logs:us-west-2:*:log-group:/aws/deadline/{reusable_farm_id}/*",
                        "Condition": {
                            "ForAnyValue:StringEquals": {
                                "aws:CalledVia": ["deadline.amazonaws.com"]
                            }
                        },
                    },
                    {
                        "Sid": "ManageLogEvents",
                        "Effect": "Allow",
                        "Action": ["logs:PutLogEvents", "logs:GetLogEvents"],
                        "Resource": f"arn:aws:logs:us-west-2:*:log-group:/aws/deadline/{reusable_farm_id}/*",
                    },
                ],
            }

            iam_client.put_role_policy(
                RoleName=DEADLINE_UNREAL_FLEET_TEST_ROLE,
                PolicyName=f"{DEADLINE_UNREAL_FLEET_TEST_ROLE}Policy",
                PolicyDocument=json.dumps(policy_document),
            )

            # IAM changes can take time to propagate
            time.sleep(20)

            return create_role_response["Role"]["Arn"]
        except botocore.exceptions.ClientError:
            # If we can't create the role either, fall back to current role
            logger.warning("Could not create test role, falling back to current execution role")

        # For AccessDenied or any other error after failed creation attempts, try current role
        logger.info("No permission to manage IAM roles, using current execution role")

        # Get the current execution role using STS
        caller_identity = sts_client.get_caller_identity()
        current_role_arn = caller_identity.get("Arn")

        # Log appropriate message based on whether we're using a role or user
        if ":assumed-role/" in current_role_arn:
            logger.info(f"Using current execution role: {current_role_arn}")
        else:
            logger.warning(
                "Not running as an IAM role, tests may fail if permissions are insufficient"
            )

        return current_role_arn


def delete_fleets_util(deadline_client: BaseClient, fleet_responses: List[Dict[str, Any]]) -> None:
    """
    Delete specific fleets created during testing with proper lifecycle management.

    Args:
        deadline_client: The Deadline Cloud client
        fleet_responses: List of fleet response objects containing fleetId and farmId
    """
    for response in fleet_responses:
        try:
            if "fleetId" in response and "farmId" in response:
                fleet_id = response["fleetId"]
                farm_id = response["farmId"]

                # First check if there are any queue-fleet associations
                try:
                    # List queue-fleet associations for this fleet
                    qfa_response = deadline_client.list_queue_fleet_associations(
                        farmId=farm_id, fleetId=fleet_id
                    )

                    # Update status and then delete any queue-fleet associations
                    for qfa in qfa_response.get("queueFleetAssociations", []):
                        queue_id = qfa.get("queueId")
                        current_status = qfa.get("status")
                        if queue_id:
                            try:
                                # Only update status if it's currently ACTIVE
                                if current_status == "ACTIVE":
                                    # First update the status to stop scheduling and cancel tasks
                                    deadline_client.update_queue_fleet_association(
                                        farmId=farm_id,
                                        queueId=queue_id,
                                        fleetId=fleet_id,
                                        status="STOP_SCHEDULING_AND_CANCEL_TASKS",
                                    )
                                    logger.info(
                                        f"Updated queue-fleet association status to STOP_SCHEDULING_AND_CANCEL_TASKS for queue {queue_id} and fleet {fleet_id}"
                                    )

                                    # Wait for the status change to take effect
                                    import time

                                    time.sleep(5)
                                else:
                                    logger.info(
                                        f"Skipping status update as current status is {current_status}, not ACTIVE"
                                    )

                                # Now delete the queue-fleet association
                                deadline_client.delete_queue_fleet_association(
                                    farmId=farm_id, queueId=queue_id, fleetId=fleet_id
                                )
                                logger.info(
                                    f"Deleted queue-fleet association between queue {queue_id} and fleet {fleet_id}"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Failed to manage queue-fleet association: {str(e)}"
                                )
                except Exception as e:
                    logger.warning(f"Error listing queue-fleet associations: {str(e)}")

                # Now delete the fleet
                deadline_client.delete_fleet(farmId=farm_id, fleetId=fleet_id)
                logger.info(f"Deleted fleet {fleet_id} from farm {farm_id}")
        except Exception as e:
            logger.warning(f"Exception occurred while deleting fleet: {str(e)}")


@pytest.fixture(scope="session")
def reusable_fleet_id(
    deadline_client: BaseClient,
    reusable_farm_id: str,
    worker_role_arn: str,
    request,
) -> Generator[str, None, None]:
    """
    Fixture that provides a fleet ID, creating one if it doesn't exist.

    Args:
        deadline_client: The Deadline Cloud client
        reusable_farm_id: The farm ID
        worker_role_arn: The ARN of the IAM role to use for the fleet
        request: The pytest request object

    Yields:
        The fleet ID
    """
    fleet_id = None
    fleet_response = None
    created_new = False

    env_fleet_id = os.environ.get("UNREAL_WORKER_FLEET_ID")
    if env_fleet_id:
        logger.info(f"Using fleet_id {env_fleet_id} from UNREAL_WORKER_FLEET_ID env var")
        yield env_fleet_id
        return

    # First check if a test fleet already exists
    try:
        # List fleets in the farm
        logger.info(f"Checking for existing test fleets in farm {reusable_farm_id}...")
        response = deadline_client.list_fleets(farmId=reusable_farm_id)

        # The API might return 'fleets' or 'items' depending on the version
        fleets = response.get("fleets", response.get("items", []))
        logger.info(f"Found {len(fleets)} fleets in farm {reusable_farm_id}")

        for fleet in fleets:
            # Check if this is our test fleet
            fleet_id = fleet.get("fleetId", "unknown")
            display_name = fleet.get("displayName", "unknown")

            if display_name == DEADLINE_UNREAL_TEST_FLEET_NAME:
                logger.info(f"✓ Found existing test fleet: {fleet_id} in farm {reusable_farm_id}")
                fleet_response = fleet
                break

        if not fleet_id or not fleet_response:
            logger.info(f"No existing test fleet found in farm {reusable_farm_id}")

            # Create a new fleet if none exists
            logger.info(f"Creating new test fleet in farm {reusable_farm_id}...")
            fleet_response = create_fleet_util(
                deadline_client,
                worker_role_arn,
                displayName=DEADLINE_UNREAL_TEST_FLEET_NAME,
                farmId=reusable_farm_id,
                configuration=DEFAULT_MIN_CMF_CONFIGURATION,
                maxWorkerCount=100,
            )
            fleet_id = fleet_response["fleetId"]
            created_new = True
            logger.info(f"✓ Created new test fleet: {fleet_id} in farm {reusable_farm_id}")

            # Wait for the fleet to be ready
            logger.info(f"Waiting for fleet {fleet_id} to become active...")
            time.sleep(30)
            logger.info(f"Fleet {fleet_id} should now be active")
    except Exception as e:
        logger.warning(f"Error checking for existing fleets: {str(e)}")
        logger.warning(f"Exception details: {type(e).__name__}")
        import traceback

        logger.warning(f"Traceback: {traceback.format_exc()}")
        raise

    # Yield the fleet ID for the test to use
    yield fleet_id

    # Only clean up if --cleanup flag is provided or if we created a new fleet
    if request.config.getoption("--cleanup"):
        logger.info(f"Cleaning up fleet {fleet_id} in farm {reusable_farm_id}")
        try:
            # If we didn't create a new fleet, we need to get the fleet details for delete_fleets_util
            if not created_new:
                fleet_response = deadline_client.get_fleet(
                    farmId=reusable_farm_id, fleetId=fleet_id
                )
            delete_fleets_util(deadline_client, [fleet_response])
            logger.info(f"✓ Successfully deleted fleet {fleet_id}")
        except Exception as e:
            logger.warning(f"Exception during fleet cleanup: {str(e)}")
    else:
        logger.info("Skipping fleet cleanup (use --cleanup to clean up resources)")


@pytest.fixture(scope="session")
def create_queue_helper(
    deadline_client: BaseClient, queue_role_arn: str, reusable_s3_bucket: str, request
) -> Generator[
    Callable[[str, Optional[str], Optional[Dict[str, Any]]], Dict[str, Any]], None, None
]:
    """
    Fixture that provides a function to create or reuse a queue.

    Args:
        deadline_client: The Deadline Cloud client
        queue_role_arn: The ARN of the IAM role to use for the queue
        reusable_s3_bucket: The S3 bucket to use for job attachments
        request: The pytest request object

    Yields:
        A callable function that creates or reuses a queue
    """
    queues: List[Tuple[str, str]] = []

    def find_existing_queue(farm_id: str) -> Optional[Dict[str, Any]]:
        """
        Find an existing test queue in the farm.

        Args:
            farm_id: The farm ID to search in

        Returns:
            The queue object if found, None otherwise
        """
        try:
            # List queues in the farm
            logger.info(f"Checking for existing test queues in farm {farm_id}...")
            response = deadline_client.list_queues(farmId=farm_id)
            for queue in response.get("queues", response.get("items", [])):
                # Check if this is our test queue
                if queue.get("displayName") == DEADLINE_UNREAL_TEST_QUEUE_NAME:
                    logger.info(
                        f"✓ Found existing test queue: {queue['queueId']} in farm {farm_id}"
                    )

                    # Cancel any pending jobs in the queue
                    logger.info(f"Checking for pending jobs in queue {queue['queueId']}...")
                    cancel_pending_jobs(deadline_client, farm_id, queue["queueId"])

                    return queue
            logger.info(f"No existing test queue found in farm {farm_id}")
            return None
        except Exception as e:
            logger.warning(f"Error checking for existing queues: {str(e)}")
            return None

    def create_queue_func(
        farm_id: str,
        queue_role_arn: Optional[str] = queue_role_arn,
        job_run_as_user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create or reuse a queue.

        Args:
            farm_id: The farm ID to create the queue in
            queue_role_arn: The ARN of the IAM role to use for the queue
            job_run_as_user: The job run as user configuration

        Returns:
            The queue object
        """
        # First check for an existing queue
        existing_queue = find_existing_queue(farm_id)
        if existing_queue:
            # Track this queue for cleanup (even though we didn't create it)
            queues.append((farm_id, existing_queue["queueId"]))
            logger.info(f"Reusing existing queue {existing_queue['queueId']} in farm {farm_id}")
            return existing_queue

        # Create a new queue if none exists
        logger.info(f"Creating new test queue in farm {farm_id}...")

        # Set up job attachment settings with the S3 bucket
        job_attachment_settings = {"s3BucketName": reusable_s3_bucket, "rootPrefix": "Deadline"}

        response = deadline_client.create_queue(
            farmId=farm_id,
            displayName=DEADLINE_UNREAL_TEST_QUEUE_NAME,
            roleArn=queue_role_arn,
            jobAttachmentSettings=job_attachment_settings,
            jobRunAsUser=job_run_as_user
            or {"posix": {"user": "", "group": ""}, "runAs": "WORKER_AGENT_USER"},
        )
        logger.info(f"✓ Created new test queue: {response['queueId']} in farm {farm_id}")
        queues.append((farm_id, response["queueId"]))
        return response

    yield create_queue_func

    # Only clean up if --cleanup flag is provided
    if request.config.getoption("--cleanup"):
        for queue in queues:
            farm_id, queue_id = queue
            try:
                logger.info(f"Cleaning up queue {queue_id} in farm {farm_id}")
                deadline_client.delete_queue(farmId=farm_id, queueId=queue_id)
                delete_farm_resource_log_group_util(farm_id=farm_id, resource_id=queue_id)
                logger.info(f"✓ Successfully deleted queue {queue_id}")
            except Exception as e:
                logger.warning(
                    f"Exception occurred while deleting Queue {farm_id} {queue_id}: {str(e)}"
                )
    else:
        logger.info("Skipping queue cleanup (use --cleanup to clean up resources)")


@pytest.fixture(scope="session")
def reusable_queue_id(
    reusable_farm_id: str,
    request,
) -> str:
    """
    Fixture that provides a queue ID.

    Uses --queue-id CLI option if provided, otherwise creates or reuses a test queue.

    Args:
        reusable_farm_id: The farm ID
        request: The pytest request object

    Returns:
        The queue ID
    """
    queue_id = request.config.getoption("--queue-id")
    if queue_id:
        logger.info(f"Using queue_id {queue_id} from --queue-id option")
        return queue_id
    # Lazy-import the create_queue_helper fixture only when needed
    create_queue_helper = request.getfixturevalue("create_queue_helper")
    queue = create_queue_helper(farm_id=reusable_farm_id)
    return queue["queueId"]


def stop_queue_fleet_associations_and_wait(
    deadline_client: BaseClient, farm_id: str, queue_id: str, fleet_id: str
) -> None:
    """
    Stop Queue Fleet Association. Attempts to transition from ACTIVE to STOP_SCHEDULING_AND_CANCEL_TASKS.
    Checks current status first and only updates if it's ACTIVE.

    Args:
        deadline_client: The Deadline Cloud client
        farm_id: The farm ID
        queue_id: The queue ID
        fleet_id: The fleet ID
    """
    try:
        # First get the current status
        try:
            response = deadline_client.get_queue_fleet_association(
                farmId=farm_id, queueId=queue_id, fleetId=fleet_id
            )
            current_status = response.get("status")
            logger.info(
                f"Current QFA status for farm {farm_id}, queue {queue_id}, fleet {fleet_id}: {current_status}"
            )

            # Only update if status is ACTIVE
            if current_status == "ACTIVE":
                # Update the status to stop scheduling and cancel tasks
                logger.info("Updating QFA status to STOP_SCHEDULING_AND_CANCEL_TASKS")
                deadline_client.update_queue_fleet_association(
                    farmId=farm_id,
                    queueId=queue_id,
                    fleetId=fleet_id,
                    status="STOP_SCHEDULING_AND_CANCEL_TASKS",
                )

                # Wait for the status change to take effect
                logger.info("Waiting for QFA to reach stopped state...")
                waiter = deadline_client.get_waiter("queue_fleet_association_stopped")
                waiter.wait(farmId=farm_id, queueId=queue_id, fleetId=fleet_id)

                # Get the final status
                response = deadline_client.get_queue_fleet_association(
                    farmId=farm_id, queueId=queue_id, fleetId=fleet_id
                )
                final_status = response.get("status")
                logger.info(f"QFA status after waiting: {final_status}")
            else:
                logger.info(
                    f"Skipping status update as current status is {current_status}, not ACTIVE"
                )
        except Exception as e:
            logger.error(f"Error getting or updating QFA: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"Failed to stop queue fleet association: {str(e)}")
        # Re-raise the exception so the caller knows something went wrong
        raise


@pytest.fixture(scope="session")
def deadline_worker_agent(
    request, reusable_farm_id: str, reusable_fleet_id: str
) -> Generator[Tuple[subprocess.Popen, str], None, None]:
    """
    Launch deadline-worker-agent as a subprocess using the farm ID and fleet ID from our tests.

    This fixture is session-scoped and ensures the worker agent is stopped during cleanup.

    Args:
        request: The pytest request object (used to read the --ueversion option)
        reusable_farm_id: The farm ID to use
        reusable_fleet_id: The fleet ID to use

    Yields:
        Tuple containing (worker_agent_process, log_file_path)
    """
    import subprocess
    import time
    import os
    import datetime
    import shutil

    # Check if deadline-worker-agent is available using 'where' or 'which'
    agent_path = None
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["where", "deadline-worker-agent"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            agent_path = result.stdout.strip().split("\n")[0]
        else:
            result = subprocess.run(
                ["which", "deadline-worker-agent"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            agent_path = result.stdout.strip()

        # Alternative check: just see if the executable exists in PATH
        if not agent_path:
            agent_path_maybe = shutil.which("deadline-worker-agent")
            if not agent_path_maybe:
                pytest.skip("deadline-worker-agent not found on PATH. Skipping worker agent tests.")
            agent_path = agent_path_maybe
    except (subprocess.SubprocessError, FileNotFoundError):
        pytest.skip("deadline-worker-agent not found on PATH. Skipping worker agent tests.")

    logger.info(
        f"Starting deadline-worker-agent with farm ID: {reusable_farm_id}, fleet ID: {reusable_fleet_id}"
    )
    logger.info(f"Using agent at: {agent_path}")

    # Create a log file for the worker agent
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(
        log_dir, f"worker-agent-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    )

    # Create persistence dir for worker agent state
    persistence_dir = os.path.join(os.getcwd(), "worker-agent-state")
    os.makedirs(persistence_dir, exist_ok=True)

    # Start the worker agent process
    cmd = [
        "deadline-worker-agent",
        "--farm-id",
        reusable_farm_id,
        "--fleet-id",
        reusable_fleet_id,
        "--structured-logs",
        "--run-jobs-as-agent-user",
        "--no-shutdown",
        "--logs-dir",
        log_dir,
        "--persistence-dir",
        persistence_dir,
    ]

    # Environment variables for the worker agent
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["TERM"] = "dumb"
    env["NO_COLOR"] = "1"

    # Add UE binaries to PATH so the adaptor can find UnrealEditor-Cmd.
    ue_bin_dir = os.path.join(
        find_engine_root(request.config.getoption("--ueversion")),
        "Engine",
        "Binaries",
        "Win64",
    )
    if os.path.isdir(ue_bin_dir):
        env["PATH"] = ue_bin_dir + os.pathsep + env.get("PATH", "")

    logger.info(f"Starting worker agent with command: {' '.join(cmd)}")
    logger.info(f"Worker agent logs will be written to: {log_file}")

    log_fh = open(log_file, "w")

    # Use different process creation flags based on platform
    if sys.platform == "win32":
        process = subprocess.Popen(
            cmd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdout=log_fh,
            stderr=log_fh,
            env=env,
            text=True,
        )
    else:
        process = subprocess.Popen(
            cmd,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            stdout=log_fh,
            stderr=log_fh,
            env=env,
            text=True,
        )

    # Give the worker agent time to start and register with the fleet
    for i in range(6):
        time.sleep(5)
        if process.poll() is not None:
            log_fh.flush()
            with open(log_file, "r") as f:
                log_content = f.read()
            pytest.fail(
                f"Worker agent exited during startup (exit code {process.returncode}):\n{log_content}"
            )
        logger.info(f"Worker agent startup check {i+1}/6 — still running (PID {process.pid})")

    # Final check
    if process.poll() is not None:
        log_fh.flush()
        with open(log_file, "r") as f:
            log_content = f.read()
        pytest.fail(f"Worker agent failed to start: exit code {process.returncode}\n{log_content}")

    logger.info(f"Worker agent started successfully with PID: {process.pid}")
    logger.info(f"To view worker agent logs, check: {log_file}")

    # Return the process and log file to the test
    yield process, log_file

    # Cleanup: terminate the worker agent process
    logger.info(f"Stopping deadline-worker-agent (PID: {process.pid})")

    try:
        if sys.platform == "win32":
            # On Windows, send Ctrl+C to the process group
            process.send_signal(signal.CTRL_C_EVENT)
            # Give it some time to shut down gracefully
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't respond to Ctrl+C
                process.terminate()
        else:
            # On Unix, use a more secure approach
            # First try SIGTERM for graceful shutdown
            process.send_signal(signal.SIGTERM)
            # Give it some time to shut down gracefully
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # If it doesn't respond to SIGTERM, try SIGINT (Ctrl+C equivalent)
                logger.warning("Process didn't respond to SIGTERM, sending SIGINT")
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # As a last resort, use SIGKILL
                    logger.warning("Process didn't respond to SIGINT, using SIGKILL")
                    process.kill()
    except Exception as e:
        logger.error(f"Error stopping worker agent: {str(e)}")
    finally:
        log_fh.close()

    logger.info("Worker agent stopped")


@pytest.fixture(scope="session")
def reusable_queue_fleet_association(
    deadline_client: BaseClient,
    reusable_farm_id: str,
    reusable_queue_id: str,
    reusable_fleet_id: str,
    request,
) -> Generator[Tuple[str, str, str], None, None]:
    """
    Fixture that provides a queue-fleet association, creating one if it doesn't exist.

    Args:
        deadline_client: The Deadline Cloud client
        reusable_farm_id: The farm ID
        reusable_queue_id: The queue ID
        reusable_fleet_id: The fleet ID
        request: The pytest request object

    Yields:
        Tuple containing (farm_id, queue_id, fleet_id)
    """

    # Check if association already exists
    try:
        logger.info(
            f"Checking if queue-fleet association exists between queue {reusable_queue_id} and fleet {reusable_fleet_id}..."
        )
        deadline_client.get_queue_fleet_association(
            farmId=reusable_farm_id, queueId=reusable_queue_id, fleetId=reusable_fleet_id
        )
        logger.info(
            f"✓ Found existing queue-fleet association between queue {reusable_queue_id} and fleet {reusable_fleet_id}"
        )
    except Exception:
        # Create new association if it doesn't exist
        logger.info(
            f"No existing queue-fleet association found. Creating new association between queue {reusable_queue_id} and fleet {reusable_fleet_id}..."
        )
        deadline_client.create_queue_fleet_association(
            farmId=reusable_farm_id, queueId=reusable_queue_id, fleetId=reusable_fleet_id
        )
        logger.info(
            f"✓ Created new queue-fleet association between queue {reusable_queue_id} and fleet {reusable_fleet_id}"
        )

    yield reusable_farm_id, reusable_queue_id, reusable_fleet_id

    # Only clean up if --cleanup flag is provided
    if request.config.getoption("--cleanup"):
        try:
            logger.info(
                f"Cleaning up queue-fleet association between queue {reusable_queue_id} and fleet {reusable_fleet_id}"
            )
            stop_queue_fleet_associations_and_wait(
                deadline_client=deadline_client,
                farm_id=reusable_farm_id,
                queue_id=reusable_queue_id,
                fleet_id=reusable_fleet_id,
            )

            deadline_client.delete_queue_fleet_association(
                farmId=reusable_farm_id, queueId=reusable_queue_id, fleetId=reusable_fleet_id
            )
            logger.info("✓ Successfully deleted queue-fleet association")
        except Exception as e:
            logger.warning(f"Exception during queue-fleet association cleanup: {str(e)}")
    else:
        logger.info(
            "Skipping queue-fleet association cleanup (use --cleanup to clean up resources)"
        )


def get_last_session_project_plugins(
    deadline_client: BaseClient, farm_id: str, queue_id: str, job_id: str
) -> List[str]:
    """
    Fetch the last session's project plugins used by a job by parsing its log events.

    Args:
        deadline_client: The Deadline Cloud client
        farm_id: The farm ID
        queue_id: The queue ID
        job_id: The job ID

    Returns:
        A sorted list of unique project plugin names used in the last session
    """
    try:
        sessions_response = deadline_client.list_sessions(
            farmId=farm_id,
            jobId=job_id,
            queueId=queue_id,
        )
        session_id = sessions_response["sessions"][0]["sessionId"]

        session_response = deadline_client.get_session(
            farmId=farm_id,
            jobId=job_id,
            queueId=queue_id,
            sessionId=session_id,
        )

        log_response = session_response["log"]

        # Get job details to find the log group and stream
        cwl_client = boto3.client("logs", TEST_TARGET_REGION)

        # Extract project plugins from the log events
        plugin_names = _extract_project_plugins_from_log_events(
            cwl_client,
            log_response["options"]["logGroupName"],
            log_response["options"]["logStreamName"],
        )
        return plugin_names

    except Exception as e:
        logger.warning(f"Error fetching job logs or extracting plugins: {str(e)}")
        return []


def _extract_project_plugins_from_log_events(logs_client, log_group, log_stream) -> List[str]:
    """
    Extract unique project plugin names from log events in the specified log group and stream.
    Args:
        logs_client: The CloudWatch Logs client
        log_group: The name of the log group
        log_stream: The name of the log stream

    Returns:
        A sorted list of unique project plugin names
    """
    plugin_names = set()
    pattern = re.compile(r"Mounting Project plugin\s+(?P<name>[^\s]+(?:\s+[^\s]+)*)\s*$")

    next_token = None
    while True:
        if next_token:
            resp = logs_client.get_log_events(
                logGroupName=log_group, logStreamName=log_stream, nextToken=next_token
            )
        else:
            resp = logs_client.get_log_events(logGroupName=log_group, logStreamName=log_stream)

        for ev in resp.get("events", []):
            msg = ev.get("message", "")
            for line in msg.splitlines():
                m = pattern.search(line)
                if m:
                    plugin_names.add(m.group("name"))

        new_token = resp.get("nextForwardToken")
        if not new_token or new_token == next_token:
            break
        next_token = new_token

    return sorted(plugin_names)
