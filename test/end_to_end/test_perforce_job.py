# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""End-to-end coverage for a directly submitted Unreal Perforce render job."""

from __future__ import annotations

import json
import logging
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

import deadline.client.config as deadline_config
import pytest
from deadline.client.api import create_job_from_job_bundle

from conftest import (
    TEST_TARGET_REGION,
    add_plugins_to_project,
    get_source_root,
    wait_for_job_state,
)
from scripts.build_plugin import find_engine_root

logger = logging.getLogger(__name__)

UE_VERSION_ENV = "DEADLINE_P4_E2E_UE_VERSION"
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_PERFORCE_E2E", "").lower() != "true",
    reason="Set RUN_PERFORCE_E2E=true to run the Perforce end-to-end test",
)

# The worker-agent fixture is session scoped and copies its environment when it
# starts. Promote test-specific values during collection so the worker sees them
# even when this test is not the first one to request the shared fixture.
for _test_name, _p4_name in (
    ("DEADLINE_P4_TEST_PORT", "P4PORT"),
    ("DEADLINE_P4_TEST_USER", "P4USER"),
    ("DEADLINE_P4_TEST_PASSWD", "P4PASSWD"),
):
    if os.environ.get(_test_name):
        os.environ[_p4_name] = os.environ[_test_name]
if os.environ.get("DEADLINE_P4_TEST_PASSWORD"):
    os.environ["P4PASSWD"] = os.environ["DEADLINE_P4_TEST_PASSWORD"]


@dataclass
class PerforceProject:
    p4: Any
    ue_version: str
    workspace_root: Path
    project_dir: Path
    project_file: Path
    client_name: str
    depot_prefix: str
    project_name: str
    output_leaf: str
    job_id: str = ""
    cleanup_safe: bool = True


def _p4_setting(suffix: str, fallback: str, default: str = "") -> str:
    return os.environ.get(f"DEADLINE_P4_TEST_{suffix}") or os.environ.get(fallback) or default


def _connect_perforce() -> Any:
    try:
        from P4 import P4
    except ImportError:
        pytest.fail("p4python is required for the Perforce end-to-end test")

    port = _p4_setting("PORT", "P4PORT")
    user = _p4_setting("USER", "P4USER")
    password = _p4_setting("PASSWD", "P4PASSWD") or os.environ.get("DEADLINE_P4_TEST_PASSWORD", "")
    if not port or not user:
        pytest.fail(
            "Set DEADLINE_P4_TEST_PORT and DEADLINE_P4_TEST_USER "
            "(or P4PORT and P4USER) to run this test"
        )

    p4 = P4()
    p4.port = port
    p4.user = user
    charset = _p4_setting("CHARSET", "P4CHARSET", "none")
    if charset and charset != "none":
        p4.charset = charset
    p4.connect()
    try:
        p4.run("trust", "-y")
    except Exception:
        # A non-SSL server does not require a trust record.
        pass
    if password:
        p4.password = password
        p4.run_login()
    return p4


def _remove_readonly(function: Any, path: str, _exc_info: Any) -> None:
    os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
    function(path)


def _remove_tree_with_retry(path: Path) -> None:
    for attempt in range(10):
        try:
            shutil.rmtree(path, onerror=_remove_readonly)
            return
        except OSError as exc:
            if attempt == 9:
                logger.warning("Could not remove worker root %s: %s", path, exc)
                return
            time.sleep(1)


def _mapped_clients(p4: Any, depot_prefix: str, seed_client: str) -> list[str]:
    clients = {seed_client}
    try:
        summaries = p4.run("clients", "-u", p4.user)
    except Exception as exc:
        logger.warning("Could not enumerate Perforce clients during cleanup: %s", exc)
        return sorted(clients)

    for summary in summaries:
        name = summary.get("client")
        if not name:
            continue
        try:
            spec = p4.fetch_client(name)
        except Exception:
            continue
        if any(depot_prefix in view for view in spec.get("View", [])):
            clients.add(name)
    return sorted(clients)


