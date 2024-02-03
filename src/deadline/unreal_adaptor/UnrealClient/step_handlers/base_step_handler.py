#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import re
from typing import Optional
from abc import abstractmethod, ABC


class BaseStepHandler(ABC):

    def __init__(self):
        self.action_dict = dict(
            run_script=self.run_script,
            wait_result=self.wait_result
        )

    @abstractmethod
    def run_script(self, args: Optional[dict] = None) -> bool:
        """
        :param args: A dictionary that contains the arguments for running the script.
        :return: boolean indicating the script run successfully or not.

        This method is an abstract method that needs to be implemented by the extending class.
        It is responsible for executing a script using the provided arguments.
        """
        raise NotImplementedError("Abstract method, need to be implemented")

    @abstractmethod
    def wait_result(self, args: Optional[dict] = None) -> None:
        """
        :param args: A dictionary that contains the arguments for waiting.
        :return: None

        This method is an abstract method that needs to be implemented by the extending class.
        It is responsible for waiting result of the
        :meth:`deadline.unreal_adaptor.UnrealClient.step_handlers.base_step_handler.BaseStepHandler.run_script()`.
        """
        raise NotImplementedError("Abstract method, need to be implemented")

    @staticmethod
    @abstractmethod
    def regex_pattern_progress() -> list[re.Pattern]:
        """ Returns a list of regex Patterns that match the progress messages """
        raise NotImplementedError("Abstract method, need to be implemented")

    @staticmethod
    @abstractmethod
    def regex_pattern_complete() -> list[re.Pattern]:
        """ Returns a list of regex Patterns that match the complete messages """
        raise NotImplementedError("Abstract method, need to be implemented")

    @staticmethod
    @abstractmethod
    def regex_pattern_error() -> list[re.Pattern]:
        """ Returns a list of regex Patterns that match the errors messages """
        raise NotImplementedError("Abstract method, need to be implemented")
