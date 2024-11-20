#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import MagicMock

import pytest

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step_host_requirements import (  # noqa: E402
    HostRequirements,
)


class TestHostRequirements:

    @pytest.mark.parametrize("in_setting, out_setting", [(True, True), (False, False)])
    def test_run_on_all_worker_nodes(self, in_setting: bool, out_setting: bool):
        # GIVEN
        host_requirements = HostRequirements(run_on_all_worker_nodes=in_setting)

        # WHEN
        run_on_all_worker_nodes = host_requirements.run_on_all_worker_nodes

        # THEN
        assert run_on_all_worker_nodes == out_setting

    @pytest.mark.parametrize(
        "amount_requirement, expected_valid",
        [
            ({"name": "cpu", "min": 0, "max": 100}, True),
            ({"name": "cpu", "min": 0}, True),
            ({"name": "cpu", "max": 0}, True),
            ({"max": 100, "min": 0}, False),
            ({"name": "cpu"}, False),
            ({"min": "cpu"}, False),
            ({"max": "cpu"}, False),
            ({}, False),
        ],
    )
    def test__amount_requirement_is_valid(self, amount_requirement: dict, expected_valid: bool):
        # GIVEN
        host_requirements = HostRequirements()

        # WHEN
        is_valid = host_requirements._amount_requirement_is_valid(amount_requirement)

        # THEN
        assert is_valid == expected_valid

    @pytest.mark.parametrize(
        "interval, name, scaling_factor, expected_result",
        [
            ((1, 100), "Test", 1, {"name": "Test", "min": 1, "max": 100}),
            ((1, 100), "Test", 20, {"name": "Test", "min": 20, "max": 2000}),
            ((0, 100), "Test", 10, {"name": "Test", "max": 1000}),
            ((100, 0), "Test", 10, {"name": "Test", "min": 1000}),
            ((1, 1), None, 1, {"name": None, "min": 1, "max": 1}),
            ((0, 0), "Test", 1, {}),
        ],
    )
    def test__get_amount_requirement(
        self, interval: tuple[int, int], name: str, scaling_factor: int, expected_result: dict
    ):
        # GIVEN
        host_requirements = HostRequirements()

        # WHEN
        amount_requirement = host_requirements._get_amount_requirement(
            interval, name, scaling_factor
        )

        # THEN
        assert amount_requirement == expected_result