def _cleanup_pending_job_changes(project: PerforceProject) -> None:
    if not project.job_id:
        return

    markers = {
        f"DeadlineCloudRenderShelve/{project.job_id}",
        f"DeadlineCloudRenderAggregate/{project.job_id}",
    }
    try:
        changes = project.p4.run(
            "changes",
            "-s",
            "pending",
            "-u",
            project.p4.user,
            "-l",
        )
    except Exception as exc:
        logger.warning("Could not enumerate pending Perforce changes during cleanup: %s", exc)
        return

    original_client = project.p4.client
    try:
        for change in changes:
            if change.get("desc", "").partition("\n")[0].strip() not in markers:
                continue

            change_number = str(change["change"])
            project.p4.client = change.get("client") or original_client
            for command, operation in (
                (("revert", "-k", "-c", change_number, "//..."), "revert"),
                (("shelve", "-d", "-c", change_number), None),
                (("change", "-d", change_number), "delete"),
            ):
                try:
                    project.p4.run(*command)
                except Exception as exc:
                    # Aggregate changes do not necessarily contain shelves.
                    if operation:
                        logger.warning(
                            "Could not %s pending Perforce change %s: %s",
                            operation,
                            change_number,
                            exc,
                        )
    finally:
        project.p4.client = original_client


def _cleanup_perforce_project(project: PerforceProject) -> None:
    p4 = project.p4
    if not p4.connected():
        p4.connect()

    _cleanup_pending_job_changes(project)

    p4.client = project.client_name
    try:
        files = p4.run("files", f"{project.depot_prefix}/...")
    except Exception:
        files = []
    if files:
        p4.run("obliterate", "-y", f"{project.depot_prefix}/...")

    for client_name in _mapped_clients(p4, project.depot_prefix, project.client_name):
        p4.client = client_name
        try:
            p4.run("revert", "-k", "//...")
        except Exception:
            pass
        p4.client = ""
        try:
            p4.run("client", "-d", client_name)
        except Exception as exc:
            logger.warning("Could not delete Perforce client %s: %s", client_name, exc)

    p4.disconnect()
    shutil.rmtree(project.workspace_root, onerror=_remove_readonly)


