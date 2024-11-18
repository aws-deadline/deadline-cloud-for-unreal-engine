#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import unittest

unittest.SkipTest("Not ready yet")

import sys
import time
from unittest.mock import Mock, MagicMock, patch

import pytest
from deadline.job_attachments.progress_tracker import ProgressReportMetadata, ProgressStatus


sys.modules["unreal"] = MagicMock()


def create_job_from_bundle_mock(
    job_bundle_dir=None,
    hashing_progress_callback=None,
    upload_progress_callback=None,
    create_job_result_callback=None,
):
    time.sleep(1)

    hashing_progress_callback(
        ProgressReportMetadata(
            status=ProgressStatus.PREPARING_IN_PROGRESS,
            progress=100.0,
            transferRate=1000.0,
            progressMessage="Done",
        )
    )
    upload_progress_callback(
        ProgressReportMetadata(
            status=ProgressStatus.UPLOAD_IN_PROGRESS,
            progress=100.0,
            transferRate=1000.0,
            progressMessage="Done",
        )
    )
    create_job_result_callback()
    return "job_id_1"


class TestUnrealSubmitter:

    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    @patch("deadline.unreal_submitter.unreal_open_job.open_job_description.OpenJobDescription")
    def test_add_job(self, job_description_mock: Mock, mock_telemetry_client: Mock):
        # GIVEN
        from deadline.unreal_submitter.submitter import UnrealSubmitter

        mrq_job = MagicMock()
        submitter = UnrealSubmitter()

        # WHEN
        submitter.add_job(mrq_job)

        # THEN
        assert len(submitter._jobs) == 1

    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    @patch(
        "deadline.unreal_submitter.submitter.create_job_from_job_bundle",
        side_effect=create_job_from_bundle_mock,
    )
    @patch("deadline.unreal_submitter.unreal_open_job.open_job_description.OpenJobDescription")
    def test_submit_jobs(
        self,
        job_description_mock: Mock,
        create_job_from_bundle_mock: Mock,
        mock_telemetry_client: Mock,
    ):
        # GIVEN
        from deadline.unreal_submitter.submitter import UnrealSubmitter

        mrq_job = MagicMock()
        submitter = UnrealSubmitter()
        submitter.add_job(mrq_job)

        # WHEN
        submitted_job_ids = submitter.submit_jobs()

        # THEN
        create_job_from_bundle_mock.assert_called_once()
        assert len(submitted_job_ids) == 1

    @patch("deadline.unreal_submitter.submitter.UnrealSubmitter.show_message_dialog")
    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    @patch(
        "deadline.unreal_submitter.submitter.create_job_from_job_bundle",
        side_effect=create_job_from_bundle_mock,
    )
    @patch("deadline.unreal_submitter.unreal_open_job.open_job_description.OpenJobDescription")
    def test_cancel_submit_jobs(
        self,
        job_description_mock: Mock,
        create_job_from_bundle_mock: Mock,
        mock_telemetry_client: Mock,
        show_message_dialog_mock: Mock,
    ):

        # GIVEN
        from deadline.unreal_submitter.submitter import UnrealSubmitter

        mrq_job = MagicMock()
        submitter = UnrealSubmitter()
        submitter.add_job(mrq_job)

        # WHEN
        with patch.object(submitter, "continue_submission", False):
            submitter.submit_jobs()

        # THEN
        assert "Jobs submission canceled" in show_message_dialog_mock.mock_calls[0].args[0]

    @patch("deadline.unreal_submitter.submitter.UnrealSubmitter.show_message_dialog")
    @patch(
        "deadline.unreal_submitter.submitter.create_job_from_job_bundle",
        side_effect=create_job_from_bundle_mock,
    )
    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    @patch("deadline.unreal_submitter.unreal_open_job.open_job_description.OpenJobDescription")
    def test_fail_submit_jobs(
        self,
        open_job_description_mock: Mock,
        mock_telemetry_client: Mock,
        create_job_from_bundle_mock: Mock,
        show_message_dialog_mock: Mock,
    ):
        # GIVEN
        from deadline.unreal_submitter.submitter import UnrealSubmitter

        mrq_job = MagicMock()
        submitter = UnrealSubmitter()
        submitter.add_job(mrq_job)

        fail_message = "Test interrupt submission"
        create_job_from_bundle_mock.side_effect = ValueError(fail_message)

        # WHEN
        submitter.submit_jobs()

        # THEN
        assert fail_message in show_message_dialog_mock.mock_calls[0].args[0]

    @pytest.mark.parametrize("silent_mode, show_message_call_count", [(True, 0), (False, 1)])
    @patch("unreal.EditorDialog.show_message")
    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    def test_silent_mode(
        self,
        mock_telemetry_client: Mock,
        show_message_mock: Mock,
        silent_mode: bool,
        show_message_call_count: int,
    ):
        # GIVEN
        from deadline.unreal_submitter.submitter import UnrealSubmitter

        submitter = UnrealSubmitter(silent_mode=silent_mode)

        # WHEN
        submitter.show_message_dialog("test_silent_mode")

        # THEN
        assert len(show_message_mock.mock_calls) == show_message_call_count
