from P4 import P4, P4Exception
from typing import Optional, Any


class PerforceApi:

    def __init__(self, port: str = None, user: str = None, password: str = None, client: str = None, charset="none"):

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
            raise Exception(f'Could not connect Perforce server {p4.port} as user {p4.user}\n{str(e)}')

        if password:
            p4.password = password
            p4.run_login()

        self.p4 = p4

    def get_info(self) -> dict[str, Any]:
        return self.p4.run('info')[0]

    def get_stream_path(self) -> Optional[str]:
        return self.get_info().get('clientStream')

    def get_client_root(self) -> Optional[str]:
        client_root = self.get_info().get('clientRoot')
        if client_root:
            client_root = client_root.replace('\\', '/')
        return client_root

    def get_latest_changelist_number(self) -> Optional[int]:
        changes = self.p4.run('changes', '-c', self.p4.client, '-m', 1, '#have')
        if changes:
            return int(changes[0]['change'])

    def get_workspace_specification(self) -> Optional[dict]:
        return self.p4.fetch_client(self.p4.client)