@pytest.fixture
def perforce_test_project(request: pytest.FixtureRequest) -> Generator[PerforceProject, None, None]:
    if sys.platform != "win32":
        pytest.skip("The Unreal Perforce end-to-end test requires Windows")

    requested_version = request.config.getoption("--ueversion")
    if not requested_version:
        pytest.fail("--ueversion is required for the Unreal Perforce end-to-end test")
    ue_version = str(requested_version)

    p4 = _connect_perforce()
    depot = _p4_setting("DEPOT", "P4DEPOT", "depot").strip("/")
    prefix_root = _p4_setting("DEPOT_PREFIX", "P4DEPOTPREFIX", "deadline-unreal-e2e").strip("/")
    token = uuid.uuid4().hex
    depot_prefix = f"//{depot}/{prefix_root}/{token}"
    client_name = f"deadline_unreal_p4e2e_{token}"
    output_leaf = f"DeadlineP4E2E_{token[:12]}"
    worker_root = Path("C:/deadline/perforce-e2e") / token
    project_base = Path.home() / "Documents" / "UnrealProjects" / "TestProjects"
    project_base.mkdir(parents=True, exist_ok=True)
    workspace_root = Path(
        tempfile.mkdtemp(prefix="deadline-unreal-p4e2e-", dir=project_base)
    ).resolve()
    project_dir = workspace_root / "TP_DMXBP"
    template_dir = Path(find_engine_root(ue_version)) / "Templates" / "TP_DMXBP"
    if not template_dir.is_dir():
        pytest.fail(f"UE {ue_version} TP_DMXBP template was not found at {template_dir}")
    shutil.copytree(template_dir, project_dir)
    project_file = project_dir / "TP_DMXBP.uproject"
    add_plugins_to_project(
        str(project_file), ["UnrealDeadlineCloudService", "MovieRenderPipeline"], True
    )
    project_name = project_file.stem
    project = PerforceProject(
        p4=p4,
        ue_version=ue_version,
        workspace_root=workspace_root,
        project_dir=project_dir,
        project_file=project_file,
        client_name=client_name,
        depot_prefix=depot_prefix,
        project_name=project_name,
        output_leaf=output_leaf,
    )
    previous_environment = {
        key: os.environ.get(key)
        for key in (
            "P4PORT",
            "P4USER",
            "P4PASSWD",
            "P4CLIENT",
            "DEADLINE_P4_TEST_WORKER_ROOT",
        )
    }

    def finalize_project() -> None:
        for key, value in previous_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        if not project.cleanup_safe:
            logger.warning(
                "Skipping Perforce cleanup because the Deadline job did not reach "
                "a terminal state"
            )
            if project.p4.connected():
                project.p4.disconnect()
            return

        try:
            _cleanup_perforce_project(project)
        finally:
            if worker_root.exists():
                _remove_tree_with_retry(worker_root)

    request.addfinalizer(finalize_project)

    depots = {item.get("name") for item in p4.run_depots()}
    if depot not in depots:
        pytest.fail(f"Perforce depot {depot!r} does not exist; available depots: {depots}")

    spec = p4.fetch_client(client_name)
    spec["Client"] = client_name
    spec["Owner"] = p4.user
    spec["Host"] = ""
    spec["Root"] = str(workspace_root)
    spec["LineEnd"] = "local"
    spec["View"] = [f"{depot_prefix}/... //{client_name}/..."]
    p4.save_client(spec)
    p4.client = client_name

    source_control_settings = (
        project_dir / "Saved" / "Config" / "WindowsEditor" / "SourceControlSettings.ini"
    )
    source_control_settings.parent.mkdir(parents=True, exist_ok=True)
    source_control_settings.write_text(
        "[SourceControl.SourceControlSettings]\n"
        "Provider=Perforce\n\n"
        "[PerforceSourceControl.PerforceSourceControlSettings]\n"
        f"Port={p4.port}\n"
        f"UserName={p4.user}\n"
        f"Workspace={client_name}\n",
        encoding="utf-8",
    )

    p4.run("add", "-f", str(project_dir / "..."))
    p4.run("submit", "-d", f"Seed Deadline Cloud Perforce E2E project {project_name}")

    os.environ["P4PORT"] = p4.port
    os.environ["P4USER"] = p4.user
    os.environ["DEADLINE_P4_TEST_WORKER_ROOT"] = worker_root.as_posix()
    password = _p4_setting("PASSWD", "P4PASSWD") or os.environ.get("DEADLINE_P4_TEST_PASSWORD", "")
    if password:
        os.environ["P4PASSWD"] = password
    os.environ["P4CLIENT"] = client_name

    yield project


def _generate_perforce_bundle(project: PerforceProject) -> Path:
    source_root = Path(get_source_root())
    generator = source_root / "pipeline" / "generate_perforce_bundle.py"
    if not generator.is_file():
        pytest.fail(f"Perforce bundle generator was not found at {generator}")

    editor = (
        Path(find_engine_root(project.ue_version))
        / "Engine"
        / "Binaries"
        / "Win64"
        / "UnrealEditor-Cmd.exe"
    )
    if not editor.is_file():
        pytest.fail(f"UE {project.ue_version} editor was not found at {editor}")

    marker_fd, marker_path = tempfile.mkstemp(prefix="deadline-p4-bundle-", suffix=".txt")
    os.close(marker_fd)
    marker = Path(marker_path)
    marker.write_text("", encoding="utf-8")
    environment = os.environ.copy()
    environment.update(
        {
            "DEADLINE_CLOUD_INTEG_MARKER_FILE": str(marker),
            "DEADLINE_P4_E2E_RUN_ID": project.output_leaf,
            UE_VERSION_ENV: project.ue_version,
        }
    )
    command = [
        str(editor),
        str(project.project_file),
        f"-ExecutePythonScript={generator}",
        "-stdout",
        "-unattended",
        "-nullrhi",
        "-nosplash",
        "-nosound",
        "-nopause",
        '-deadlineargs="-NoLoadingScreen -FixedSeed -log -Unattended '
        '-MRQInstance -deterministicaudio -audiomixer"',
    ]
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=environment,
        timeout=600,
    )
    output = result.stdout or ""
    try:
        marker_value = marker.read_text(encoding="utf-8").strip()
    finally:
        marker.unlink(missing_ok=True)

    diagnostics = "\n".join(output.splitlines()[-200:])
    assert (
        result.returncode == 0
    ), f"Unreal bundle generation exited with {result.returncode}:\n{diagnostics}"
    assert marker_value, f"Unreal did not report a bundle path:\n{diagnostics}"
    assert not marker_value.startswith(
        "ERROR:"
    ), f"Perforce bundle generation failed: {marker_value}\n{diagnostics}"

    bundle = Path(marker_value)
    assert bundle.is_dir(), f"Generated bundle does not exist: {bundle}"
    for filename in ("template.yaml", "parameter_values.yaml", "asset_references.yaml"):
        assert (bundle / filename).is_file(), f"Bundle is missing {filename}: {bundle}"
    return bundle


