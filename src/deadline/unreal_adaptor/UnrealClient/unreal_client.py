#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import sys
from http import HTTPStatus

from typing import Optional

if "PYTHONPATH" in os.environ:
    for p in os.environ["PYTHONPATH"].split(os.pathsep):
        if p not in sys.path:
            sys.path.insert(0, p.replace("\\", "/"))

for p in sys.path:
    print(p)

from openjd.adaptor_runtime_client.win_client_interface import WinClientInterface  # noqa: E402
from deadline.unreal_adaptor.UnrealClient.step_handlers.base_step_handler import (  # noqa: E402
    BaseStepHandler,
)
from deadline.unreal_adaptor.UnrealClient.step_handlers import get_step_handler_class  # noqa: E402


class UnrealClient(WinClientInterface):
    """
    Socket DCC client implementation for UnrealEngine that send requests for actions and execute them.
    """

    def __init__(self, socket_path: str) -> None:
        super().__init__(socket_path)
        self.handler: BaseStepHandler
        self.actions.update({"set_handler": self.set_handler})

    def set_handler(self, handler_dict: dict) -> None:
        """Set the current Step Handler"""

        handler_class = get_step_handler_class(handler_dict.get("handler", "base"))
        self.handler = handler_class()
        # This is an abstract method in a base class and isn't callable but the actual handler will implement this as callable.
        # TODO: Properly type hint self.handler
        self.actions.update(self.handler.action_dict)  # type: ignore

    def close(self, args: Optional[dict] = None) -> None:
        """Close the Unreal Engine"""
        import unreal

        unreal.log("Quit the Editor: normal shutdown")
        unreal.SystemLibrary.quit_editor()

    def graceful_shutdown(self, *args, **kwargs) -> None:
        """Close the Unreal Engine if the UnrealAdaptor terminate the client with 0s grace time"""
        import unreal

        unreal.log("Quit the Editor: graceful shutdown")
        unreal.SystemLibrary.quit_editor()

    def poll(self) -> None:
        """
        This function will poll the server for the next task. If the server is in between Subtasks
        (no actions in the queue), a backoff function will be called to add a delay between the
        requests.
        """
        status, reason, action = self._request_next_action()
        if status == HTTPStatus.OK:
            if action is not None:
                print(
                    f"Performing action: {action}",
                    flush=True,
                )
                self._perform_action(action)
        else:  # Any other status or reason
            print(
                f"ERROR: An error was raised when trying to connect to the server: {status} "
                f"{reason}",
                file=sys.stderr,
                flush=True,
            )


def main():
    import unreal

    socket_path = os.environ.get("UNREAL_ADAPTOR_SOCKET_PATH", "")
    print(f"SOCKET_PATH: {socket_path}")
    if not socket_path:
        raise OSError(
            "UnrealClient cannot connect to the Adaptor because the environment variable "
            "UNREAL_ADAPTOR_SOCKET_PATH does not exist"
        )

    if not os.path.exists(socket_path):
        raise OSError(
            "UnrealClient cannot connect to the Adaptor because the socket at the path defined by "
            "the environment variable UNREAL_ADAPTOR_SOCKET_PATH does not exist. Got: "
            f"{os.environ['UNREAL_ADAPTOR_SOCKET_PATH']}"
        )

    @unreal.uclass()
    class OnTickThreadExecutorImplementation(unreal.PythonGameThreadExecutor):
        """
        Python implementation of the OnTickThreadExecutor class that runs the
        :meth:`deadline.unreal_adaptor.UnrealClient.unreal_client.UnrealClient.poll()`
        """

        client = UnrealClient(socket_path)
        time_elapsed = unreal.uproperty(float)

        def _post_init(self):
            self.time_elapsed = 0

        @unreal.ufunction(override=True)
        def execute(self, delta_time: float):
            self.time_elapsed += delta_time
            if self.time_elapsed >= 1:
                self.time_elapsed = 0
                self.client.poll()


if __name__ == "__main__":  # pragma: no cover
    main()
