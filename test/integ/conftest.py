# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

# Add repository root to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

from scripts.build_plugin import find_engine_root

logger = logging.getLogger(__name__)


def pytest_addoption(parser) -> None:
    """Add custom command line options to pytest."""
    parser.addoption(
        "--nobuild", action="store_true", default=False, help="Skip build_plugin fixture"
    )
    parser.addoption(
        "--ueversion",
        action="store",
        default=None,
        help="Specify Unreal Engine version (e.g. 5.4)",
    )


def get_source_root() -> str:
    """
    Return the path of the root of the deadline-cloud-for-unreal-engine source.

    Assumes it's 2 folders up from the directory this file lives in.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    root_dir = os.path.dirname(parent_dir)
    return root_dir


def add_plugins_to_project(project_path: str, plugins: List[str], enabled: bool) -> None:
    """
    Add the provided list of plugins to the uproject at the given project_path.

    Args:
        project_path: Path to .uproject file to add plugins to
        plugins: List of string names of plugins to add to the project
        enabled: Whether to enable or disable the plugins
    """
    with open(project_path, "r") as f:
        project_data = json.load(f)

    if "Plugins" not in project_data:
        project_data["Plugins"] = []

    for plugin_name in plugins:
        plugin_entry = {"Name": plugin_name, "Enabled": enabled}
        if plugin_entry not in project_data["Plugins"]:
            project_data["Plugins"].append(plugin_entry)

    with open(project_path, "w") as f:
        json.dump(project_data, f, indent=2)


@pytest.fixture(scope="session")
def build_plugin(request) -> None:
    """
    Fixture to run the scripts/build_plugin.py script at most once per test session.

    Guarantees the latest version of the code has been built and installed.
    Skipped if --nobuild is passed.
    """
    if request.config.getoption("--nobuild"):
        logger.info("Skipping build_plugin (--nobuild)")
    else:
        script_path = os.path.join(get_source_root(), "scripts", "build_plugin.py")
        if not os.path.exists(script_path):
            pytest.fail(f"Could not find build_plugin.py at {script_path}")

        build_args = ["python", script_path, "--install", "--test"]

        ueversion = request.config.getoption("--ueversion")
        if ueversion:
            build_args.append(f"--ueversion={ueversion}")

        logger.info(f"Running build_plugin: {' '.join(build_args)}")
        result = subprocess.run(build_args, text=True)
        assert (
            result.returncode == 0
        ), f"build_plugin.py failed with return code {result.returncode}"


@pytest.fixture(scope="session")
def create_test_project(request) -> Generator[Tuple[str, str], None, None]:
    """
    Create a test Unreal Engine project for integration testing.

    Creates a copy of the TP_DMXBP template project and adds the required plugins.

    Yields:
        Tuple containing (project_directory_path, project_file_path)
    """
    project_base = os.path.expanduser("~/Documents/UnrealProjects/TestProjects")
    os.makedirs(project_base, exist_ok=True)

    # Create a directory with a unique name under the project base folder
    temp_dir = tempfile.TemporaryDirectory(dir=project_base).name
    logger.info(f"Created project folder: {temp_dir}")

    engine_root = find_engine_root(request.config.getoption("--ueversion"))
    source_path = os.path.join(engine_root, r"Templates\TP_DMXBP")
    if not os.path.exists(source_path):
        pytest.fail(f"Could not find source template at {source_path}")

    dest_path = os.path.abspath(os.path.join(temp_dir, "TP_DMXBP"))

    shutil.copytree(source_path, dest_path)
    logger.info(f"Created project dir {dest_path}")

    # Add required plugins to the project
    project_path = os.path.join(dest_path, "TP_DMXBP.uproject")
    add_plugins_to_project(
        project_path,
        ["UnrealDeadlineCloudService", "MovieRenderPipeline"],
        True,
    )

    yield dest_path, project_path

    # Cleanup: remove the temporary project directory
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"Cleaned up project folder: {temp_dir}")
    except Exception as e:
        logger.warning(f"Failed to clean up project folder {temp_dir}: {e}")


def run_unreal_python_script(
    request,
    uproject_file: str,
    script_path: str,
    env_updates: Dict[str, str],
    timeout: Optional[float] = None,
) -> Tuple[int, str]:
    """
    Launch UnrealEditor-Cmd -unattended with -ExecutePythonScript and wait for it to exit.

    UE's print() does not reach parent process stdout, so scripts report results through
    marker files named in env_updates. The UE exit code alone does not indicate success.

    Returns:
        Tuple containing (UE exit code, combined UE output)
    """
    engine_root = find_engine_root(request.config.getoption("--ueversion"))
    editor_exe = os.path.join(engine_root, "Engine", "Binaries", "Win64", "UnrealEditor-Cmd.exe")
    if not os.path.exists(editor_exe):
        pytest.fail(f"Could not find UnrealEditor-Cmd.exe at {editor_exe}")
    if not os.path.exists(script_path):
        pytest.fail(f"Could not find script at {script_path}")

    # No API credentials are needed: scripts generate bundles locally with zero network access
    env = os.environ.copy()
    env.update(env_updates)

    cmd = [
        editor_exe,
        uproject_file,
        f"-ExecutePythonScript={script_path}",
        "-stdout",
        "-unattended",
        "-nullrhi",
        "-nosplash",
        "-nosound",
        "-nopause",
    ]

    logger.info("Launching UE via -ExecutePythonScript")
    logger.info(f"Command: {' '.join(cmd)}")
    logger.info(f"Environment updates: {env_updates}")

    process = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        timeout=timeout,
    )
    logger.info(f"UE exited with return code {process.returncode}")
    return process.returncode, process.stdout or ""


def _output_tail(output: str, lines: int = 100) -> str:
    return "".join(output.splitlines(keepends=True)[-lines:])


@pytest.fixture
def run_unreal_bundle_only(request, create_test_project) -> Path:
    """
    Fixture that launches UnrealEditor-Cmd with -ExecutePythonScript to generate a job bundle.

    Uses a marker file to communicate the bundle path back from UE's embedded Python,
    since UE's print() does not reach parent process stdout. No Deadline Cloud API
    calls are made -- the script generates the bundle locally with zero network access.

    Returns:
        Path to the generated job bundle directory.
    """
    _, uproject_file = create_test_project

    # Locate the generate_bundle.py script relative to the repository root
    generate_bundle_script = os.path.join(get_source_root(), "pipeline", "generate_bundle.py")

    # Create a temporary marker file for the script to write the bundle path into
    marker_fd, marker_file_path = tempfile.mkstemp(prefix="deadline_bundle_marker_", suffix=".txt")
    os.close(marker_fd)
    marker_file = Path(marker_file_path)
    # Ensure it starts empty so we can detect if the script never wrote to it
    marker_file.write_text("")

    returncode, ue_output = run_unreal_python_script(
        request,
        uproject_file,
        generate_bundle_script,
        {"DEADLINE_CLOUD_INTEG_MARKER_FILE": str(marker_file)},
    )

    # Read the marker file to get the bundle path
    if not marker_file.exists():
        pytest.fail(
            f"Marker file was not created at {marker_file}.\n"
            f"UE exit code: {returncode}\n"
            f"UE output (last 100 lines):\n{_output_tail(ue_output)}"
        )

    bundle_path = marker_file.read_text().strip()

    # Clean up marker file
    try:
        marker_file.unlink()
    except OSError:
        pass  # Non-critical: temp file cleanup failure is acceptable

    if not bundle_path:
        pytest.fail(
            f"Marker file at {marker_file_path} exists but is empty. "
            f"The generate_bundle.py script may have failed to write the bundle path.\n"
            f"UE exit code: {returncode}\n"
            f"UE output (last 100 lines):\n{_output_tail(ue_output)}"
        )

    bundle = Path(bundle_path)
    if not bundle.exists():
        pytest.fail(
            f"Bundle path reported by script does not exist: {bundle}\n"
            f"UE exit code: {returncode}"
        )

    logger.info(f"Bundle generated at: {bundle}")
    return bundle


@pytest.fixture(scope="session")
def run_template_update_bundles(request, build_plugin, create_test_project) -> Dict[str, Any]:
    """
    Launch UE once to generate MRQ job template update bundles.

    See pipeline/generate_template_update_bundles.py for the cases. Bundles, the JSON marker
    and the UE log are preserved in DEADLINE_CLOUD_INTEG_ARTIFACTS_DIR (or a new temp
    directory) for inspection; temporary template YAML files are removed.

    Returns:
        Marker JSON with per-case results and bundle paths.
    """
    _, uproject_file = create_test_project
    script = os.path.join(get_source_root(), "pipeline", "generate_template_update_bundles.py")
    artifacts_dir = Path(
        os.environ.get("DEADLINE_CLOUD_INTEG_ARTIFACTS_DIR")
        or tempfile.mkdtemp(prefix="deadline_template_update_bundles_")
    )
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="deadline_template_update_work_"))
    marker_file = work_dir / "marker.json"
    # Keep CondaChannels deterministic for Conda default normalization
    conda_channels = os.environ.pop("DEADLINE_CONDA_CHANNELS", None)
    try:
        returncode, ue_output = run_unreal_python_script(
            request,
            uproject_file,
            script,
            {
                "DEADLINE_CLOUD_INTEG_MARKER_FILE": str(marker_file),
                "DEADLINE_CLOUD_INTEG_WORK_DIR": str(work_dir),
                "DEADLINE_CLOUD_INTEG_ARTIFACTS_DIR": str(artifacts_dir),
            },
            timeout=1800,
        )
        (artifacts_dir / "unreal_output.log").write_text(ue_output, encoding="utf-8")
        marker_text = marker_file.read_text(encoding="utf-8") if marker_file.exists() else ""
        if marker_text:
            (artifacts_dir / "marker.json").write_text(marker_text, encoding="utf-8")
    finally:
        if conda_channels is not None:
            os.environ["DEADLINE_CONDA_CHANNELS"] = conda_channels
        shutil.rmtree(work_dir, ignore_errors=True)

    logger.info(f"Template update artifacts: {artifacts_dir}")
    if not marker_text:
        pytest.fail(
            f"Template update marker was not written. UE exit code: {returncode}\n"
            f"Artifacts: {artifacts_dir}\nUE output (last 100 lines):\n{_output_tail(ue_output)}"
        )
    result = json.loads(marker_text)
    if result.get("status") != "ok":
        pytest.fail(
            f"Template update script failed: {result.get('error')}\n{result.get('traceback')}\n"
            f"UE exit code: {returncode}\nArtifacts: {artifacts_dir}"
        )
    result["artifacts_dir"] = str(artifacts_dir)
    return result
