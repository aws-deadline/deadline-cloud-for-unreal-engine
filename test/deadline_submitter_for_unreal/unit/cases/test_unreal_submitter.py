#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import time
import unreal
import unittest
from unittest.mock import PropertyMock, Mock, patch

from deadline.unreal_submitter.submitter import UnrealSubmitter
from deadline.job_attachments.progress_tracker import ProgressReportMetadata, ProgressStatus


PIPELINE_QUEUE = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem).get_queue()


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
            progressMessage='Done'
        )
    )
    upload_progress_callback(
        ProgressReportMetadata(
            status=ProgressStatus.UPLOAD_IN_PROGRESS,
            progress=100.0,
            transferRate=1000.0,
            progressMessage='Done'
        )
    )
    create_job_result_callback()
    return 'job_id_1'


class TestUnrealSubmitter(unittest.TestCase):

    def test_add_job(self, submitter=UnrealSubmitter()):

        for job in PIPELINE_QUEUE.get_jobs():
            new_queue = unreal.MoviePipelineQueue()
            new_job = new_queue.duplicate_job(job)

            submitter.add_job(new_job)

        self.assertIsNot(len(submitter._jobs), 0)

    @patch('deadline.unreal_submitter.submitter.create_job_from_job_bundle', side_effect=create_job_from_bundle_mock)
    def test_submit_jobs(self, create_job_from_bundle_mock: Mock):

        submitter = UnrealSubmitter(silent_mode=True)
        self.test_add_job(submitter)
        submitter.submit_jobs()

        create_job_from_bundle_mock.assert_called_once()

    @patch('deadline.unreal_submitter.submitter.create_job_from_job_bundle', side_effect=create_job_from_bundle_mock)
    def test_cancel_submit_jobs(self, create_job_from_bundle_mock: Mock):

        submitter = UnrealSubmitter(silent_mode=True)
        self.test_add_job(submitter)

        with patch.object(submitter, 'continue_submission', False):
            submitter.submit_jobs()

        create_job_from_bundle_mock.assert_called_once()

    @patch('deadline.unreal_submitter.submitter.UnrealSubmitter.submission_failed_message', new_callable=PropertyMock)
    @patch('deadline.unreal_submitter.submitter.create_job_from_job_bundle', side_effect=create_job_from_bundle_mock)
    def test_fail_submit_jobs(self, create_job_from_bundle_mock: Mock, failed_message_mock: Mock):

        fail_message = 'Test interrupt submission'
        failed_message_mock.side_effect = [fail_message, fail_message, fail_message]

        submitter = UnrealSubmitter(silent_mode=True)
        self.test_add_job(submitter)

        submitter.submit_jobs()

        create_job_from_bundle_mock.assert_called_once()


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUnrealSubmitter)
    unittest.TextTestRunner(stream=sys.stdout, buffer=True).run(suite)
