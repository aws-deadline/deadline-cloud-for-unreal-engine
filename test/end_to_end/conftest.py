# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import json
import pytest
import os
import shutil
import subprocess
import sys
import tempfile

# import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

from scripts.build_plugin import find_engine_root


def get_source_root() -> str:
    """
    Return the path of the root of the deadline-cloud-for-unreal-engine source.  Assumes it's 2 folders up from the directory this
    file lives in, which is in a "/scripts/" subfolder off the root
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Get the parent directory
    parent_dir = os.path.dirname(current_dir)
    root_dir = os.path.dirname(parent_dir)
    return root_dir


def get_build_script_args() -> list[str]:
    """
    Return the arguments to pass to the build script for a test installation
    """

    return ["--install", "--test", "--worker"]


def add_plugins_to_project(project_path: str, plugins: list[str]):
    """
    Add the provided list of plugins to the uproject at the given project_path

    :param project_path: path to .uproject file to add plugins to
    :param plugins: List of string names of plugins to add to the project
    """

    # Read the current .uproject file
    with open(project_path, "r") as f:
        project_data = json.load(f)

    # Make sure Plugins list exists
    if "Plugins" not in project_data:
        project_data["Plugins"] = []

    # Add each plugin if not already present
    for plugin_name in plugins:
        plugin_entry = {"Name": plugin_name, "Enabled": True}
        if plugin_entry not in project_data["Plugins"]:
            project_data["Plugins"].append(plugin_entry)

    # Write back the modified file
    with open(project_path, "w") as f:
        json.dump(project_data, f, indent=2)


@pytest.fixture(scope="session")
def build_plugin():
    # A fixture to run the scripts/build_plugin.py script at most once per test session to guarantee
    # the latest version of the code has been built and installed.  We run the script as a subprocess
    # rather than importing and running the methods directly to simulate how customers will execute it

    # build_plugin.py lives in the scripts subfolder relative to the root of the repository
    # which is two folders up from this folder
    script_path = os.path.join(get_source_root(), "scripts", "build_plugin.py")
    if not os.path.exists(script_path):
        pytest.fail(f"Could not find build_plugin.py at {script_path}")

    build_args = ["python", script_path]
    build_args.extend(get_build_script_args())
    # Run the script and capture the output
    result = subprocess.run(build_args, text=True)
    assert result.returncode == 0


@pytest.fixture(scope="session")
def create_readonly_test_project():
    project_base = os.path.expanduser("~/Documents/UnrealProjects/TestProjects")
    os.makedirs(project_base, exist_ok=True)

    # Create a directory with a unique name under the project base folder
    # Using a default temporary directory will cause Unreal build failures
    temp_dir = tempfile.TemporaryDirectory(dir=project_base).name
    print(f"Created project folder: {temp_dir}")

    engine_root = find_engine_root()
    # Source path for the template
    source_path = os.path.join(engine_root, "Templates\TP_DMXBP")
    if not os.path.exists(source_path):
        pytest.fail(f"Could not find source template at {source_path}")

    # Destination will be temp_dir/TP_DMXBP
    dest_path = os.path.abspath(os.path.join(temp_dir, "TP_DMXBP"))

    # Recursively copy the directory
    shutil.copytree(source_path, dest_path)
    print(f"Created project dir {dest_path}")

    # Add our plugins
    project_path = os.path.join(dest_path, "TP_DMXBP.uproject")
    add_plugins_to_project(project_path, ["UnrealDeadlineCloudService", "MovieRenderPipeline"])

    yield dest_path, project_path
