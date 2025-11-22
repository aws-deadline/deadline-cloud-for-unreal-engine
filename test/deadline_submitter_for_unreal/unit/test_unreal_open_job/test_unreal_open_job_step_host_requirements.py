# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import Mock, MagicMock, patch

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step_host_requirements import (  # noqa: E402
    HostRequirementsHelper,
)


class TestHostRequirementsHelper:

    def test_u_host_requirements_to_openjd_host_requirements_with_os_requirements(self):
        """Test that u_host_requirements_to_openjd_host_requirements returns valid HostRequirementsTemplate with OS requirements"""
        # GIVEN
        mock_host_reqs = Mock()
        mock_host_reqs.run_on_all_worker_nodes = False
        mock_host_reqs.operating_system = "linux"
        mock_host_reqs.cpu_architecture = "x86_64"

        # Mock hardware requirements to return empty
        with patch.object(HostRequirementsHelper, "get_hardware_requirements", return_value=[]):
            # WHEN
            result = HostRequirementsHelper.u_host_requirements_to_openjd_host_requirements(
                mock_host_reqs
            )

            # THEN
            assert result is not None
            # Verify the result has the expected structure for OS requirements
            assert hasattr(result, "attributes")

    def test_u_host_requirements_to_openjd_host_requirements_with_hardware_requirements(self):
        """Test that u_host_requirements_to_openjd_host_requirements returns valid HostRequirementsTemplate with hardware requirements"""
        # GIVEN
        mock_host_reqs = Mock()
        mock_host_reqs.run_on_all_worker_nodes = False

        # Mock OS requirements to return empty
        with patch.object(HostRequirementsHelper, "get_os_requirements", return_value=[]):
            # Mock hardware requirements to return valid data
            hardware_reqs = [{"name": "amount.worker.vcpu", "min": 2}]
            with patch.object(
                HostRequirementsHelper, "get_hardware_requirements", return_value=hardware_reqs
            ):
                # WHEN
                result = HostRequirementsHelper.u_host_requirements_to_openjd_host_requirements(
                    mock_host_reqs
                )

                # THEN
                assert result is not None
                # Verify the result has the expected structure for hardware requirements
                assert hasattr(result, "amounts")

    def test_u_host_requirements_to_openjd_host_requirements_with_both_requirements(self):
        """Test that u_host_requirements_to_openjd_host_requirements returns valid HostRequirementsTemplate with both OS and hardware requirements"""
        # GIVEN
        mock_host_reqs = Mock()
        mock_host_reqs.run_on_all_worker_nodes = False

        # Mock both OS and hardware requirements
        os_reqs = [{"name": "attr.worker.os.family", "anyOf": ["linux"]}]
        hardware_reqs = [{"name": "amount.worker.vcpu", "min": 2}]

        with patch.object(HostRequirementsHelper, "get_os_requirements", return_value=os_reqs):
            with patch.object(
                HostRequirementsHelper, "get_hardware_requirements", return_value=hardware_reqs
            ):
                # WHEN
                result = HostRequirementsHelper.u_host_requirements_to_openjd_host_requirements(
                    mock_host_reqs
                )

                # THEN
                assert result is not None
                # Verify the result has both attributes and amounts
                assert hasattr(result, "attributes")
                assert hasattr(result, "amounts")

    def test_u_host_requirements_to_openjd_host_requirements_run_on_all_nodes(self):
        """Test that u_host_requirements_to_openjd_host_requirements returns None when run_on_all_worker_nodes is True"""
        # GIVEN
        mock_host_reqs = Mock()
        mock_host_reqs.run_on_all_worker_nodes = True

        # WHEN
        result = HostRequirementsHelper.u_host_requirements_to_openjd_host_requirements(
            mock_host_reqs
        )

        # THEN
        assert result is None
