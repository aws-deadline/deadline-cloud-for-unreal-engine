# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import re
import sys
import inspect
import importlib
import traceback
from pathlib import Path
from typing import Optional
from types import ModuleType

from .base_step_handler import BaseStepHandler
from deadline.unreal_logger import get_logger


logger = get_logger()


class UnrealCustomStepHandler(BaseStepHandler):
    @staticmethod
    def regex_pattern_progress() -> list[re.Pattern]:
        return [re.compile(".*Custom Step Executor: Progress: ([0-9.]+)")]

    @staticmethod
    def regex_pattern_complete() -> list[re.Pattern]:
        return [re.compile(".*Custom Step Executor: Complete"), re.compile(".*QUIT EDITOR")]

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
        Executing a script using the provided arguments by calling the
        https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PythonScriptLibrary?application_version=5.4#unreal.PythonScriptLibrary.execute_python_command_ex

        :param args: A dictionary that contains the arguments for running the script.
        :return: boolean indicating the script run successfully or not.
        """

        try:
            import unreal

            result = unreal.PythonScriptLibrary.execute_python_command_ex(
                f"{args['script_path']} {args.get('script_args', '')}",
                execution_mode=unreal.PythonCommandExecutionMode.EXECUTE_FILE,
                file_execution_scope=unreal.PythonFileExecutionScope.PUBLIC,
            )

            if result:
                failure, _ = result

                # If the command ran successfully, this will return None else the
                # failure
                # https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/PythonScriptLibrary?application_version=5.4#unreal.PythonScriptLibrary.execute_python_command_ex
                if failure:
                    raise RuntimeError(failure)

            logger.info(f"Custom Step Executor Result: {result}")
            return True
        except KeyError as e:
            logger.error(traceback.format_exc())
            logger.error(
                f"Custom Step Executor: Error: {str(e)}. "
                f"It is possible `script_path` missed from args {args}"
            )
            return False
        except RuntimeError as e:
            logger.error(traceback.format_exc())
            logger.error(
                f"Custom Step Executor: Error: {str(e)}"
                f"Error occurred while executing the given script {args.get('script_path')} "
                f"with args {args.get('script_args')} via "
                f"unreal.PythonScriptLibrary.execute_python_command_ex"
            )
            return False
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(
                f"Custom Step Executor: Error: {str(e)}"
                f"Unexpected error occurred while executing the given script "
                f"{args.get('script_path')}"
            )
            return False

    def wait_result(self, args: Optional[dict] = None) -> None:  # pragma: no cover
        """
        :param args: A dictionary that contains the arguments for waiting.
        :return: None

        It is responsible for waiting result of the
        :meth:`deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_custom_step_handler.UnrealCustomStepHandler.run_script()`.
        """

        logger.info("Render wait start")
        logger.info("Render wait finish")