def _submit_bundle(bundle: Path, project_dir: Path) -> str:
    job_id = create_job_from_job_bundle(
        job_bundle_dir=str(bundle),
        known_asset_paths=[str(project_dir)],
        interactive_confirmation_callback=lambda _message, _default: True,
        from_gui=False,
    )
    assert job_id, "Direct bundle submission did not return a job ID"
    return job_id


def _list_job_sessions(
    deadline_client: Any,
    farm_id: str,
    queue_id: str,
    job_id: str,
) -> list[dict[str, Any]]:
    pages = deadline_client.get_paginator("list_sessions").paginate(
        farmId=farm_id, queueId=queue_id, jobId=job_id
    )
    return [session for page in pages for session in page.get("sessions", [])]


def _local_worker_id() -> str:
    state_file = Path.cwd() / "worker-agent-state" / "worker.json"
    worker_id = json.loads(state_file.read_text(encoding="utf-8")).get("worker_id")
    assert worker_id, f"Worker agent did not persist its worker ID to {state_file}"
    return str(worker_id)


def _assert_job_ran_on_worker(
    deadline_client: Any,
    farm_id: str,
    queue_id: str,
    job_id: str,
    expected_fleet_id: str,
    expected_worker_id: str,
) -> None:
    sessions = _list_job_sessions(deadline_client, farm_id, queue_id, job_id)
    assert sessions, f"Job {job_id} did not create any worker sessions"

    unexpected = [
        {
            "sessionId": session.get("sessionId"),
            "fleetId": session.get("fleetId"),
            "workerId": session.get("workerId"),
        }
        for session in sessions
        if session.get("fleetId") != expected_fleet_id
        or session.get("workerId") != expected_worker_id
    ]
    assert not unexpected, (
        f"Job {job_id} ran outside CMF worker "
        f"{expected_fleet_id}/{expected_worker_id}: {unexpected}"
    )


def _wait_for_job_sessions_to_end(
    deadline_client: Any,
    farm_id: str,
    queue_id: str,
    job_id: str,
    max_wait_time: int = 300,
) -> bool:
    deadline = time.monotonic() + max_wait_time
    active: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        sessions = _list_job_sessions(deadline_client, farm_id, queue_id, job_id)
        active = [
            {
                "sessionId": session.get("sessionId"),
                "lifecycleStatus": session.get("lifecycleStatus"),
            }
            for session in sessions
            if session.get("lifecycleStatus") != "ENDED"
        ]
        if not active:
            return True
        time.sleep(5)

    logger.warning("Job %s still has active sessions after cancellation: %s", job_id, active)
    return False


def _cancel_job_and_wait(deadline_client: Any, farm_id: str, queue_id: str, job_id: str) -> bool:
    job = deadline_client.get_job(farmId=farm_id, queueId=queue_id, jobId=job_id)
    terminal_states = ["CANCELED", "FAILED", "NOT_COMPATIBLE", "SUCCEEDED"]
    if job.get("taskRunStatus") not in terminal_states:
        deadline_client.update_job(
            farmId=farm_id,
            queueId=queue_id,
            jobId=job_id,
            targetTaskRunStatus="CANCELED",
        )
        success, _status, message = wait_for_job_state(
            deadline_client=deadline_client,
            farm_id=farm_id,
            queue_id=queue_id,
            job_id=job_id,
            expected_states=terminal_states,
            failure_states=[],
            max_wait_time=300,
            wait_interval=5,
        )
        if not success:
            logger.warning("Job did not stop before Perforce cleanup: %s", message)
            return False

    return _wait_for_job_sessions_to_end(deadline_client, farm_id, queue_id, job_id)


