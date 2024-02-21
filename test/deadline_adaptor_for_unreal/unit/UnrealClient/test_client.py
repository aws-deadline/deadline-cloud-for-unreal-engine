#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import sys
import pytest
from unittest.mock import Mock, patch


from deadline.unreal_adaptor.UnrealClient.unreal_client import UnrealClient, main


class UnrealPackageMock(Mock):
    def log(self, message: str) -> None:
        print(message)


sys.modules["unreal"] = UnrealPackageMock()


class TestUnrealClient:
    @patch("deadline.unreal_adaptor.UnrealClient.unreal_client.WinClientInterface")
    def test_unreal_client(self, mock_winclient: Mock) -> None:
        """Tests that the unreal client can initialize, set a renderer and close"""

        client = UnrealClient(socket_path=str(999))
        client.set_handler(handler_dict=dict(handler="render"))
        client.close()

    @patch("deadline.unreal_adaptor.UnrealClient.unreal_client.os.path.exists")
    @patch.dict(os.environ, {"UNREAL_ADAPTOR_SOCKET_PATH": "socket_path"})
    @patch("deadline.unreal_adaptor.UnrealClient.unreal_client.UnrealClient.poll")
    @patch("deadline.unreal_adaptor.UnrealClient.unreal_client.WinClientInterface")
    def test_main(
        self,
        mock_httpclient: Mock,
        mock_poll: Mock,
        mock_exists: Mock,
    ) -> None:
        """Tests that the main method starts the unreal client polling method"""

        # GIVEN
        mock_exists.return_value = True

        # WHEN
        main()

        # THEN
        mock_exists.assert_called_once_with("socket_path")
        mock_poll.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    @patch("deadline.unreal_adaptor.UnrealClient.unreal_client.UnrealClient.poll")
    def test_main_no_server_socket(self, mock_poll: Mock) -> None:
        """Tests that the main method raises an OSError if no server socket is found"""
        # WHEN
        with pytest.raises(OSError) as exc_info:
            main()

        # THEN
        assert str(exc_info.value) == (
            "UnrealClient cannot connect to the Adaptor because the environment variable "
            "UNREAL_ADAPTOR_SOCKET_PATH does not exist"
        )
        mock_poll.assert_not_called()

    @patch.dict(os.environ, {"UNREAL_ADAPTOR_SOCKET_PATH": "/a/path/that/does/not/exist"})
    @patch("deadline.unreal_adaptor.UnrealClient.unreal_client.os.path.exists")
    @patch("deadline.unreal_adaptor.UnrealClient.unreal_client.UnrealClient.poll")
    def test_main_server_socket_not_exists(self, mock_poll: Mock, mock_exists: Mock) -> None:
        """Tests that the main method raises an OSError if the server socket does not exist"""
        # GIVEN
        mock_exists.return_value = False

        # WHEN
        with pytest.raises(OSError) as exc_info:
            main()

        # THEN
        mock_exists.assert_called_once_with(os.environ["UNREAL_ADAPTOR_SOCKET_PATH"])
        assert str(exc_info.value) == (
            "UnrealClient cannot connect to the Adaptor because the socket at the path defined by "
            "the environment variable UNREAL_ADAPTOR_SOCKET_PATH does not exist. Got: "
            f"{os.environ['UNREAL_ADAPTOR_SOCKET_PATH']}"
        )
        mock_poll.assert_not_called()
