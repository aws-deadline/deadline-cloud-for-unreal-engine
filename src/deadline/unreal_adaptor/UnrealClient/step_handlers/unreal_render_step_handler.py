#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import re
import shutil
from pathlib import Path

try:
    import unreal
except Exception:
    print(
        "Seems like UnrealClient used outside of Unreal Editor session. Some functions may not work."
    )
    unreal = None

from typing import Optional

from .base_step_handler import BaseStepHandler
from deadline.unreal_logger import get_logger


logger = get_logger()


if unreal:

    @unreal.uclass()
    class RemoteRenderMoviePipelineEditorExecutor(unreal.MoviePipelinePIEExecutor):
        totalFrameRange = unreal.uproperty(int)  # Total frame range of the job's level sequence
        currentFrame = unreal.uproperty(int)  # Current frame handler that will be updating later

        def _post_init(self):
            """
            Constructor that gets called when created either via C++ or Python
            Note that this is different from the standard __init__ function of Python
            """
            self.totalFrameRange = 0
            self.currentFrame = 0

        @unreal.ufunction(override=True)
        def execute(self, queue: unreal.MoviePipelineQueue):
            """
            Execute the provided Queue.
            You are responsible for deciding how to handle each job in the queue and processing them.

            Here we define totalFrameRange as frames count from the sequence/job configuration

            :param queue: The queue that this should process all jobs for
            :return: None
            """

            # get the single job from queue
            jobs = queue.get_jobs()
            if len(jobs) == 0:
                logger.error(f"Render Executor: Error: {queue} has 0 jobs")
                return

            for job in jobs:
                # get output settings block
                output_settings = job.get_configuration().find_or_add_setting_by_class(
                    unreal.MoviePipelineOutputSetting
                )

                # if user override frame range, use overriden values
                if output_settings.use_custom_playback_range:
                    self.totalFrameRange += (
                        output_settings.custom_end_frame - output_settings.custom_start_frame
                    )

                # else use default frame range of the level sequence
                else:
                    level_sequence = unreal.EditorAssetLibrary.load_asset(
                        unreal.SystemLibrary.conv_soft_object_reference_to_string(
                            unreal.SystemLibrary.conv_soft_obj_path_to_soft_obj_ref(job.sequence)
                        )
                    )
                    if level_sequence is None:
                        logger.error(
                            "Render Executor: Error: Level Sequence not loaded. Check if the sequence "
                            "exists and is valid"
                        )
                        return

                    self.totalFrameRange += (
                        level_sequence.get_playback_end() - level_sequence.get_playback_start()
                    )

                if self.totalFrameRange == 0:
                    logger.error(
                        "Render Executor: Error: Cannot render the Queue with frame range of zero length"
                    )

            # don't forget to call parent's execute to run the render process
            super().execute(queue)

        @unreal.ufunction(override=True)
        def on_begin_frame(self):
            """
            Called once at the beginning of each engine frame (e.g. tick, fps)
            Since the executor will work with Play in Editor widget, each rendered frame will match with widget frame tick.
            """

            super(RemoteRenderMoviePipelineEditorExecutor, self).on_begin_frame()

            # Since PIEExecutor launching Play in Editor before mrq is rendering, we should ensure, that
            # executor actually rendering the sequence.
            if self.is_rendering():
                self.currentFrame += 1
                progress = self.currentFrame / self.totalFrameRange * 100

                # Executor work with the render queue after all frames are rendered - do all
                # support stuff, handle safe quit, etc, so we should ignore progress that more than 100.
                if progress <= 100:
                    logger.info(f"Render Executor: Progress: {progress}")


