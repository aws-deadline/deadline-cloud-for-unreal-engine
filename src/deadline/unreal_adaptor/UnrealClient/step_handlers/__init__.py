#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from typing import Type, Union

from .base_step_handler import BaseStepHandler
from .unreal_render_step_handler import UnrealRenderStepHandler
from .unreal_custom_step_handler import UnrealCustomStepHandler

__all__ = ["BaseStepHandler", "get_step_handler_class"]


def get_step_handler_class(
    handler: str = "base",
) -> Type[Union[BaseStepHandler, UnrealCustomStepHandler, UnrealRenderStepHandler]]:
    """
    Returns the step handler instance for the given handler name.

    Args:
        handler (str, optional): The handler name to get the handler instance of.
            Defaults to "BaseStepHandler".

    Returns the BaseStepHandler instance for the given handler name.
    """

    handlers_map = dict(
        base=BaseStepHandler, render=UnrealRenderStepHandler, custom=UnrealCustomStepHandler
    )

    print(
        f'Trying to get step handler class, defined as "{handler}" in the handlers map: {handlers_map}'
    )
    handler_class = handlers_map.get(handler, BaseStepHandler)
    print(f"Got step handler class: {handler_class}")

    return handler_class
