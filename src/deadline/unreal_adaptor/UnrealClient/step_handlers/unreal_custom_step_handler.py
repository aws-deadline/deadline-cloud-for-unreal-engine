#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import re
import sys
import inspect
import importlib
import traceback
from pathlib import Path
from typing import Optional
from types import ModuleType

from .base_step_handler import BaseStepHandler


class UnrealCustomStepHandler(BaseStepHandler):
    @staticmethod
    def regex_pattern_progress() -> list[re.Pattern]:
        return [re.compile(".*Custom Step Executor: Progress: ([0-9.]+)")]

    @staticmethod
    def regex_pattern_complete() -> list[re.Pattern]:
        return [re.compile(".*Custom Step Executor: Complete")]

    @staticmethod
    def regex_pattern_error() -> list[re.Pattern]:
        return [re.compile(".*Exception:.*|.*Custom Step Executor: Error:.*")]

    @staticmethod
    def validate_script(script_path: str) -> ModuleType:
        """
        This method is responsible for validating the script

        :param script_path: Path of the script to validate
        :return: If script is valid, returns its as module, None otherwise
        """

        _script_path = Path(script_path)

        if not _script_path.exists() or not _script_path.is_file():
            raise FileNotFoundError(f"Script {script_path} does not exist or it is not a file")

        sys.path.append(str(_script_path.parent))
        script_module = importlib.import_module(_script_path.stem)

        has_main_method = False

        for name, obj in inspect.getmembers(script_module, predicate=inspect.isfunction):
            if name == "main":
                has_main_method = True
                break

        if not has_main_method:
            raise Exception("Invalid script. Please check the script have the 'main' method.")

        return script_module

    def run_script(self, args: dict) -> bool:
        """
        Executing a script using the provided arguments.

        :param args: A dictionary that contains the arguments for running the script.
        :return: boolean indicating the script run successfully or not.
        """

        import unreal

        try:
            script_module = UnrealCustomStepHandler.validate_script(script_path=args["script_path"])
            script_args = args.get("script_args", {})
            result = script_module.main(**script_args)
            unreal.log(f"Custom Step Executor: Complete: {result}")
            return True
        except Exception as e:
            unreal.log(
                f"Custom Step Executor: Error: "
                f'Error occured while executing the given script {args.get("script_path")}: {str(e)}\n'
            )
            unreal.log(traceback.format_exc())
            return False

    def wait_result(self, args: Optional[dict] = None) -> None:
        """
        :param args: A dictionary that contains the arguments for waiting.
        :return: None

        It is responsible for waiting result of the
        :meth:`deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_custom_step_handler.UnrealCustomStepHandler.run_script()`.
        """
        import unreal

        unreal.log("Render wait start")
        unreal.log("Render wait finish")