class UnrealRenderStepHandler(BaseStepHandler):
    @staticmethod
    def regex_pattern_progress() -> list[re.Pattern]:
        """
        Regex pattern for handle the render progress

        :return: A list of regular expression patterns
        :rtype: list[re.Pattern]
        """
        return [re.compile(".*Render Executor: Progress: ([0-9.]+)")]

    @staticmethod
    def regex_pattern_complete() -> list[re.Pattern]:
        """
        Regex pattern for handle the render completion

        :return: A list of regular expression patterns
        :rtype: list[re.Pattern]
        """
        return [
            re.compile(".*Render Executor: Rendering is complete"),
            re.compile(".* finished ([0-9]+) jobs in .*"),
        ]

    @staticmethod
    def regex_pattern_error() -> list[re.Pattern]:
        """
        Regex pattern for handle any python exceptions and render executor errors

        :return: A list of regular expression patterns
        :rtype: list[re.Pattern]
        """
        return [re.compile(".*Exception:.*|.*Render Executor: Error:.*|.*LogPython: Error:.*")]

    @staticmethod
    def executor_failed_callback(executor, pipeline, is_fatal, error):
        """
        Callback executed when an error occurs in RemoteRenderMoviePipelineEditorExecutor

        :param executor: The RemoteRenderMoviePipelineEditorExecutor instance
        :param pipeline: The unreal.MoviePipelineQueue instance
        :param is_fatal: Whether the error is fatal or not
        :param error: The error message
        """
        logger.error(f"Render Executor: Error: {error}")

    @staticmethod
    def executor_finished_callback(pipeline_executor=None, success=None):
        """
        Callback executed when RemoteRenderMoviePipelineEditorExecutor finished render

        :param pipeline_executor: The RemoteRenderMoviePipelineEditorExecutor instance
        :param success: Whether finished successfully or not
        """
        logger.info("Render Executor: Rendering is complete")

    @staticmethod
    def copy_pipeline_queue_from_manifest_file(
        movie_pipeline_queue_subsystem, queue_manifest_path: str
    ):
        """
        Create unreal.MoviePipelineQueue from manifest file by loading the file.
        Unreal requires the manifest file to be placed under the <project_root>/Saved directory.

        :param movie_pipeline_queue_subsystem: unreal.MoviePipelineQueueSubsystem instance
        :param queue_manifest_path: Path to the manifest file
        """
        manifest_queue = unreal.MoviePipelineLibrary.load_manifest_file_from_string(
            queue_manifest_path
        )
        pipeline_queue = movie_pipeline_queue_subsystem.get_queue()
        pipeline_queue.delete_all_jobs()
        pipeline_queue.copy_from(manifest_queue)

    @staticmethod
    def create_queue_from_manifest(movie_pipeline_queue_subsystem, queue_manifest_path: str):
        """
        Create the unreal.MoviePipelineQueue object from the given queue manifest path.

        Before creating, check if manifest located outside the Project "Saved" directory
        and copy it there.

        :param movie_pipeline_queue_subsystem: The unreal.MoviePipelineQueueSubsystem instance
        :param queue_manifest_path: Path to the manifest file
        """

        logger.info(f"Create unreal.MoviePipelineQueue from manifest file: {queue_manifest_path}")

        manifest_path = queue_manifest_path.replace("\\", "/")

        project_dir = os.path.dirname(
            unreal.Paths.convert_relative_path_to_full(unreal.Paths.get_project_file_path())
        )
        project_saved_dir = os.path.join(project_dir, "Saved").replace("\\", "/")

        if not manifest_path.startswith(project_saved_dir):
            project_manifest_directory = os.path.join(
                project_saved_dir, "UnrealDeadlineCloudService", "RenderJobManifests"
            ).replace("\\", "/")
            os.makedirs(project_manifest_directory, exist_ok=True)

            destination_manifest_path = os.path.join(
                project_manifest_directory, Path(manifest_path).name
            )
            logger.info(
                f"Manifest path {queue_manifest_path} is outside "
                f"the project saved directory: {project_saved_dir}. "
                f"Trying to copy it to {destination_manifest_path}"
            )
            if not os.path.exists(destination_manifest_path):
                logger.info(f"Copying {manifest_path} to {destination_manifest_path}")
                shutil.copy(manifest_path, destination_manifest_path)
            else:
                logger.info("Destination manifest file already exists, skipping copy")

            manifest_path = destination_manifest_path.replace("\\", "/")

        UnrealRenderStepHandler.copy_pipeline_queue_from_manifest_file(
            movie_pipeline_queue_subsystem, manifest_path
        )

    @staticmethod
    def create_queue_from_job_args(
        movie_pipeline_queue_subsystem,
        level_sequence_path: str,
        level_path: str,
        job_configuration_path: str,
        job_name: Optional[str] = None,
    ):
        """
        Create the unreal.MoviePipelineQueue object from the given job arguments

        :param movie_pipeline_queue_subsystem: The unreal.MoviePipelineQueueSubsystem instance
        :param level_sequence_path: Unreal path to the level sequence file (e.g. /Game/Path/To/LevelSequence)
        :param level_path: Unreal path to the level file (e.g. /Game/Path/To/Level)
        :param job_configuration_path: Unreal path to the job configuration file (e.g. /Game/Path/To/JobConfiguration)
        :param job_name: [OPTIONAL] Name of the job to create
        """

        project_settings = unreal.get_default_object(unreal.MovieRenderPipelineProjectSettings)

        pipeline_queue = movie_pipeline_queue_subsystem.get_queue()
        pipeline_queue.delete_all_jobs()

        render_job = pipeline_queue.allocate_new_job(
            unreal.SystemLibrary.conv_soft_class_path_to_soft_class_ref(
                project_settings.default_executor_job
            )
        )

        render_job.sequence = unreal.SoftObjectPath(level_sequence_path)  # level sequence
        render_job.map = unreal.SoftObjectPath(level_path)  # level
        render_job.set_configuration(  # configuration
            unreal.EditorAssetLibrary.load_asset(job_configuration_path)
        )

        name = job_name or Path(level_sequence_path).stem
        render_job.job_name = name

    @staticmethod
    def create_queue_from_queue_asset(
        movie_pipeline_queue_subsystem, movie_pipeline_queue_asset_path: str
    ):
        pipeline_queue = movie_pipeline_queue_subsystem.get_queue()
        pipeline_queue.delete_all_jobs()

        movie_pipeline_queue_asset = unreal.EditorAssetLibrary.load_asset(
            movie_pipeline_queue_asset_path
        )
        pipeline_queue.copy_from(movie_pipeline_queue_asset)

    @staticmethod
    def enable_shots_by_chunk(render_job, task_chunk_size: int, task_chunk_id: int):

        all_shots_to_render = [shot for shot in render_job.shot_info if shot.enabled]
        shots_chunk = all_shots_to_render[
            task_chunk_id * task_chunk_size : (task_chunk_id + 1) * task_chunk_size
        ]
        for shot in render_job.shot_info:
            if shot in shots_chunk:
                shot.enabled = True
                logger.info(f"Shot to render: {shot.outer_name}: {shot.inner_name}")
            else:
                shot.enabled = False
        logger.info(f"Shots in task: {[shot.outer_name for shot in shots_chunk]}")

    def run_script(self, args: dict) -> bool:
        """
        Create the unreal.MoviePipelineQueue object and render it with the render executor

        :param args: arguments for creating the unreal.MoviePipelineQueue object
        :return: always True, because the Unreal launch render always as async process.
            (https://docs.unrealengine.com/5.2/en-US/PythonAPI/class/MoviePipelineQueueEngineSubsystem.html#unreal.MoviePipelineQueueEngineSubsystem.render_queue_with_executor_instance)
        """
        logger.info(
            f"{UnrealRenderStepHandler.run_script.__name__} executing with args: {args} ..."
        )

        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
        asset_registry.wait_for_completion()

        subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)

        if args.get("queue_manifest_path"):
            UnrealRenderStepHandler.create_queue_from_manifest(
                movie_pipeline_queue_subsystem=subsystem,
                queue_manifest_path=args["queue_manifest_path"],
            )
        else:
            UnrealRenderStepHandler.create_queue_from_job_args(
                movie_pipeline_queue_subsystem=subsystem,
                level_sequence_path=args.get("level_sequence_path", ""),
                level_path=args.get("level_path", ""),
                job_configuration_path=args.get("job_configuration_path", ""),
            )

        for job in subsystem.get_queue().get_jobs():
            if "chunk_size" in args and "chunk_id" in args:
                chunk_size: int = args["chunk_size"]
                chunk_id: int = args["chunk_id"]
                UnrealRenderStepHandler.enable_shots_by_chunk(
                    render_job=job,
                    task_chunk_size=chunk_size,
                    task_chunk_id=chunk_id,
                )

            if "output_path" in args:
                if not os.path.exists(args["output_path"]):
                    os.makedirs(args["output_path"], exist_ok=True)

                new_output_dir = unreal.DirectoryPath()
                new_output_dir.set_editor_property("path", args["output_path"].replace("\\", "/"))

                output_setting = job.get_configuration().find_setting_by_class(
                    unreal.MoviePipelineOutputSetting
                )
                output_setting.output_directory = new_output_dir

        # Initialize Render executor
        executor = RemoteRenderMoviePipelineEditorExecutor()

        # Add callbacks on complete and error actions to handle it and
        # provide output to the Deadline Adaptor
        executor.on_executor_errored_delegate.add_callable(
            UnrealRenderStepHandler.executor_failed_callback
        )
        executor.on_executor_finished_delegate.add_callable(
            UnrealRenderStepHandler.executor_finished_callback
        )

        # Render queue with the given executor
        subsystem.render_queue_with_executor_instance(executor)

        return True

    def wait_result(self, args: Optional[dict] = None) -> None:
        """
        :param args: A dictionary that contains the arguments for waiting.
        :return: None

        It is responsible for waiting result of the
        :meth:`deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler.UnrealRenderStepHandler.run_script()`.
        """
        logger.info("Render wait start")
        logger.info("Render wait finish")