def _assert_aggregate_outputs(project: PerforceProject, job_id: str) -> None:
    output_prefix = f"{project.depot_prefix}/{project.project_name}/Saved/{project.output_leaf}"
    changes = project.p4.run("changes", "-s", "submitted", "-l", f"{output_prefix}/...")
    marker = f"DeadlineCloudRenderAggregate/{job_id}"
    matches = [
        change for change in changes if change.get("desc", "").partition("\n")[0].strip() == marker
    ]
    assert len(matches) == 1, (
        f"Expected one submitted aggregate changelist with marker {marker!r}, "
        f"found {len(matches)}"
    )

    change_number = str(matches[0]["change"])
    description = project.p4.run("describe", "-s", change_number)
    assert description, f"Could not describe aggregate changelist {change_number}"
    depot_files = description[0].get("depotFile", [])
    if isinstance(depot_files, str):
        depot_files = [depot_files]
    output_files = [
        depot_file
        for depot_file in depot_files
        if depot_file.lower().startswith(f"{output_prefix}/".lower())
    ]
    assert output_files, (
        f"Aggregate changelist {change_number} has no files under {output_prefix}: "
        f"{depot_files}"
    )
    file_sizes = {
        record["depotFile"]: int(record.get("fileSize", 0))
        for record in project.p4.run(
            "fstat",
            "-Ol",
            "-T",
            "depotFile,fileSize",
            *(f"{depot_file}@={change_number}" for depot_file in output_files),
        )
        if isinstance(record, dict) and record.get("depotFile")
    }
    empty_files = [depot_file for depot_file in output_files if file_sizes.get(depot_file, 0) <= 0]
    assert (
        not empty_files
    ), f"Aggregate changelist {change_number} contains empty render outputs: {empty_files}"


def test_perforce_render_job_succeeds(
    deadline_client: Any,
    build_plugin: None,
    reusable_farm_id: str,
    reusable_queue_id: str,
    reusable_queue_fleet_association: tuple[str, str, str],
    deadline_worker_agent: tuple[subprocess.Popen, str],
    perforce_test_project: PerforceProject,
) -> None:
    """Generate, submit, render, and verify one Perforce-backed Unreal job."""
    del build_plugin
    _farm_id, _queue_id, expected_fleet_id = reusable_queue_fleet_association
    _worker_process, _worker_log = deadline_worker_agent
    expected_worker_id = _local_worker_id()

    deadline_config.set_setting("defaults.farm_id", reusable_farm_id)
    deadline_config.set_setting("defaults.queue_id", reusable_queue_id)
    deadline_config.set_setting("settings.deadline_regions", TEST_TARGET_REGION)

    bundle = _generate_perforce_bundle(perforce_test_project)
    perforce_test_project.cleanup_safe = False
    job_id = _submit_bundle(bundle, perforce_test_project.project_dir)
    perforce_test_project.job_id = job_id
    logger.info("Submitted Perforce render job %s", job_id)

    try:
        success, _status, message = wait_for_job_state(
            deadline_client=deadline_client,
            farm_id=reusable_farm_id,
            queue_id=reusable_queue_id,
            job_id=job_id,
            expected_states=["SUCCEEDED"],
            max_wait_time=1200,
            wait_interval=10,
        )
        assert success, message
        _assert_job_ran_on_worker(
            deadline_client,
            reusable_farm_id,
            reusable_queue_id,
            job_id,
            expected_fleet_id,
            expected_worker_id,
        )
        _assert_aggregate_outputs(perforce_test_project, job_id)
    finally:
        perforce_test_project.cleanup_safe = _cancel_job_and_wait(
            deadline_client,
            reusable_farm_id,
            reusable_queue_id,
            job_id,
        )
