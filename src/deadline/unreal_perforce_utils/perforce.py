#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import re
from P4 import P4, P4Exception
from typing import Optional, Any

from deadline.unreal_logger import get_logger
from deadline.unreal_perforce_utils import exceptions


logger = get_logger()


class PerforceConnection:
    """
    Wrapper around the P4 object of p4python package

    P4 connection can be created by passing port, user, password and charset to the constructor
    or setting appropriate P4PORT, P4USER and P4PASSWD environment variables.

    .. note::
       Current connection properties will be used by default
    """

    def __init__(self, port: str = None, user: str = None, password: str = None, charset="none"):
        p4 = P4()
        p4.charset = charset

        p4_port = port or os.getenv("P4PORT")
        if p4_port:
            p4.port = p4_port

        p4_user = user or os.getenv("P4USER")
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

        p4_password = password or os.getenv("P4PASSWD")
        if p4_password:
            p4.password = p4_password
            p4.run_login()

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
        changes = self.p4.run("changes", "-c", self.p4.client, "-m", 1, "#have")
        if changes:
            return int(changes[0]["change"])
        return None

    def get_workspace_specification(self) -> Optional[dict]:
        return self.p4.fetch_client(self.p4.client)

    def get_depot_file_path(self, local_file_path: str) -> Optional[str]:
        """
        Return the file location on Perforce depot by running `p4 where <local_path>`

        :param local_file_path: Local file path to find in Depot

        :return: File path on Perforce depot if found, None otherwise
        :rtype: Optional[str]
        """

        local_file_path = local_file_path.replace("\\", "/")

        where_info = self.p4.run("where", local_file_path)
        # Should consist of 1 element because we give single path, but let's be defensive
        if len(where_info) == 1:
            return where_info[0].get("depotFile")

        return None


class PerforceClient:
    """
    Wrapper around the P4 workspace (client)
    """

    def __init__(self, connection: PerforceConnection, name: str, specification: dict = None):
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

    def sync(self, filepath: str = None, changelist: str = None, force: bool = False):
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
        print(f"Running P4 sync with following arguments: {sync_args}")

        self.p4.run(sync_args)


def get_perforce_workspace_specification(
    port: str = None, user: str = None, client: str = None
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
    port: str = None, user: str = None, client: str = None
) -> dict:
    """
    Get perforce workspace specification template using provided port, user and client.
    Template built from perforce workspace specification by replacing any occurrences
    of workspace name with `{workspace_name}` token in specification fields

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
