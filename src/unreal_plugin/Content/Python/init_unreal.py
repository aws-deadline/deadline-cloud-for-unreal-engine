# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import json
import sys
import unreal
from pathlib import Path
from typing import Optional


def get_ue_path(in_path: str) -> Optional[str]:
    """
    Convert given path to unreal path by replacing substring that ends with /content/ to /Game/.
    If it can't convert, return None

    :param in_path: Path to convert
    :type in_path: str
    :return: Converted path or None
    :rtype: str
    """

    keyword = "/content/"
    idx = in_path.lower().find(keyword)
    if idx == -1:
        unreal.log_error(f"Depot path doesn't contain /Content/: {in_path}")
        return None

    ue_path = "/Game/" + in_path[idx + len(keyword) :]
    return ue_path


def sync_mrq_dependencies(dependencies_descriptor_path: str) -> None:
    """
    Read given dependencies descriptor, try to sync them with unreal source control and
    scan modified assets

    :param dependencies_descriptor_path: Path to the dependencies JSON descriptor file
    :type dependencies_descriptor_path: str
    """

    if not os.path.exists(dependencies_descriptor_path):
        unreal.log_error(
            f"MrqJobDependenciesDescriptor file does not exist: {dependencies_descriptor_path}"
        )
        return

    with open(dependencies_descriptor_path, "r", encoding="utf8") as f:
        job_dependencies_descriptor = json.load(f)

    job_dependencies = job_dependencies_descriptor.get("job_dependencies", [])
    if not job_dependencies:
        unreal.log_error(f"Job dependencies list is empty: {dependencies_descriptor_path}")
        return

    synced = unreal.SourceControl.sync_files(job_dependencies)
    if not synced:
        unreal.log_error(
            f"Failed to sync job dependencies: {dependencies_descriptor_path}. "
            f"Sync error message: {unreal.SourceControl.last_error_msg()}"
        )
        return

    ue_paths = []
    for job_dependency in job_dependencies:
        # Trim changelist number if any
        content_path = job_dependency.split("@")[0].replace("\\", "/")
        ue_path = get_ue_path(content_path)
        if ue_path:
            ue_paths.append(ue_path)

    if not ue_paths:
        unreal.log_error("No UE paths converted from input paths. Nothing to scan.")
        return

    asset_registry = unreal.AssetRegistryHelpers().get_asset_registry()
    asset_registry.scan_modified_asset_files(ue_paths)
    asset_registry.scan_paths_synchronous(ue_paths, True, True)


remote_execution = os.getenv("REMOTE_EXECUTION", "False")
if remote_execution != "True":

    # Add predefined OpenJD templates directory to sys path
    # to get available to submit jobs without providing YAMLs for default entities
    if "OPENJD_TEMPLATES_DIRECTORY" not in os.environ:
        os.environ["OPENJD_TEMPLATES_DIRECTORY"] = (
            f"{Path(__file__).parent.as_posix()}/openjd_templates"
        )

    # Add the custom submit actions path to sys path
    actions_path = Path(__file__).parent.joinpath("submit_actions").as_posix()

    if actions_path not in sys.path:
        sys.path.append(actions_path)

    libraries_path = f"{os.path.dirname(__file__)}/libraries".replace("\\", "/")
    if not os.getenv("DEADLINE_CLOUD") and os.path.exists(libraries_path):
        os.environ["DEADLINE_CLOUD"] = libraries_path

    if os.getenv("DEADLINE_CLOUD") and os.environ["DEADLINE_CLOUD"] not in sys.path:
        sys.path.append(os.environ["DEADLINE_CLOUD"])

    from deadline.unreal_logger import get_logger

    logger = get_logger()

    logger.info("INIT DEADLINE CLOUD")

    logger.info(f'DEADLINE CLOUD PATH: {os.getenv("DEADLINE_CLOUD")}')

    # These unused imports are REQUIRED!!!
    # Unreal Engine loads any init_unreal.py it finds in its search paths.
    # These imports finish the setup for the plugin.
    from settings import (
        DeadlineCloudSettingsLibraryImplementation,  # noqa: F401
        background_init_s3_client,
    )
    from job_library import DeadlineCloudJobBundleLibraryImplementation  # noqa: F401
    from open_job_template_api import (  # noqa: F401
        PythonYamlLibraryImplementation,
        ParametersConsistencyCheckerImplementation,
    )
    import remote_executor  # noqa: F401

    try:
        background_init_s3_client()
    except Exception as e:
        logger.error(f"Failed to run background_init_s3_client: {e}")

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
        sync_mrq_dependencies(cmd_parameters["MrqJobDependenciesDescriptor"])
