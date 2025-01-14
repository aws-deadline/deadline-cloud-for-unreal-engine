#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import unreal
import threading
import traceback
from enum import Enum
from typing import Callable

from deadline.client.api import (
    create_job_from_job_bundle,
    get_deadline_cloud_library_telemetry_client,
)
from deadline.job_attachments.exceptions import AssetSyncCancelledError

from deadline.unreal_logger import get_logger
from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (
    UnrealOpenJob,
    RenderUnrealOpenJob,
)

from ._version import version


# Initialize telemetry client, opt-out is respected
telemetry_client = get_deadline_cloud_library_telemetry_client()
telemetry_client.update_common_details(
    {
        "deadline-cloud-for-unreal-engine-submitter-version": version,
        # Example: 5.4.3-34507850+++UE5+Release-5.4
        "unreal-engine-version": unreal.SystemLibrary.get_engine_version(),
    }
)


logger = get_logger()


def error_notify(
    notify_title: str = "Operation failed",
    notify_prefix: str = "Error occurred:\n",
    with_traceback: bool = False,
):
    def decorator(func: Callable):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                unreal.log(str(e))
                unreal.log(traceback.format_exc())

                telemetry_client.record_error(
                    event_details={"exception_scope": "on_submit"},
                    exception_type=str(type(e)),
                    from_gui=not self._silent_mode,
                )

                message = notify_prefix + str(e)
                if with_traceback:
                    message += "\n" + traceback.format_exc()
                else:
                    message += "\nSee logs for more details."
                self.show_message_dialog(message=message, title=notify_title)

        return wrapper

    return decorator


class UnrealSubmitStatus(Enum):
    """
    Enumeration of the current UnrealSubmitter status
    """

    COMPLETED = 1
    HASHING = 2
    UPLOADING = 3


