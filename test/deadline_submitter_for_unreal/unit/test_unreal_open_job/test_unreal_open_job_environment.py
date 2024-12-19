#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import patch, MagicMock, Mock

import pytest
from openjd.model.v2023_09 import Environment

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (  # noqa: E402
    UnrealOpenJobEnvironment,
)


class TestUnrealOpenJobEnvironment:

    @patch("builtins.open", MagicMock())
    @patch("yaml.safe_load", MagicMock(side_effect=[{"variables": {"varA": "valueA"}}]))
    def test__check_parameters_consistency_passed(self):
        # GIVEN
        openjd_env = UnrealOpenJobEnvironment(file_path="", variables={"varA": "valueA"})

        # WHEN
        consistency_check_result = openjd_env._check_parameters_consistency()

        # THEN
        assert consistency_check_result.passed
        assert "Parameters are consistent" in consistency_check_result.reason

    @patch("builtins.open", MagicMock())
    @patch("yaml.safe_load", MagicMock(side_effect=[{"variables": {}}]))
    def test__check_parameters_consistency_failed_yaml(self):
        # GIVEN
        openjd_env = UnrealOpenJobEnvironment(file_path="", variables={"varA": "valueA"})

        # WHEN
        consistency_check_result = openjd_env._check_parameters_consistency()

        # THEN
        assert not consistency_check_result.passed
        assert "Data Asset's parameters missed in YAML" in consistency_check_result.reason

    @patch("builtins.open", MagicMock())
    @patch("yaml.safe_load", MagicMock(side_effect=[{"variables": {"varA": "valueA"}}]))
    def test__check_parameters_consistency_failed_data_asset(self):
        # GIVEN
        openjd_env = UnrealOpenJobEnvironment(file_path="", variables={})

        # WHEN
        consistency_check_result = openjd_env._check_parameters_consistency()

        # THEN
        assert not consistency_check_result.passed
        assert "YAML's parameters missed in Data Asset" in consistency_check_result.reason

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"variables": {"varA": "valueA"}},
    )
    def test__build_template(self, get_template_object_mock: Mock):
        # GIVEN
        openjd_entity = UnrealOpenJobEnvironment(
            file_path="", name="TestEnv", variables={"varA": "valueA"}
        )

        # WHEN
        openjd_template = openjd_entity._build_template()

        # THEN
        assert isinstance(openjd_template, Environment)

    def test_from_data_asset(self):
        # GIVEN
        env_data_asset = MagicMock()
        env_data_asset.path_to_template.file_path = ""
        env_data_asset.name = "StepA"

        variables_mock = MagicMock()
        variables_mock.variables = {"varA": "valA", "varB": "valB"}

        env_data_asset.variables = variables_mock

        # WHEN
        open_job_environment = UnrealOpenJobEnvironment.from_data_asset(env_data_asset)

        # THEN
        assert isinstance(open_job_environment, UnrealOpenJobEnvironment)
        assert open_job_environment.name == env_data_asset.name
        assert env_data_asset.variables.variables == open_job_environment._variables

    @pytest.mark.parametrize("variables", [{"varA": "valA"}, {}])
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={},
    )
    def test_variables_getter(self, get_template_object_mock: Mock, variables: dict[str, str]):
        # GIVEN
        open_job_environment = UnrealOpenJobEnvironment(variables=variables)

        # WHEN
        env_variables = open_job_environment.variables

        # THEN
        assert env_variables == variables

    @pytest.mark.parametrize("variables", [{"varA": "valA"}, {}])
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={},
    )
    def test_variables_setter(self, get_template_object_mock: Mock, variables: dict[str, str]):
        # GIVEN
        open_job_environment = UnrealOpenJobEnvironment()

        # WHEN
        open_job_environment.variables = variables

        # THEN
        assert isinstance(open_job_environment.variables, dict)
        assert open_job_environment.variables == variables

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={"variables": {"MISSED_VAR": "MissedValue"}},
    )
    def test__create_missing_variables_from_template(self, get_template_object_mock: Mock):
        # WHEN
        open_job_environment = UnrealOpenJobEnvironment()

        # THEN
        yaml_vars = get_template_object_mock.return_value["variables"]
        for key, value in yaml_vars.items():
            assert key in open_job_environment.variables
            assert open_job_environment.variables.get(key) == value
