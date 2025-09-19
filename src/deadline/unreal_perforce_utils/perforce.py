# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import re
from P4 import P4, P4Exception
from typing import Optional, Any

from deadline.unreal_logger import get_logger
from deadline.unreal_perforce_utils import exceptions, secret_manager


logger = get_logger()


class PerforceConnection:
    """
    Wrapper around the P4 object of p4python package

    P4 connection can be created by:

    1. passing port, user, password and charset to the constructor
    2. providing AWS Secrets Manager secret name in env variable AWS_SECRET_P4INFO where
       p4 connection parameters are stored
    3. setting appropriate P4PORT, P4USER and P4PASSWD environment variables.

    .. note::
       Default connection properties will be used if none of the above is provided
    """

    def __init__(
        self,
        port: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        client: Optional[str] = None,
        charset="none",
    ):
        p4 = P4()
        p4.charset = charset

        p4_secret = secret_manager.get_perforce_info() or {}

        p4_port = port or p4_secret.get("P4PORT") or os.getenv("P4PORT")
        if p4_port:
            p4.port = p4_port

        p4_user = user or p4_secret.get("P4USER") or os.getenv("P4USER")
        if p4_user:
            p4.user = p4_user

        try:
            p4.connect()
        except P4Exception as e:
            raise exceptions.PerforceConnectionError(
                f"Could not connect Perforce server {p4.port} as user {p4.user}\n{str(e)}"
            )

        p4.input = "y"
        p4.run("trust", ["-y"])

        # If any of P4 variables is set in environment (PORT, P4USER, P4PASSWD, etc.), P4 instance's
        # appropriate property will be set automatically. That means right here if
        # os.environ["P4PASSWD"] = "SomePass" then p4.password will be set to "SomePass".
        # But let's be defensive and set it explicitly
        p4_password = password or p4_secret.get("P4PASSWD") or os.getenv("P4PASSWD")
        if p4_password:
            p4.password = p4_password
            p4.run_login()

        p4_client = client or os.getenv("P4CLIENT")
        if p4_client:
            p4.client = p4_client

        self.p4 = p4

    def get_info(self) -> dict[str, Any]:
        return self.p4.run("info")[0]

    def get_stream_path(self) -> Optional[str]:
        return self.get_info().get("clientStream")

    def get_client_root(self) -> Optional[str]:
        client_root = self.get_info().get("clientRoot")
        if client_root:
            client_root = client_root.replace("\\", "/")
        return client_root

    def get_latest_changelist_number(self) -> Optional[int]:
        changes = self.p4.run("changes", "-m", 1, "#have")
        if changes:
            return int(changes[0]["change"])
        return None

    def get_workspace_specification(self) -> Optional[dict]:
        return self.p4.fetch_client(self.p4.client)

    def get_depot_file_paths(self, local_file_paths: list[str]) -> list[str]:
        """
        Return the file locations on Perforce depot by running `p4 where <local_paths>`

        :param local_file_paths: Local file paths to find in Depot

        :return: File paths on Perforce depot if found, None otherwise
        :rtype: list[str]
        """

        where_info = self.p4.run("where", local_file_paths)

        return [file_info.get("depotFile") for file_info in where_info]


class PerforceClient:
    """
    Wrapper around the P4 workspace (client)
    """

    def __init__(
        self, connection: PerforceConnection, name: str, specification: Optional[dict] = None
    ):
        self.p4 = connection.p4
        self.name = name
        self.spec = self.p4.fetch_client(name)

        if specification:
            self.spec.update(specification)

        self.p4.client = self.name

    def save(self):
        """
        Save the perforce client (workspace) on the P4 server
        """

        self.p4.save_client(self.spec)

    def sync(
        self, filepath: Optional[str] = None, changelist: Optional[str] = None, force: bool = False
    ):
        """
        Execute `p4 sync` on the given file path or changelist.
        If no arguments were given, will sync the whole workspace to latest changelist

        :param filepath: File path to sync
        :param changelist: Changelist number to sync. Can be "latest", so passed as string
        :param force: Force sync
        """
        sync_args = ["sync"]
        if force:
            sync_args.append("-f")

        if changelist is None or changelist == "latest":
            changelist_to_sync = None
        else:
            changelist_to_sync = int(changelist)

        if filepath:
            path_to_sync = (
                filepath if not changelist_to_sync else f"{filepath}@{changelist_to_sync}"
            )
            sync_args.append(path_to_sync)
        elif changelist_to_sync:
            sync_args.append(f"{self.spec['Stream']}/...@{changelist_to_sync}")

        logger.info(f"Running P4 sync with following arguments: {sync_args}")

        try:
            self.p4.run(sync_args)
        except Exception as e:
            logger.error(f"Error during p4 sync: {str(e)}")

    def where(self, depot_path: str) -> Optional[str]:
        """
        Convert depot path to local workspace path using `p4 where`

        :param depot_path: Depot path to convert

        :return: Local workspace path if found, None otherwise
        :rtype: Optional[str]
        """
        try:
            # Strip revision specification (@changelist or #revision) for where command
            clean_depot_path = depot_path.split("@")[0].split("#")[0]
            where_info = self.p4.run("where", clean_depot_path)
            if where_info and len(where_info) > 0:
                return where_info[0].get("path")
        except Exception as e:
            logger.error(f"Error converting depot path {depot_path} to local path: {e}")
        return None


