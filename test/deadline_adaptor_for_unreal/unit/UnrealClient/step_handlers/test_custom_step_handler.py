# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
from pathlib import Path
from typing import Union
from types import ModuleType
from unittest.mock import MagicMock, patch


from deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_custom_step_handler import (
    UnrealCustomStepHandler,
)


unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock


@pytest.fixture()
def unreal_custom_step_handler() -> UnrealCustomStepHandler:
    return UnrealCustomStepHandler()


class TestUnrealCustomStepHandler:
    @pytest.mark.parametrize(
        "script_path_map",
        [
            {
                "path": f"{Path(__file__).parent}/custom_scripts/valid_script.py",
                "is_module": True,
                "expected_exception": None,
            },
            {
                "path": f"{Path(__file__).parent}/custom_scripts/existed_not_valid_script.py",
                "is_module": True,
                "expected_exception": Exception,
            },
            {
                "path": "C:/path/to/not/existed/script.py",
                "is_module": False,
                "expected_exception": FileNotFoundError,
            },
        ],
    )
    def test_validate_script_pass(
        self, unreal_custom_step_handler: UnrealCustomStepHandler, script_path_map: dict
    ) -> None:
        if script_path_map["expected_exception"]:
            with pytest.raises(script_path_map["expected_exception"]):
                validated_script = unreal_custom_step_handler.validate_script(
                    script_path=script_path_map["path"]
                )
                assert isinstance(validated_script, ModuleType) == script_path_map["is_module"]
        else:
            validated_script = unreal_custom_step_handler.validate_script(
                script_path=script_path_map["path"]
            )

            assert isinstance(validated_script, ModuleType) == script_path_map["is_module"]

    @pytest.mark.parametrize(
        "execute_command_output, expected_result", [(None, True), ((None, "Success output"), True)]
    )
    def test_run_script(
        self,
        unreal_custom_step_handler: UnrealCustomStepHandler,
        execute_command_output: Union[tuple, None],
        expected_result: bool,
    ) -> None:

        # GIVEN
        with patch(
            "unreal.PythonScriptLibrary.execute_python_command_ex",
            return_value=execute_command_output,
        ):
            # WHEN
            real_result = unreal_custom_step_handler.run_script(
                {"script_path": "path/to/script.py"}
            )

        # THEN
        assert real_result == expected_result

    def test_run_script_failed(self, unreal_custom_step_handler: UnrealCustomStepHandler) -> None:

        # GIVEN
        error_message = "Division by zero"
        error_traceback = "Traceback\nDivision by zero\n1/0"

        with patch(
            "unreal.PythonScriptLibrary.execute_python_command_ex",
            return_value=(error_message, error_traceback),
        ):
            # WHEN
            real_result = unreal_custom_step_handler.run_script(
                {"script_path": "path/to/script.py"}
            )

        # THEN
        assert real_result is False
