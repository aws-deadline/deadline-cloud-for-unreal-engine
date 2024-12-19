#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest
from unittest.mock import patch, MagicMock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_parameters_consistency import (
    ParametersConsistencyChecker,
    ParametersConsistencyCheckResult,
)

from test.deadline_submitter_for_unreal import fixtures


class TestParametersConsistencyChecker:

    @pytest.mark.parametrize(
        "input_left, input_right, output_left, output_right",
        [
            (
                [("paramA", "INT"), ("paramB", "STRING")],
                [("paramA", "INT"), ("paramB", "STRING")],
                [],
                [],
            ),
            (
                [("paramA", "INT"), ("paramB", "STRING")],
                [("paramA", "INT")],
                [],
                [("paramB", "STRING")],
            ),
            (
                [("paramB", "STRING")],
                [("paramA", "INT"), ("paramB", "STRING")],
                [("paramA", "INT")],
                [],
            ),
            (
                [("paramA", "INT"), ("paramB", "STRING"), ("paramC", "FLOAT")],
                [("paramB", "STRING"), ("paramC", "FLOAT"), ("paramD", "PATH")],
                [("paramD", "PATH")],
                [("paramA", "INT")],
            ),
            (
                [("paramA", "INT"), ("paramB", "STRING")],
                [("paramA", "INT"), ("paramB", "FLOAT")],
                [("paramB", "FLOAT")],
                [("paramB", "STRING")],
            ),
        ],
    )
    def test_symmetric_difference(self, input_left, input_right, output_left, output_right):
        # GIVEN
        checker = ParametersConsistencyChecker()

        # WHEN
        missed_in_left, missed_in_right = checker.symmetric_difference(input_left, input_right)

        # THEN
        assert missed_in_left == output_left
        assert missed_in_right == output_right

    @pytest.mark.parametrize(
        "yaml_parameters, data_asset_parameters, expected_result",
        [
            (
                [("paramA", "INT"), ("paramB", "STRING")],
                [("paramA", "INT"), ("paramB", "STRING")],
                ParametersConsistencyCheckResult(True, "Parameters are consistent"),
            ),
            (
                [("paramA", "INT"), ("paramB", "STRING")],
                [("paramA", "INT")],
                ParametersConsistencyCheckResult(
                    False, "YAML's parameters missed in Data Asset: paramB (STRING)"
                ),
            ),
            (
                [("paramB", "STRING")],
                [("paramA", "INT"), ("paramB", "STRING")],
                ParametersConsistencyCheckResult(
                    False, "Data Asset's parameters missed in YAML: paramA (INT)"
                ),
            ),
            (
                [("paramA", "INT"), ("paramB", "STRING"), ("paramC", "FLOAT")],
                [("paramB", "STRING"), ("paramC", "FLOAT"), ("paramD", "PATH")],
                ParametersConsistencyCheckResult(
                    False,
                    "Data Asset's parameters missed in YAML: paramD (PATH)\n"
                    "YAML's parameters missed in Data Asset: paramA (INT)",
                ),
            ),
            (
                [("paramA", "INT"), ("paramB", "STRING")],
                [("paramA", "INT"), ("paramB", "FLOAT")],
                ParametersConsistencyCheckResult(
                    False,
                    "Data Asset's parameters missed in YAML: paramB (FLOAT)\n"
                    "YAML's parameters missed in Data Asset: paramB (STRING)",
                ),
            ),
        ],
    )
    def test_check_parameters_consistency(
        self, yaml_parameters, data_asset_parameters, expected_result
    ):
        # GIVEN
        checker = ParametersConsistencyChecker()

        # WHEN
        result = checker.check_parameters_consistency(yaml_parameters, data_asset_parameters)

        assert result.passed == expected_result.passed
        assert result.reason == expected_result.reason

    @pytest.mark.parametrize(
        "missed_yaml, missed_data_asset, yaml_parameters, data_asset_parameters, output_fixed",
        [
            (
                [],
                [],
                [{"name": "paramA", "type": "INT"}, {"name": "paramB", "type": "STRING"}],
                [{"name": "paramA", "type": "INT"}, {"name": "paramB", "type": "STRING"}],
                [{"name": "paramA", "type": "INT"}, {"name": "paramB", "type": "STRING"}],
            ),
            (
                [],
                [("paramB", "STRING")],
                [{"name": "paramA", "type": "INT"}, {"name": "paramB", "type": "STRING"}],
                [{"name": "paramA", "type": "INT"}],
                [{"name": "paramA", "type": "INT"}, {"name": "paramB", "type": "STRING"}],
            ),
            (
                [("paramA", "INT")],
                [],
                [{"name": "paramB", "type": "STRING"}],
                [{"name": "paramA", "type": "INT"}, {"name": "paramB", "type": "STRING"}],
                [{"name": "paramB", "type": "STRING"}],
            ),
            (
                [("paramD", "PATH")],
                [("paramA", "INT")],
                [
                    {"name": "paramA", "type": "INT"},
                    {"name": "paramB", "type": "STRING"},
                    {"name": "paramC", "type": "FLOAT"},
                ],
                [
                    {"name": "paramB", "type": "STRING"},
                    {"name": "paramC", "type": "FLOAT"},
                    {"name": "paramD", "type": "PATH"},
                ],
                [
                    {"name": "paramA", "type": "INT"},
                    {"name": "paramB", "type": "STRING"},
                    {"name": "paramC", "type": "FLOAT"},
                ],
            ),
            (
                [("paramB", "FLOAT")],
                [("paramB", "STRING")],
                [{"name": "paramA", "type": "INT"}, {"name": "paramB", "type": "STRING"}],
                [{"name": "paramA", "type": "INT"}, {"name": "paramB", "type": "FLOAT"}],
                [{"name": "paramA", "type": "INT"}, {"name": "paramB", "type": "STRING"}],
            ),
            (
                [],
                [("paramB", "STRING")],
                [
                    {"name": "paramA", "type": "INT"},
                    {"name": "paramB", "type": "STRING", "default": "foo"},
                ],
                [{"name": "paramA", "type": "INT"}],
                [
                    {"name": "paramA", "type": "INT"},
                    {"name": "paramB", "type": "STRING", "default": "foo"},
                ],
            ),
        ],
    )
    def test_fix_parameters_consistency(
        self, missed_yaml, missed_data_asset, yaml_parameters, data_asset_parameters, output_fixed
    ):
        # GIVEN
        checker = ParametersConsistencyChecker()

        # WHEN
        fixed = checker.fix_parameters_consistency(
            missed_yaml,
            missed_data_asset,
            yaml_parameters,
            data_asset_parameters,
        )

        # THEN
        assert fixed == output_fixed

    @pytest.mark.parametrize(
        "missed_yaml, missed_data_asset, yaml_variables, data_asset_variables, output_fixed",
        [
            (
                [],
                [],
                {"varA": "valueA", "varB": "valueB"},
                {"varA": "valueA", "varB": "valueB"},
                {"varA": "valueA", "varB": "valueB"},
            ),
            (
                [],
                [("varB", "VARIABLE")],
                {"varA": "valueA", "varB": "valueB"},
                {"varA": "valueA"},
                {"varA": "valueA", "varB": "valueB"},
            ),
            (
                [("varA", "VARIABLE")],
                [],
                {"varB": "valueB"},
                {"varA": "valueA", "varB": "valueB"},
                {"varB": "valueB"},
            ),
            (
                [("varC", "VARIABLE")],
                [("varA", "VARIABLE")],
                {"varA": "valueA", "varB": "valueB"},
                {"varB": "valueB", "varC": "valueC"},
                {"varA": "valueA", "varB": "valueB"},
            ),
        ],
    )
    def test_fix_variables_consistency(
        self, missed_yaml, missed_data_asset, yaml_variables, data_asset_variables, output_fixed
    ):
        # GIVEN
        checker = ParametersConsistencyChecker()

        # WHEN
        fixed = checker.fix_variables_consistency(
            missed_yaml, missed_data_asset, yaml_variables, data_asset_variables
        )

        # THEN
        assert fixed == output_fixed

    def test_fix_job_parameters_consistency(self):
        # GIVEN
        checker = ParametersConsistencyChecker()
        expected_fixed_parameters = [
            {"name": p["name"], "type": p["type"], "default": p["default"]}
            for p in fixtures.f_job_template_default()["parameterDefinitions"]
        ]

        # WHEN
        with patch("yaml.safe_load", MagicMock(side_effect=[fixtures.f_job_template_default()])):
            with patch("builtins.open", MagicMock()):
                fixed = checker.fix_job_parameters_consistency("", [])

        # THEN
        assert fixed == expected_fixed_parameters

    def test_fix_step_parameters_consistency(self):
        # GIVEN
        checker = ParametersConsistencyChecker()
        expected_fixed_parameters = [
            {"name": p["name"], "type": p["type"]}
            for p in fixtures.f_step_template_default()["parameterSpace"][
                "taskParameterDefinitions"
            ]
        ]

        # WHEN
        with patch("yaml.safe_load", MagicMock(side_effect=[fixtures.f_step_template_default()])):
            with patch("builtins.open", MagicMock()):
                fixed = checker.fix_step_parameters_consistency("", [])

        # THEN
        assert fixed == expected_fixed_parameters

    def test_fix_environment_variables_consistency(self):
        # GIVEN
        checker = ParametersConsistencyChecker()

        # WHEN
        with patch(
            "yaml.safe_load", MagicMock(side_effect=[fixtures.f_environment_template_default()])
        ):
            with patch("builtins.open", MagicMock()):
                fixed = checker.fix_environment_variables_consistency("", {})

        # THEN
        assert fixed == fixtures.f_environment_template_default()["variables"]
