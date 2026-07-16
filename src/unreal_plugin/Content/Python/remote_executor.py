# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import unreal

from deadline.unreal_logger import get_logger
from deadline.unreal_submitter.submitter import UnrealMrqJobSubmitter

logger = get_logger()


@unreal.uclass()
class MoviePipelineDeadlineCloudRemoteExecutor(unreal.MoviePipelinePythonHostExecutor):
    """
    Deadline Cloud remote executor for Movie Render Queue.

    Inherits from MoviePipelinePythonHostExecutor (not MoviePipelineExecutorBase directly)
    because Python-defined UClasses aren't available when the executor is first initialized.
    The host executor's C++ code handles Execute() dispatch and forwards to execute_delayed()
    which Python can reliably override.
    """

    job_ids = unreal.uproperty(unreal.Array(str))

    @unreal.ufunction(override=True)
    def execute_delayed(self, pipeline_queue):
        logger.info(f"Asked to execute Queue: {pipeline_queue}")
        logger.info(f"Queue has {len(pipeline_queue.get_jobs())} jobs")

        if not pipeline_queue or (not pipeline_queue.get_jobs()):
            self.on_executor_finished_impl()
            return

        if not self.check_dirty_packages():
            return

        if not self.check_maps(pipeline_queue):
            return

        self.pipeline_queue = pipeline_queue

        unreal_submitter = UnrealMrqJobSubmitter(silent_mode=unreal.SystemLibrary.is_unattended())

        for job in self.pipeline_queue.get_jobs():
            logger.info(f"Submitting Job `{job.job_name}` to Deadline Cloud...")
            unreal_submitter.add_job(job)

        unreal_submitter.submit_jobs()

    @unreal.ufunction(override=True)
    def is_rendering(self):
        return False

    def check_dirty_packages(self) -> bool:
        dirty_packages = []
        dirty_packages.extend(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        dirty_packages.extend(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())

        if dirty_packages:
            if not unreal.EditorLoadingAndSavingUtils.save_dirty_packages_with_dialog(True, True):
                message = (
                    "One or more jobs in the queue have an unsaved map/content. "
                    "{packages} "
                    "Please save and check-in all work before submission.".format(
                        packages="\n".join(dirty_packages)
                    )
                )

                logger.error(message)
                unreal.EditorDialog.show_message(
                    "Unsaved Maps/Content", message, unreal.AppMsgType.OK
                )
                self.on_executor_finished_impl()
                return False
        return True

    def check_maps(self, pipeline_queue) -> bool:
        has_valid_map = unreal.MoviePipelineEditorLibrary.is_map_valid_for_remote_render(
            pipeline_queue.get_jobs()
        )
        if not has_valid_map:
            message = (
                "One or more jobs in the queue have an unsaved map as "
                "their target map. "
                "These unsaved maps cannot be loaded by an external process, "
                "and the render has been aborted."
            )
            logger.error(message)
            unreal.EditorDialog.show_message("Unsaved Maps", message, unreal.AppMsgType.OK)
            self.on_executor_finished_impl()
            return False

        return True
