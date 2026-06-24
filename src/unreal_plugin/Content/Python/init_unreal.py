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
    scan modified assets.

    If DEPENDENCIES_SYNCED env var is set, the P4 sync environment already synced
    these files — skip the redundant sync and just scan the asset registry.

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

    if os.getenv("DEPENDENCIES_SYNCED") != "true":
        synced = unreal.SourceControl.sync_files(job_dependencies)
        if not synced:
            unreal.log_error(
                f"Failed to sync job dependencies: {dependencies_descriptor_path}. "
                f"Sync error message: {unreal.SourceControl.last_error_msg()}"
            )
            return
    else:
        unreal.log("Skipping P4 sync — dependencies already synced by P4 sync environment.")

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


def _check_patch_pydantic_py397():
    """
    Fix Pydantic's StringConstraints for Python 3.9.7 compatibility to work with
    default Python in Unreal 5.3 (3.9.7)

    In Python 3.9.7, when a dataclass with frozen=True inherits from a Protocol,
    the dataclass decorator fails to generate the __init__ method. This function
    manually generates the proper __init__ for StringConstraints.

    See https://github.com/pydantic/pydantic/issues/7745
    """

    # Only apply on Python 3.9.7
    if sys.version_info[:3] != (3, 9, 7):
        print(f"Skipping Python 3.9.7 patch: Python version is {sys.version_info[:3]}")
        return

    try:
        import pydantic.types
    except ImportError:
        print("Skipping Python 3.9.7 patch: pydantic not found")
        # Pydantic not installed, nothing to fix
        return

    from typing import Pattern, Union

    StringConstraints = pydantic.types.StringConstraints

    # Generate the proper __init__ method with correct type hints
    def __init__(
        self: "pydantic.types.StringConstraints",
        *,
        strip_whitespace: Optional[bool] = None,
        to_upper: Optional[bool] = None,
        to_lower: Optional[bool] = None,
        strict: Optional[bool] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Union[str, Pattern[str], None] = None,
    ) -> None:
        """Initialize StringConstraints with the given parameters."""
        # Use object.__setattr__ because frozen=True prevents normal attribute assignment
        object.__setattr__(self, "strip_whitespace", strip_whitespace)
        object.__setattr__(self, "to_upper", to_upper)
        object.__setattr__(self, "to_lower", to_lower)
        object.__setattr__(self, "strict", strict)
        object.__setattr__(self, "min_length", min_length)
        object.__setattr__(self, "max_length", max_length)
        object.__setattr__(self, "pattern", pattern)

    # Apply the fix - type checkers will complain but this is intentional monkey-patching
    StringConstraints.__init__ = __init__  # type: ignore

    print("Applied Python 3.9.7 compatibility fix for pydantic.types.StringConstraints")


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
        # Insert before UE's auto-installed PipInstall packages, which may contain
        # older versions of shared dependencies (e.g. typing_extensions) that are
        # incompatible with the versions bundled by this plugin.
        _pip_install_idx = next(
            (i for i, p in enumerate(sys.path) if "PipInstall" in p),
            len(sys.path),
        )
        sys.path.insert(_pip_install_idx, os.environ["DEADLINE_CLOUD"])

    from deadline.unreal_logger import get_logger

    logger = get_logger()

    logger.info("INIT DEADLINE CLOUD")

    from update_check import safe_check_and_show_update_dialog

    safe_check_and_show_update_dialog()

    logger.info(f'DEADLINE CLOUD PATH: {os.getenv("DEADLINE_CLOUD")}')

    # These unused imports are REQUIRED!!!
    # Unreal Engine loads any init_unreal.py it finds in its search paths.
    # These imports finish the setup for the plugin.
    from settings import (
        DeadlineCloudSettingsLibraryImplementation,  # noqa: F401
        background_init_s3_client,
    )

    # UNREAL 5.3 PATCH - Temp fix to maintain support for system default python
    # in Unreal 5.3 (3.9.7)
    _check_patch_pydantic_py397()

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
