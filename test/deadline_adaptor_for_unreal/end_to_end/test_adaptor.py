#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import sys
import glob
import yaml
import subprocess
from pathlib import Path

import pytest


current_python_executable = sys.executable
deadline_cloud_for_unreal_location = Path(__file__).parent.parent.parent.parent
unreal_adaptor_executable = str(
    Path(current_python_executable).parent / "UnrealAdaptor.exe"
).replace("\\", "/")


def rebuild_adaptor():
    print(deadline_cloud_for_unreal_location)
    print(current_python_executable)
    # 1. Remove old builds
    os.system(f"rmdir /S /Q {deadline_cloud_for_unreal_location}\dist")

    # 2. Make a new build
    os.system(f"cd {deadline_cloud_for_unreal_location}")
    os.system(f"{current_python_executable} -m build")

    # 3. uninstall previous adaptor
    os.system(f"{current_python_executable} -m pip uninstall deadline-cloud-for-unreal --yes")

    # 4. install new build
    built_package = next(
        (f for f in glob.glob(f"{deadline_cloud_for_unreal_location}/dist/*.whl", recursive=True)),
        None,
    )
    if built_package:
        os.system(f"{current_python_executable} -m pip install {built_package}")


def to_yaml_file(data: dict, file_path: str):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        yaml.dump_all([data], f, indent=1)

    return f.name


def init_data():
    return {
        "project_path": "C:/LocalProjects/AWS_RND/AWS_RND.uproject",
    }


def run_data_render() -> dict:
    return {
        "handler": "render",
        "queue_manifest_path": "C:/LocalProjects/AWS_RND/Saved/MovieRenderPipeline/QueueManifest.utxt",
    }


def run_data_custom() -> dict:
    return {
        "handler": "custom",
        "script_path": f"{deadline_cloud_for_unreal_location}/"
        f"test/deadline_adaptor_for_unreal/unit/"
        f"UnrealClient/step_handlers/custom_scripts/valid_script.py",
    }


class TestUnrealAdaptor:
    @pytest.mark.parametrize(
        "init_data, run_data", [(init_data(), run_data_render()), (init_data(), run_data_custom())]
    )
    def test_full_run(self, init_data: dict, run_data: dict) -> None:
        current_location = os.path.dirname(__file__).replace("\\", "/")
        init_data_pah = to_yaml_file(init_data, f"{current_location}/data/init-data.yml")
        run_data_path = to_yaml_file(run_data, f"{current_location}/data/run-data.yml")

        assert Path(unreal_adaptor_executable).is_file()

        process = subprocess.Popen(
            [
                unreal_adaptor_executable,
                "run",
                "--init-data",
                f"file://{init_data_pah}",
                "--run-data",
                f"file://{run_data_path}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        output = process.communicate()
        out, err = output[0].decode("utf-8"), output[1].decode("utf-8")

        assert err == ""
        assert "Done UnrealAdaptor main" in out
        assert "Unreal Encountered an Error" not in out