class UnrealSubmitter:
    """
    Execute the OpenJob submission
    """

    open_job_class: type[UnrealOpenJob] = UnrealOpenJob

    def __init__(self, silent_mode: bool = False):
        self._silent_mode = silent_mode

        self._jobs: list[UnrealOpenJob] = []
        self.submit_status: UnrealSubmitStatus = UnrealSubmitStatus.COMPLETED
        self.submit_message: str = "Start submitting..."
        self.progress_list: list[float] = []

        self.continue_submission = True  # affect all not submitted jobs
        self.submitted_job_ids: list[str] = []  # use after submit loop is ended
        self._submission_failed_message = ""  # reset after each job in the loop

    @property
    def submission_failed_message(self) -> str:
        return self._submission_failed_message

    def add_job(self, *args, **kwargs):
        """
        Build and add to the submission queue :class:`deadline.unreal_submitter.unreal_open_job.open_job_description.OpenJobDescription`
        """
        raise NotImplementedError

    def _display_progress(self, check_submit_status, message):
        """
        Display the operation progress in the UI.

        :param check_submit_status: :class:`deadline.unreal_submitter.submitter.UnrealSubmitStatus` value
        :type check_submit_status: :class:`deadline.unreal_submitter.submitter.UnrealSubmitStatus`
        :param message: Message to display
        :type message: str
        """
        last_progress: float = 0
        with unreal.ScopedSlowTask(100, message) as submit_task:
            submit_task.make_dialog(True)
            while self.submit_status == check_submit_status:
                if self.submission_failed_message != "":
                    break

                if submit_task.should_cancel():
                    self.continue_submission = False
                    break

                if len(self.progress_list) > 0:
                    new_progress = self.progress_list.pop(0)
                else:
                    new_progress = last_progress
                submit_task.enter_progress_frame(new_progress - last_progress, self.submit_message)
                last_progress = new_progress

    def _start_submit(self, job_bundle_path):
        """
        Start the OpenJob submission

        :param job_bundle_path: Path of the Job bundle to submit
        :type job_bundle_path: str
        """
        try:
            job_id = create_job_from_job_bundle(
                job_bundle_dir=job_bundle_path,
                hashing_progress_callback=lambda hash_metadata: self._hash_progress(hash_metadata),
                upload_progress_callback=lambda upload_metadata: self._upload_progress(
                    upload_metadata
                ),
                create_job_result_callback=lambda: self._create_job_result(),
            )
            if job_id:
                logger.info(f"Job creation result: {job_id}")
                self.submitted_job_ids.append(job_id)

        except AssetSyncCancelledError as e:
            logger.warning(str(e))

        except Exception as e:
            logger.error(str(e))
            logger.error(traceback.format_exc())
            self._submission_failed_message = str(e)

    def _hash_progress(self, hash_metadata) -> bool:
        """
        Hashing progress callback for displaying hash metadata on the progress bar

        :param hash_metadata: :class:`deadline.job_attachments.progress_tracker.ProgressReportMetadata`
        :type hash_metadata: deadline.job_attachments.progress_tracker.ProgressReportMetadata
        :return: Continue submission or not
        :rtype: bool
        """
        self.submit_status = UnrealSubmitStatus.HASHING
        logger.info(
            "Hash progress: {} {}".format(hash_metadata.progress, hash_metadata.progressMessage)
        )
        self.submit_message = hash_metadata.progressMessage
        self.progress_list.append(hash_metadata.progress)
        return self.continue_submission

    def _upload_progress(self, upload_metadata) -> bool:
        """
        Uploading progress callback for displaying upload metadata on the progress bar

        :param upload_metadata: :class:`deadline.job_attachments.progress_tracker.ProgressReportMetadata`
        :type upload_metadata: deadline.job_attachments.progress_tracker.ProgressReportMetadata
        :return: Continue submission or not
        :rtype: bool
        """

        self.submit_status = UnrealSubmitStatus.UPLOADING
        logger.info(
            "Upload progress: {} {}".format(
                upload_metadata.progress, upload_metadata.progressMessage
            )
        )
        self.submit_message = upload_metadata.progressMessage
        self.progress_list.append(upload_metadata.progress)
        return self.continue_submission

    def _create_job_result(self) -> bool:
        """
        Creates job result callback
        :return: True
        """

        self.submit_status = UnrealSubmitStatus.COMPLETED
        logger.info("Create job result...")
        return True

    def show_message_dialog(
        self, message: str, title="Job Submission", message_type=unreal.AppMsgType.OK
    ):
        """
        Show message dialog in the Unreal Editor UI

        :param message: Message to display
        :type message: str
        :param title: Message title
        :type title: str
        :param message_type: Message box type
        :type message_type: unreal.AppMsgType.OK
        """

        if self._silent_mode:
            return

        unreal.EditorDialog.show_message(title=title, message=message, message_type=message_type)

    @error_notify("Submission failed")
    def submit_jobs(self) -> list[str]:
        """
        Submit OpenJobs to the Deadline Cloud
        """

        del self.submitted_job_ids[:]

        for job in self._jobs:
            logger.info("Creating job from bundle...")
            self.submit_status = UnrealSubmitStatus.HASHING
            self.progress_list = []
            self.submit_message = "Start submitting..."
            self._submission_failed_message = ""

            job_bundle_path = job.create_job_bundle()

            t = threading.Thread(target=self._start_submit, args=(job_bundle_path,), daemon=True)
            t.start()

            self._display_progress(
                check_submit_status=UnrealSubmitStatus.HASHING, message="Hashing"
            )
            if self.continue_submission:
                self._display_progress(
                    check_submit_status=UnrealSubmitStatus.UPLOADING, message="Uploading"
                )
            t.join()

            # current job failed, notify and continue
            if self.submission_failed_message != "":
                self.show_message_dialog(
                    f"Job {job.name} unsubmitted for the reason:\n {self.submission_failed_message}"
                )

            # User cancel submission, notify and quit submission queue
            if not self.continue_submission:
                self.show_message_dialog(
                    f"Jobs submission canceled.\n"
                    f"Number of unsubmitted jobs: {len(self._jobs) - len(self.submitted_job_ids)}"
                )
                break

        # Summary notification about submission process
        self.show_message_dialog(
            f"Submitted jobs ({len(self.submitted_job_ids)}):\n" + "\n".join(self.submitted_job_ids)
        )

        del self._jobs[:]

        return self.submitted_job_ids


class UnrealOpenJobDataAssetSubmitter(UnrealSubmitter):

    @error_notify("Data asset converting failed")
    def add_job(self, unreal_open_job_data_asset: unreal.DeadlineCloudJob):
        open_job = self.open_job_class.from_data_asset(unreal_open_job_data_asset)
        self._jobs.append(open_job)


class UnrealMrqJobSubmitter(UnrealSubmitter):

    open_job_class = RenderUnrealOpenJob

    @error_notify("Data asset converting failed")
    def add_job(self, mrq_job: unreal.MoviePipelineExecutorJob):
        render_open_job = self.open_job_class.from_mrq_job(mrq_job)
        self._jobs.append(render_open_job)


class UnrealOpenJobSubmitter(UnrealSubmitter):

    @error_notify("Data asset converting failed")
    def add_job(self, open_job: UnrealOpenJob):
        self._jobs.append(open_job)


class UnrealRenderOpenJobSubmitter(UnrealSubmitter):

    open_job_class = RenderUnrealOpenJob

    @error_notify("Data asset converting failed")
    def add_job(self, render_open_job: RenderUnrealOpenJob):
        self._jobs.append(render_open_job)
