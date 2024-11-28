#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import MagicMock, patch

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
            (None, "Test", 1, {}),
            (tuple([0]), "Test", 1, {}),
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

    @pytest.mark.parametrize(
        "operating_sys, arch, expected_keys",
        [
            (None, None, []),
            ("windows", "x86_64", ["attr.worker.os.family", "attr.worker.cpu.arch"]),
            ("linux", "arm64", ["attr.worker.os.family", "attr.worker.cpu.arch"]),
            ("windows", None, ["attr.worker.os.family"]),
            (None, "x86_64", ["attr.worker.cpu.arch"]),
        ],
    )
    def test__get_os_requirements(self, operating_sys, arch, expected_keys):
        # GIVEN
        host_requirements = HostRequirements(operating_system=operating_sys, cpu_architecture=arch)

        # WHEN
        os_requirements = host_requirements._get_os_requirements()

        # THEN
        assert [r.get("name") for r in os_requirements] == expected_keys

    @pytest.mark.parametrize(
        "cpu, cpu_mem, gpu, gpu_mem, scratch_space, expected_keys",
        [
            ((0, 0), (0, 0), (0, 0), (0, 0), (0, 0), []),
            ((1, 2), (0, 0), (0, 0), (0, 0), (0, 0), ["amount.worker.vcpu"]),
            (
                (0, 1),
                (1, 1),
                (1, 1),
                (1, 1),
                (1, 1),
                [
                    "amount.worker.vcpu",
                    "amount.worker.memory",
                    "amount.worker.gpu",
                    "amount.worker.gpu.memory",
                    "amount.worker.disk.scratch",
                ],
            ),
        ],
    )
    def test__get_hardware_requirements(
        self, cpu, cpu_mem, gpu, gpu_mem, scratch_space, expected_keys
    ):
        # GIVEN
        host_requirements = HostRequirements(
            cpu_count=cpu,
            cpu_memory_gb=cpu_mem,
            gpu_count=gpu,
            gpu_memory_gb=gpu_mem,
            scratch_space=scratch_space,
        )

        # WHEN
        hardware_requirements = host_requirements._get_hardware_requirements()

        # THEN
        assert [r["name"] for r in hardware_requirements] == expected_keys

    @pytest.mark.parametrize(
        "os_requirements, hardware_requirements, expected_keys",
        [
            (None, None, []),
            (
                [{"name": "attr.worker.os.family", "anyOf": ["windows"]}],
                [{"name": "amount.worker.vcpu", "min": 1, "max": 1}],
                ["attributes", "amounts"],
            ),
            ([{"name": "attr.worker.os.family", "anyOf": ["windows"]}], None, ["attributes"]),
            (None, [{"name": "amount.worker.vcpu", "min": 1, "max": 1}], ["amounts"]),
        ],
    )
    def test_as_dict(self, os_requirements, hardware_requirements, expected_keys):
        # GIVEN
        host_requirements = HostRequirements()
        with patch.object(host_requirements, "_get_os_requirements", return_value=os_requirements):
            with patch.object(
                host_requirements, "_get_hardware_requirements", return_value=hardware_requirements
            ):
                # WHEN
                result = host_requirements.as_dict()

        # THEN
        assert list(result.keys()) == expected_keys
