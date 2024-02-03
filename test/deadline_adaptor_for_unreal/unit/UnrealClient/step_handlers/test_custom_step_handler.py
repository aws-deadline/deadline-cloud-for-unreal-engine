#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import sys
import pytest
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch


from deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_custom_step_handler import UnrealCustomStepHandler


@pytest.fixture()
def unreal_custom_step_handler() -> UnrealCustomStepHandler:
    return UnrealCustomStepHandler()


class UnrealPackageMock(Mock):

    def log(self, message: str) -> None:
        print(message)


sys.modules['unreal'] = UnrealPackageMock()


class TestUnrealCustomStepHandler:

    @pytest.mark.parametrize(
        "script_path_map",
        [
            {
                'path': f'{Path(__file__).parent}/custom_scripts/valid_script.py',
                'is_module': True,
                'expected_exception': None
            },
            {
                'path':  f'{Path(__file__).parent}/custom_scripts/existed_not_valid_script.py',
                'is_module': True,
                'expected_exception': Exception
            },
            {
                'path': 'C:/path/to/not/existed/script.py',
                'is_module': False,
                'expected_exception': FileNotFoundError
            }
        ]
    )
    def test_validate_script_pass(
            self,
            unreal_custom_step_handler: UnrealCustomStepHandler,
            script_path_map: dict
    ) -> None:

        if script_path_map['expected_exception']:
            with pytest.raises(script_path_map['expected_exception']):
                validated_script = unreal_custom_step_handler.validate_script(
                    script_path=script_path_map['path']
                )
                assert isinstance(validated_script, ModuleType) == script_path_map['is_module']
        else:
            validated_script = unreal_custom_step_handler.validate_script(
                script_path=script_path_map['path']
            )

            assert isinstance(validated_script, ModuleType) == script_path_map['is_module']

    @pytest.mark.parametrize(
        "script_path_map",
        [
            {
                'args': {
                    'script_path': f'{Path(__file__).parent}/custom_scripts/valid_script.py',
                    'script_args': {'foo': 1, 'bar': 2}
                },
                'expected_result': True
            },
            {
                'args': {
                    'script_path': f'{Path(__file__).parent}/custom_scripts/existed_not_valid_script.py'
                },
                'expected_result': False
            },
            {
                'args': {
                    'script_path': 'C:/path/to/not/existed/script.py'
                },
                'expected_result': False
            }
        ]
    )
    def test_run_script(
            self,
            unreal_custom_step_handler: UnrealCustomStepHandler,
            script_path_map: dict
    ) -> None:

        real_result = unreal_custom_step_handler.run_script(
            args=script_path_map['args']
        )

        assert real_result == script_path_map['expected_result']
