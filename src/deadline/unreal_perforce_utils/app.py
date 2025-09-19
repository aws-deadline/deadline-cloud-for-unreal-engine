# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import json
import pprint
import socket
import getpass
from pathlib import Path
from typing import Optional

from deadline.unreal_logger import get_logger
from deadline.unreal_perforce_utils import perforce, exceptions, secret_manager

logger = get_logger()


def get_workspace_name(project_name: str) -> str:
    """
    Build and return the workspace name based on the given project name:
    ``<USERNAME>_<HOST>_<PROJECT_NAME>``.

    If ``DEADLINE_WORKER_ID`` environment variable is set, it will be appended:
    ``<USERNAME>_<HOST>_<PROJECT_NAME>_<WORKER_ID>``

    :param project_name: Name of the project

    :return: Workspace name
    :rtype: str
    """

    workspace_name = f"{getpass.getuser()}_{socket.gethostname()}_{project_name}"
    if "DEADLINE_WORKER_ID" in os.environ:
        workspace_name += f"_{os.environ['DEADLINE_WORKER_ID']}"

    return workspace_name


def get_workspace_specification_template_from_file(
    workspace_specification_template_path: str,
) -> dict:
    """
    Read the given workspace specification template file path and return loaded content

    :param workspace_specification_template_path: Path to the workspace specification template file

    :return: Loaded workspace specification template dictionary
    :rtype: dict
    """

    if not os.path.exists(workspace_specification_template_path):
        raise FileNotFoundError(
            f"The workspace specification template does not exist: {workspace_specification_template_path}"
        )

    logger.info(
        f"Getting workspace specification template from file: {workspace_specification_template_path} ..."
    )
    with open(workspace_specification_template_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_perforce_workspace_from_template(
    specification_template: dict,
    project_name: str,
    overridden_workspace_root: Optional[str] = None,
) -> perforce.PerforceClient:
    """
    Creates Perforce workspace from the template.

    For template example see
    :meth:`deadline.unreal_perforce_utils.perforce.get_perforce_workspace_specification_template()`

    Replace ``{workspace_name}`` token in the template with the real workspace name in
    ``"Client"`` and ``"View"`` fields

    :param specification_template: Workspace specification template dictionary
    :param project_name: Name of the project to build workspace name
    :param overridden_workspace_root: Workspace local path root (Optional, root from template is used by default)

    :return: :class:`p4utilsforunreal.perforce.PerforceClient` instance
    :rtype: :class:`p4utilsforunreal.perforce.PerforceClient`
    """

    logger.info(
        f"Creating perforce workspace from template: \n"
        f"Specification template: {specification_template}\n"
        f"Project: {project_name}\n"
        f"Overridden workspace root: {overridden_workspace_root}"
    )

    workspace_name = get_workspace_name(project_name=project_name)

    specification_template["Client"] = specification_template["Client"].replace(
        "{workspace_name}", workspace_name
    )
    if "View" in specification_template:
        updated_views = []
        for view in specification_template["View"]:
            updated_views.append(view.replace("{workspace_name}", workspace_name))
        specification_template["View"] = updated_views

    if overridden_workspace_root:
        specification_template["Root"] = overridden_workspace_root
    else:
        specification_template["Root"] = (
            f"{os.getenv('P4_CLIENTS_ROOT_DIRECTORY', os.getcwd())}/{workspace_name}"
        )

    logger.info(f"Specification: {specification_template}")

    perforce_client = perforce.PerforceClient(
        connection=perforce.PerforceConnection(),
        name=workspace_name,
        specification=specification_template,
    )

    perforce_client.save()

    logger.info("Perforce workspace created!")
    logger.info(pprint.pformat(perforce_client.spec))

    return perforce_client


def _parse_job_dependencies(
    workspace: perforce.PerforceClient, job_dependencies_descriptor_path: str
) -> list[str]:
    with open(job_dependencies_descriptor_path, "r", encoding="utf-8") as f:
        job_data = json.load(f)
        dependent_paths = job_data.get("job_dependencies", [])
        if not isinstance(dependent_paths, list):
            logger.info(
                f"Warning: job_dependencies must be a list, got {type(dependent_paths).__name__}"
            )
            return []

        # Convert dependency paths to local workspace paths
        dependent_paths_to_sync = []
        for dependent_path in dependent_paths:
            if not isinstance(dependent_path, str) or not dependent_path.strip():
                logger.warning(f"Warning: skipping invalid dependency path: {dependent_path}")
                continue

            local_path = workspace.where(dependent_path)
            if local_path:
                dependent_paths_to_sync.append(local_path.replace("\\", "/"))
            else:
                logger.warning(f"Can't convert {dependent_path} to local path.")
    return dependent_paths_to_sync


def initial_workspace_sync(
    workspace: perforce.PerforceClient,
    unreal_project_relative_path: str,
    changelist: Optional[str] = None,
    job_dependencies_descriptor_path: Optional[str] = None,
) -> None:
    """
    Do initial workspace synchronization:

    - .uproject file
    - Binaries folder
    - Config folder
    - Plugins folder
    - If ``job_dependencies_descriptor_path`` is provided, sync job dependencies as well.

    :param workspace: p4utilsforunreal.perforce.PerforceClient instance
    :param unreal_project_relative_path: path to the .uproject file relative to the workspace root
    :param changelist: Changelist number to sync workspace to
    :param job_dependencies_descriptor_path: Path to JSON file containing job dependencies to sync
    """

    logger.info("Workspace initial synchronizing ...")

    workspace_root = workspace.spec["Root"].replace("\\", "/")
    paths_to_sync = [f"{workspace_root}/{unreal_project_relative_path}"]
    unreal_project_directory = os.path.dirname(unreal_project_relative_path)
    for folder in ["Binaries", "Config", "Plugins"]:
        tokens = filter(
            lambda t: t not in [None, ""], [workspace_root, unreal_project_directory, folder, "..."]
        )
        paths_to_sync.append("/".join(tokens))

    # Add job dependencies if provided
    if job_dependencies_descriptor_path and os.path.exists(job_dependencies_descriptor_path):
        dependency_paths = _parse_job_dependencies(workspace, job_dependencies_descriptor_path)
        paths_to_sync.extend(dependency_paths)

    logger.info(f"Paths to sync: {paths_to_sync}")

    for path in paths_to_sync:
        try:
            workspace.sync(path, changelist=changelist, force=True)
        except Exception as e:
            logger.error(f"Initial workspace sync exception: {str(e)}")


def configure_project_source_control_settings(
    workspace: perforce.PerforceClient, unreal_project_relative_path: str
):
    """
    Configure SourceControl settings (Saved/Config/WindowsEditor/SourceControlSettings.ini)
    with the current P4 connection settings

    :param workspace: p4utilsforunreal.perforce.PerforceClient instance
    :param unreal_project_relative_path: path to the .uproject file relative to the workspace root
    """

    logger.info("Configuring Unreal project SourceControl settings ...")
    unreal_project_directory = os.path.dirname(unreal_project_relative_path)
    tokens = filter(
        lambda t: t not in [None, ""],
        [
            workspace.spec["Root"],
            unreal_project_directory,
            "Saved/Config/WindowsEditor/SourceControlSettings.ini",
        ],
    )
    source_control_settings_path = "/".join(tokens)
    os.makedirs(os.path.dirname(source_control_settings_path), exist_ok=True)
    logger.info(f"Source Control settings file: {source_control_settings_path}")

    source_control_settings_lines = [
        "[PerforceSourceControl.PerforceSourceControlSettings]\n",
        "UseP4Config = False\n",
        f"Port = {workspace.p4.port}\n",
        f"UserName = {workspace.p4.user}\n",
        f"Workspace = {workspace.p4.client}\n\n",
        "[SourceControl.SourceControlSettings]\n",
        "Provider = Perforce\n",
    ]
    logger.info("source control settings:\n")
    for setting_line in source_control_settings_lines:
        logger.info(setting_line)

    with open(source_control_settings_path, "w+") as f:
        for setting_line in source_control_settings_lines:
            f.write(setting_line)


def create_workspace(
    perforce_specification_template_path: str,
    unreal_project_relative_path: str,
    unreal_project_name: Optional[str] = None,
    overridden_workspace_root: Optional[str] = None,
    changelist: Optional[str] = None,
    job_dependencies_descriptor_path: Optional[str] = None,
):
    """
    Create P4 workspace and execute next steps:

    - :meth:`deadline.unreal_perforce_utils.app.get_workspace_specification_template_from_file()`
    - :meth:`deadline.unreal_perforce_utils.app.initial_workspace_sync()`
    - :meth:`deadline.unreal_perforce_utils.app.configure_project_source_control_settings()`

    :param perforce_specification_template_path: Path to the perforce specification template file to read specification from
    :param unreal_project_relative_path: path to the .uproject file relative to the workspace root
    :param unreal_project_name: Name of the .uproject file
    :param overridden_workspace_root: Workspace local path root (Optional, root from template is used by default)
    :param changelist: Changelist to sync workspace to
    :param job_dependencies_descriptor_path: Path to JSON file containing job dependencies to sync
    """

    logger.info(
        "Creating workspace with the following settings:\n"
        f"Specification template: {perforce_specification_template_path}\n"
        f"Unreal project relative path: {unreal_project_relative_path}\n"
        f"Overridden workspace root: {overridden_workspace_root}\n"
        f"Changelist: {changelist}\n"
        f"job_dependencies_descriptor_path: {job_dependencies_descriptor_path}"
    )

    workspace_specification_template = get_workspace_specification_template_from_file(
        workspace_specification_template_path=perforce_specification_template_path
    )

    workspace = create_perforce_workspace_from_template(
        specification_template=workspace_specification_template,
        project_name=unreal_project_name or Path(unreal_project_relative_path).stem,
        overridden_workspace_root=overridden_workspace_root,
    )

    # Required to make DeadlineCloud set this variable to Environment
    p4_client_directory = workspace.spec["Root"].replace("\\", "/")
    logger.info(f"openjd_env: P4_CLIENT_DIRECTORY={p4_client_directory}")

    initial_workspace_sync(
        workspace=workspace,
        unreal_project_relative_path=unreal_project_relative_path,
        changelist=changelist,
        job_dependencies_descriptor_path=job_dependencies_descriptor_path,
    )

    configure_project_source_control_settings(
        workspace=workspace, unreal_project_relative_path=unreal_project_relative_path
    )


def revert_all_changes_in_workspace(
    workspace_name: str, workspace_root: str, p4_connection: perforce.P4
) -> Optional[Exception]:
    """
    Revert all changes in default changelist by running command
    `p4 revert -c default <workspace_root>/...`.

    :param workspace_name: Name of the workspace to revert
    :type workspace_name: str
    :param workspace_root: Workspace root directory
    :type workspace_root: str
    :param p4_connection: P4 connection
    :type p4_connection: perforce.P4

    :return: Exception if caught, None otherwise
    :rtype: Optional[Exception]
    """

    try:
        logger.info("Reverting changes in default changelist")
        p4_connection.client = workspace_name
        p4_connection.run("revert", "-c", "default", workspace_root + "/...")
    except Exception as e:
        if "file(s) not opened on this client" in str(e):
            logger.info("Nothing to revert")
        else:
            logger.error(f"Error handled while reverting changes: {e}")
            return e

    return None


def clear_workspace_files(
    workspace_name: str, workspace_root: str, p4_connection: perforce.P4
) -> Optional[Exception]:
    """
    Delete all local files from workspace syncing them to revision #0.
    Command `p4 sync -f <workspace_root>/...#0>`.

    :param workspace_name: Name of the workspace to clear
    :type workspace_name: str
    :param workspace_root: Workspace root directory
    :type workspace_root: str
    :param p4_connection: P4 connection
    :type p4_connection: perforce.P4

    :return: Exception if caught, None otherwise
    :rtype: Optional[Exception]
    """

    try:
        logger.info(f"Clearing workspace root: {workspace_root}")
        p4_connection.client = workspace_name
        p4_connection.run("sync", "-f", workspace_root + "/...#0")
    except Exception as e:
        if "file(s) up-to-date" in str(e):
            logger.info("Nothing to clear")
        else:
            logger.error(f"Error handled while clearing workspace: {e}")
            return e

    return None


def delete_workspace(workspace_name: Optional[str] = None, project_name: Optional[str] = None):
    """
    Clear workspace files in the depot and delete the workspace.
    If the `P4_CLIENTS_ROOT_DIRECTORY` environment variable is set, skip deletion. This indicates
    that the workspaces are located in a permanent directory and should not be deleted.

    Roll back all possible changes in reverse order:
    Delete worksapce <- Delete local files <- Revert changes

    - :meth:`deadline.unreal_perforce_utils.app.revert_all_changes_in_workspace()`
    - :meth:`deadline.unreal_perforce_utils.app.clear_workspace_files()`
    - delete workspace by running ``p4.run("client", "-d", "-f", workspace_name_to_delete)``

    :param workspace_name: Name of the workspace to delete
    :param project_name: Name of the Unreal Project to generate a workspace name if not provided
    """

    if "P4_CLIENTS_ROOT_DIRECTORY" in os.environ:
        logger.info("P4_CLIENTS_ROOT_DIRECTORY variable found. Skip deleting the workspace")
        return

    logger.info(f"Deleting workspace for the project: {project_name}")

    if workspace_name:
        workspace_name_to_delete = workspace_name
    elif project_name:
        workspace_name_to_delete = get_workspace_name(project_name)
    else:
        raise exceptions.PerforceWorkspaceNotFoundError(
            "Can't get workspace name to delete "
            "since no workspace name or Unreal project name is provided"
        )

    p4 = perforce.PerforceConnection().p4

    last_exception = None

    workspace_root = p4.fetch_client(workspace_name_to_delete).get("Root").replace("\\", "/")
    if workspace_root and os.path.exists(workspace_root):
        revert_exc = revert_all_changes_in_workspace(
            workspace_name=workspace_name_to_delete, workspace_root=workspace_root, p4_connection=p4
        )
        if revert_exc is not None:
            last_exception = revert_exc

        clear_exc = clear_workspace_files(
            workspace_name=workspace_name_to_delete, workspace_root=workspace_root, p4_connection=p4
        )
        if clear_exc is not None:
            last_exception = clear_exc

    try:
        logger.info(f"Deleting workspace: {workspace_name_to_delete}")
        p4.run("client", "-d", "-f", workspace_name_to_delete)
    except Exception as e:
        logger.error(f"Error handled while deleting workspace: {e}")
        last_exception = e

    if last_exception and isinstance(last_exception, Exception):
        raise last_exception


def apply_perforce_secrets() -> None:
    """
    Apply secrets from Boto3 SecretsManager to Perforce environment variables. Try to find secret
    by name stored in AWS_SECRET_P4INFO and apply all key/value pairs from it as environment variables.

    The following environment variables can be set:

    - P4USER
    - P4PASSWD
    - P4PORT

    """

    logger.info("Applying perforce secrets from Boto3 SecretsManager ...")

    p4_info = secret_manager.get_perforce_info()
    if not p4_info:
        logger.info("No perforce secrets found in Boto3 SecretsManager. Skip applying")
        return

    for env_name, env_value in p4_info.items():
        # For some reason, adaptor doesn't show logger records, need to R&D
        logger.info(f"openjd_redacted_env: {env_name}={env_value}")