def get_perforce_workspace_specification(
    port: Optional[str] = None, user: Optional[str] = None, client: Optional[str] = None
) -> Optional[dict]:
    """
    Get perforce workspace specification using provided port, user and client.
    If some of the parameters are missing, defaults will be used

    :param port: P4 server address
    :param user: P4 user name
    :param client: P4 client (workspace) name

    :return: P4 workspace specification dictionary if successful, None otherwise
    :rtype: Optional[dict]
    """

    p4 = PerforceConnection(port=port, user=user).p4
    if client:
        p4.client = client

    try:
        workspace_specification = p4.fetch_client(p4.client)
        return workspace_specification
    except P4Exception as e:
        logger.info(str(e))

    return None


def get_perforce_workspace_specification_template(
    port: Optional[str] = None, user: Optional[str] = None, client: Optional[str] = None
) -> dict:
    """
    Get perforce workspace specification template using provided port, user and client.
    Template built from perforce workspace specification by replacing any occurrences
    of workspace name with `{workspace_name}` token in specification fields

    Template Example:

    {
        "Client": "{workspace_name}",
        "Root": "D:/Perforce/j.doe-JDOE-PC_MeerkatDemo_Mainline",
        "Stream": "//MeerkatDemo/Mainline"
    }

    OR

    {
        "Client": "{workspace_name}",
        "Root": "D:/Perforce/j.doe-JDOE-PC_MeerkatDemo_Mainline",
        "View": [
            "//MeerkatDemo/Mainline/... //{workspace_name}/...",
            "//Plugins/Mainline/... //{workspace_name}/UE5/MeerkatDemo/Plugins...",
            "//Plugins/Dev/... //{workspace_name}/UE5/MeerkatDemo/Plugins/Dev...",
            "//OtherDepsDepot/Mainline/... //{workspace_name}/UE5/MeerkatDemo/Deps...",
        ]
    }

    :param port: P4 server address (optional)
    :param user: P4 user name (optional)
    :param client: P4 client (workspace) name (optional)

    :raises exceptions.PerforceWorkspaceNotFoundError: When not P4 workspace was found
    :return: P4 workspace specification dictionary if successful, None otherwise
    :rtype: Optional[dict]
    """

    workspace_specification = get_perforce_workspace_specification(port, user, client)
    if not isinstance(workspace_specification, dict):
        raise exceptions.PerforceWorkspaceNotFoundError(
            "No Perforce workspace found. Please check P4 environment and try again"
        )

    workspace_name = workspace_specification["Client"]
    workspace_root = workspace_specification["Root"]

    workspace_name_template = "{workspace_name}"

    workspace_specification_template = {"Client": workspace_name_template, "Root": workspace_root}

    if workspace_specification.get("Stream"):
        workspace_specification_template["Stream"] = workspace_specification["Stream"]
    elif workspace_specification.get("View"):
        view_regex = rf".*(\/\/{workspace_name}\/).*"
        view_templates = []
        for view in workspace_specification["View"]:
            match = re.match(view_regex, view)
            if match and len(match.groups()) == 1 and match.groups()[0] == f"//{workspace_name}/":
                view_templates.append(
                    view.replace(f"//{workspace_name}/", f"//{workspace_name_template}/")
                )
            else:
                view_templates.append(view)
        workspace_specification_template["View"] = view_templates

    return workspace_specification_template
