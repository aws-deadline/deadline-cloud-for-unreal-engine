# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import json
import unreal
from pathlib import Path
import sys

remote_execution = os.getenv("REMOTE_EXECUTION", "False")
if remote_execution != "True":

    if "OPENJD_TEMPLATES_DIRECTORY" not in os.environ:
        os.environ["OPENJD_TEMPLATES_DIRECTORY"] = (
            f"{Path(__file__).parent.as_posix()}/openjd_templates"
        )

    # Add the actions path to sys path
    actions_path = Path(__file__).parent.joinpath("submit_actions").as_posix()

    if actions_path not in sys.path:
        sys.path.append(actions_path)

    from deadline.unreal_logger import get_logger

    logger = get_logger()

    logger.info("INIT DEADLINE CLOUD")

    # These unused imports are REQUIRED!!!
    # Unreal Engine loads any init_unreal.py it finds in its search paths.
    # These imports finish the setup for the plugin.
    from settings import DeadlineCloudDeveloperSettingsImplementation  # noqa: F401
    from job_library import DeadlineCloudJobBundleLibraryImplementation  # noqa: F401
    from open_job_template_api import (  # noqa: F401
        PythonYamlLibraryImplementation,
        ParametersConsistencyCheckerImplementation,
    )
    import remote_executor  # noqa: F401

    logger.info("DEADLINE CLOUD INITIALIZED")

else:
    tokens, switchers, cmd_parameters = unreal.SystemLibrary.parse_command_line(
        unreal.SystemLibrary.get_command_line()
    )
    unreal.log(
        f"Parsed arguments:\n"
        f"Tokens: {tokens}\n"
        f"Switchers: {switchers}\n"
        f"CMD Parameters: {cmd_parameters}"
    )

    unreal.log("Waiting for asset registry completion ...")
    asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
    asset_registry.wait_for_completion()

    if "MrqJobDependenciesDescriptor" in cmd_parameters:
        descriptor = cmd_parameters["MrqJobDependenciesDescriptor"]

        if not os.path.exists(descriptor):
            unreal.log_error(f"MrqJobDependenciesDescriptor file does not exist: {descriptor}")
        else:
            with open(descriptor, "r") as f:
                job_dependencies_descriptor = json.load(f)

            for job_dependency in job_dependencies_descriptor.get("job_dependencies", []):
                if os.path.exists(job_dependency):
                    continue
                synced = unreal.SourceControl.sync_files([job_dependency])
                if synced:
                    unreal.AssetRegistryHelpers().get_asset_registry().scan_modified_asset_files(
                        [job_dependency]
                    )
                    unreal.AssetRegistryHelpers().get_asset_registry().scan_paths_synchronous(
                        [job_dependency], True, True
                    )
