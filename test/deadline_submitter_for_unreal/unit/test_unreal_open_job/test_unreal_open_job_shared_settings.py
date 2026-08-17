# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
from unittest.mock import MagicMock, patch

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_shared_settings import (  # noqa: E402
    JobSharedSettings,
)


class TestJobSharedSettings:

    @patch("unreal.DeadlineCloudJobSharedSettingsStruct")
    def test_from_u_deadline_cloud_job_shared_settings(self, u_settings_mock: MagicMock):
        # GIVEN
        u_settings_mock.initial_state = "READY"
        u_settings_mock.maximum_failed_tasks_count = 50
        u_settings_mock.maximum_retries_per_task = 50
        u_settings_mock.priority = 100

        # WHEN
        settings = JobSharedSettings.from_u_deadline_cloud_job_shared_settings(u_settings_mock)

        # THEN
        assert settings.get_initial_state() == u_settings_mock.initial_state
        assert settings.get_max_failed_tasks_count() == u_settings_mock.maximum_failed_tasks_count
        assert settings.get_max_retries_per_task() == u_settings_mock.maximum_retries_per_task
        assert settings.get_priority() == u_settings_mock.priority

    def test_getters_reflect_direct_parameter_values_mutation(self):
        """parameter_values is the single source of truth: even a caller mutating the
        serialized list directly (e.g. legacy code) is reflected by the typed getters."""
        # GIVEN
        settings = JobSharedSettings()

        # WHEN
        for parameter_value in settings.parameter_values:
            if parameter_value["name"] == "deadline:priority":
                parameter_value["value"] = 75

        # THEN
        assert settings.get_priority() == 75
