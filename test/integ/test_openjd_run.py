# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Integration test: validates the full UE adaptor lifecycle via openjd run."""

import glob
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

from scripts.build_plugin import find_engine_root

logger = logging.getLogger(__name__)


def test_openjd_run(request, build_plugin, create_test_project):
    """
    Run openjd run with the UE adaptor to validate the full lifecycle:
    daemon start (onEnter) -> custom script execution (onRun) -> daemon stop (onExit).
    """
    project_dir, uproject_file = create_test_project
    engine_root = find_engine_root(request.config.getoption("--ueversion"))
    editor_exe = Path(engine_root) / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe"

    # Find the most recent generated template from bundle gen test
    user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    pattern = os.path.join(user_profile, ".deadline", "job_history", "**", "template.yaml")
    templates = glob.glob(pattern, recursive=True)
    assert templates, "No template.yaml found in job_history — run test_bundle_generation first"

    template = Path(sorted(templates)[-1])
    logger.info(f"Using template: {template}")

    # Copy template to simple path (avoid parentheses/spaces)
    simple_template = Path("C:/Temp/test_template.yaml")
    simple_template.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template, simple_template)

    # Read template to get ScriptPath range value
    tmpl = yaml.safe_load(simple_template.read_text())
    step = next(s for s in tmpl["steps"] if s["name"] == "IntegTestStep")
    script_path_param = next(
        p for p in step["parameterSpace"]["taskParameterDefinitions"] if p["name"] == "ScriptPath"
    )
    test_script_path = script_path_param["range"][0]
    logger.info(f"ScriptPath from template range: {test_script_path}")

    # Create the test script at the expected path
    test_script = Path(test_script_path)
    test_script.parent.mkdir(parents=True, exist_ok=True)
    test_script.write_text(
        "import unreal\n"
        'unreal.log("IntegTest: Custom step script running inside UE")\n'
        'print("Custom Step Executor: Progress: 100")\n'
        'print("Custom Step Executor: Complete")\n'
    )

    # Write job params to file (avoids shell quoting issues)
    params_file = Path("C:/Temp/job_params.yaml")
    params = {
        "ProjectFilePath": str(uproject_file),
        "Executable": str(editor_exe),
        "ExtraCmdArgs": "-log -nullrhi -nosplash -nosound -unattended",
        "ExtraCmdArgsFile": "",
        "MarketplacePluginsDir": "",
    }
    params_file.write_text(yaml.dump(params))

    # Create environment template with specificationVersion header
    env_content = f"""specificationVersion: environment-2023-09
environment:
  name: LaunchUnrealEditor
  variables:
    REMOTE_EXECUTION: 'True'
  script:
    embeddedFiles:
      - name: initData
        filename: init-data.yaml
        type: TEXT
        data: |
          executable: {editor_exe}
          project_path: {uproject_file}
          extra_cmd_args: -log -nullrhi -nosplash -nosound -unattended
          extra_cmd_args_file: ''
    actions:
      onEnter:
        command: unreal-engine-openjd
        args:
        - daemon
        - start
        - --connection-file
        - '{{{{Session.WorkingDirectory}}}}/connection.json'
        - --init-data
        - file://{{{{Env.File.initData}}}}
        cancelation:
          mode: NOTIFY_THEN_TERMINATE
      onExit:
        command: unreal-engine-openjd
        args:
        - daemon
        - stop
        - --connection-file
        - '{{{{Session.WorkingDirectory}}}}/connection.json'
        cancelation:
          mode: NOTIFY_THEN_TERMINATE
"""
    env_file = Path("C:/Temp/test_environment.yaml")
    env_file.write_text(env_content)

    # Build and run openjd command
    tasks_json = json.dumps([{"Handler": "custom", "ScriptPath": test_script_path}])
    cmd = [
        "openjd",
        "run",
        str(simple_template),
        "--step",
        "IntegTestStep",
        "--environment",
        str(env_file),
        "--job-param",
        f"file://{params_file}",
        "--tasks",
        tasks_json,
    ]

    logger.info(f"Running openjd run: {cmd}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    logger.info(f"Return code: {result.returncode}")
    logger.info(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        logger.info(f"STDERR:\n{result.stderr}")

    assert result.returncode == 0, f"openjd run failed with return code {result.returncode}"
    assert "Session ended successfully" in result.stdout
