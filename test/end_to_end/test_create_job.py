# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import subprocess
import logging

logger = logging.getLogger(__name__)


def test_create_job(build_plugin, create_readonly_test_project):
    """Run CreateJob automation test from within Unreal"""

    _, uproject_file = create_readonly_test_project

    logger.info(f"Creating job from project {uproject_file}")
    create_job_args = [
        "UnrealEditor-Cmd.exe",
        uproject_file,
        "-ExecCmds=Automation RunTests Deadline.Integration.CreateJob",
        "-stdout",
        "-unattended",
        "-nullrhi",
        "-nosplash",
        "-nosound",
        "-nocontentbrowser",
        "-nopause",
        "-testexit=Automation Test Queue Empty",
        "-deadlineargs=-NoLoadingScreen -FixedSeed -log -Unattended -MRQInstance -deterministicaudio -audiomixer",
    ]
    logger.info(f"Calling subprocess with args {create_job_args}")
    result = subprocess.run(create_job_args, text=True)
    assert result.returncode == 0
