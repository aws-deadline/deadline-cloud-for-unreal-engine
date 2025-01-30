from P4 import P4, P4Exception
from typing import Optional, Any

from deadline.unreal_submitter import exceptions


class PerforceApi:
    """
    API for working with Perforce
    """

    def __init__(
        self,
        port: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        client: Optional[str] = None,
        charset: str = "none",
    ):
        """
        Create instance of PerforceApi. All parameters are optional,
        if some of them are not provided, will use default values of current global P4 connection.

        :param port: Port to connect to
        :param user: User to connect as
        :param password: Password to authenticate with
        :param client: Client (workspace name) to operate with
        :param charset: Character set used for translation of Unicode files

        """

        p4 = P4()
        p4.charset = charset

        if port:
            p4.port = port

        if user:
            p4.user = user

        if client:
            p4.client = client

        try:
            p4.connect()
        except P4Exception as e:
            raise exceptions.PerforceConnectionError(
                f"Could not connect Perforce server {p4.port} as user {p4.user}\n{str(e)}"
            )

        if password:
            p4.password = password
            p4.run_login()

        self.p4 = p4

    def get_info(self) -> dict[str, Any]:
        """
        Run `p4 info` and return its output as a dictionary that contains information about
        client and server:
            1. Client name, root, stream, etc.
            2. Server address, root, version, id, license, etc.

        :return: Dictionary of info about the current connection
        :rtype: dict[str, Any]
        """

        return self.p4.run("info")[0]

    def get_stream_path(self) -> Optional[str]:
        """
        Get client stream path from p4 info output, e.g. //MyProject/Mainline

        :return: Client stream path
        :rtype: Optional[str]
        """

        return self.get_info().get("clientStream")

    def get_client_root(self) -> Optional[str]:
        """
        Get client root from p4 info output, e.g. C:/users/j.doe/Perforce/MyProject_workspace_dir

        :return: Client root path
        :rtype: Optional[str]
        """

        client_root = self.get_info().get("clientRoot")
        if client_root:
            client_root = client_root.replace("\\", "/")
        return client_root

    def get_latest_changelist_number(self) -> Optional[int]:
        """
        Get latest changelist number from `p4 changes -c <client> -m 1 #have` command output

        :return: Latest changelist number
        :rtype: Optional[int]
        """

        changes = self.p4.run("changes", "-c", self.p4.client, "-m", 1, "#have")
        if changes:
            return int(changes[0]["change"])
        return None

    def get_workspace_specification(self) -> Optional[dict]:
        """
        Run `p4 client -o <client>` and return its output as a dictionary that contains information about
        workspace specification:
            1. Client name, host, root
            2. Sync and Submit options
            3. Stream
            4. Workspace View

        :return: Workspace specification
        :rtype: Optional[dict]
        """

        return self.p4.fetch_client(self.p4.client)
