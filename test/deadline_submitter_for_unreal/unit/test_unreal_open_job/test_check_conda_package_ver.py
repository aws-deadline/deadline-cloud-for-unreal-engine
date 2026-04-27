# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from typing import Any

from unittest.mock import MagicMock, patch

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (  # noqa: E402
    UnrealOpenJob,
)

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (  # noqa: E402
    OpenJobParameterNames,
)


class TestCheckCondaPackageVersion:

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.SystemLibrary.get_engine_version"
    )
    def test_check_conda_package_version_no_conda_packages_param(self, get_engine_version_mock):
        # GIVEN
        get_engine_version_mock.return_value = "5.4.0"

        job_parameter_values: list[dict[str, Any]] = []

        # WHEN
        assert UnrealOpenJob.check_conda_package_version(job_parameter_values)

        # THEN
        assert job_parameter_values == []

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.SystemLibrary.get_engine_version"
    )
    def test_check_conda_package_version_conda_packages_no_value(self, get_engine_version_mock):
        # GIVEN
        get_engine_version_mock.return_value = "5.4.0"

        job_parameter_values = [dict(name=OpenJobParameterNames.CONDA_PACKAGES, value="")]

        # WHEN
        assert UnrealOpenJob.check_conda_package_version(job_parameter_values)

        # THEN
        assert job_parameter_values[0].get("value") == "unrealengine=5.4"

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.SystemLibrary.get_engine_version"
    )
    def test_check_conda_package_version_no_unrealengine_pattern(self, get_engine_version_mock):
        # GIVEN
        get_engine_version_mock.return_value = "5.4.0"

        job_parameter_values = [
            dict(
                name=OpenJobParameterNames.CONDA_PACKAGES,
                value="somepackage=1.0",
            )
        ]

        # WHEN
        assert UnrealOpenJob.check_conda_package_version(job_parameter_values)

        # THEN
        assert job_parameter_values[0].get("value") == "unrealengine=5.4 somepackage=1.0"

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.SystemLibrary.get_engine_version"
    )
    def test_check_conda_package_version_versions_match(self, get_engine_version_mock):
        # GIVEN
        get_engine_version_mock.return_value = "5.4"

        job_parameter_values = [
            dict(name=OpenJobParameterNames.CONDA_PACKAGES, value="unrealengine=5.4")
        ]

        # WHEN
        assert UnrealOpenJob.check_conda_package_version(job_parameter_values)

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.SystemLibrary.get_engine_version"
    )
    def test_check_conda_package_version_versions_mismatch(self, get_engine_version_mock):
        # GIVEN
        get_engine_version_mock.return_value = "5.5"

        job_parameter_values = [
            dict(name=OpenJobParameterNames.CONDA_PACKAGES, value="unrealengine=5.4")
        ]

        # WHEN
        assert not UnrealOpenJob.check_conda_package_version(job_parameter_values)

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.SystemLibrary.get_engine_version"
    )
    def test_check_conda_package_version_minor_version_difference(self, get_engine_version_mock):
        # GIVEN
        get_engine_version_mock.return_value = "5.4.4"

        job_parameter_values = [
            dict(name=OpenJobParameterNames.CONDA_PACKAGES, value="unrealengine=5.4")
        ]

        # WHEN
        assert UnrealOpenJob.check_conda_package_version(job_parameter_values)

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.SystemLibrary.get_engine_version"
    )
    def test_does_not_auto_add_unrealengine_openjd(self, get_engine_version_mock):
        """Verify unrealengine-openjd is never auto-added to CondaPackages."""
        test_cases = [
            "",  # empty
            "unrealengine=5.7",  # engine only
            "unrealengine=5.7 somepkg=1.0",  # engine + other
        ]
        get_engine_version_mock.return_value = "5.7.0"

        for input_value in test_cases:
            job_parameter_values = [
                dict(name=OpenJobParameterNames.CONDA_PACKAGES, value=input_value)
            ]
            UnrealOpenJob.check_conda_package_version(job_parameter_values)
            result = job_parameter_values[0].get("value", "")
            assert (
                "unrealengine-openjd" not in result
            ), f"unrealengine-openjd was auto-added for input '{input_value}', got '{result}'"
