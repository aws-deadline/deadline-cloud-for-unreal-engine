#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import time
from unittest.mock import Mock, MagicMock, patch

import pytest
from deadline.job_attachments.progress_tracker import ProgressReportMetadata, ProgressStatus

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.submitter import UnrealSubmitter  # noqa: E402


def create_job_from_bundle_mock(
    job_bundle_dir=None,
    hashing_progress_callback=None,
    upload_progress_callback=None,
    create_job_result_callback=None,
):
    time.sleep(0.1)

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
    @patch(
        "deadline.unreal_submitter.submitter.create_job_from_job_bundle",
        side_effect=create_job_from_bundle_mock,
    )
    @patch("deadline.unreal_submitter.submitter.UnrealOpenJob")
    @patch("deadline.unreal_submitter.submitter.UnrealSubmitter._hash_progress")
    @patch("deadline.unreal_submitter.submitter.UnrealSubmitter._upload_progress")
    def test_submit_jobs(
        self,
        upload_progress_mock: Mock,
        hash_progress_mock: Mock,
        open_job_mock: Mock,
        create_job_from_bundle_mock: Mock,
        mock_telemetry_client: Mock,
    ):
        # GIVEN

        open_job_mock.create_job_bundle = MagicMock()
        submitter = UnrealSubmitter()
        submitter._jobs.append(open_job_mock)

        # WHEN
        submitted_job_ids = submitter.submit_jobs()

        # THEN
        create_job_from_bundle_mock.assert_called_once()
        upload_progress_mock.assert_called_once()
        hash_progress_mock.assert_called_once()
        assert len(submitted_job_ids) == 1

    @patch("deadline.unreal_submitter.submitter.UnrealSubmitter.show_message_dialog")
    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    @patch(
        "deadline.unreal_submitter.submitter.create_job_from_job_bundle",
        side_effect=create_job_from_bundle_mock,
    )
    @patch("deadline.unreal_submitter.submitter.UnrealOpenJob")
    def test_cancel_submit_jobs(
        self,
        open_job_mock: Mock,
        create_job_from_bundle_mock: Mock,
        mock_telemetry_client: Mock,
        show_message_dialog_mock: Mock,
    ):
        # GIVEN
        open_job_mock.create_job_bundle = MagicMock()
        submitter = UnrealSubmitter()
        submitter._jobs.append(open_job_mock)

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
    @patch("deadline.unreal_submitter.submitter.UnrealOpenJob")
    def test_fail_submit_jobs(
        self,
        open_job_mock: Mock,
        mock_telemetry_client: Mock,
        create_job_from_bundle_mock: Mock,
        show_message_dialog_mock: Mock,
    ):
        # GIVEN
        open_job_mock.create_job_bundle = MagicMock()
        submitter = UnrealSubmitter()
        submitter._jobs.append(open_job_mock)

        fail_message = "Test interrupt submission"
        create_job_from_bundle_mock.side_effect = ValueError(fail_message)

        # WHEN
        submitter.submit_jobs()

        # THEN
        assert fail_message in show_message_dialog_mock.mock_calls[0].args[0]

    @pytest.mark.parametrize("silent_mode, show_message_call_count", [(True, 0), (False, 1)])
    @patch("deadline.unreal_submitter.submitter.get_deadline_cloud_library_telemetry_client")
    def test_silent_mode(
        self,
        mock_telemetry_client: Mock,
        silent_mode: bool,
        show_message_call_count: int,
    ):
        # GIVEN
        submitter = UnrealSubmitter(silent_mode=silent_mode)

        unreal_show_message_mock = MagicMock()
        unreal_mock.EditorDialog.show_message = unreal_show_message_mock

        # WHEN
        submitter.show_message_dialog("test_silent_mode")

        # THEN
        assert unreal_show_message_mock.call_count == show_message_call_count
