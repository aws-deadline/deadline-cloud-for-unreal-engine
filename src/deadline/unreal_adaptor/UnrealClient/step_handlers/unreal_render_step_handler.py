#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import re
from pathlib import Path

try:
    import unreal
except:
    print('Seems like UnrealClient used outside of Unreal Editor session. Some functions may not work.')
    unreal = None

from typing import Optional

from .base_step_handler import BaseStepHandler


if unreal:
    @unreal.uclass()
    class RemoteRenderMoviePipelineEditorExecutor(unreal.MoviePipelinePIEExecutor):
        totalFrameRange = unreal.uproperty(int)  # Total frame range of the job's level sequence
        currentFrame = unreal.uproperty(int)     # Current frame handler that will be updating later

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
                unreal.log_error(f"Render Executor: Error: {queue} has 0 jobs")

            job = jobs[0]

            # get output settings block
            output_settings = job.get_configuration().find_or_add_setting_by_class(
                unreal.MoviePipelineOutputSetting
            )

            # if user override frame range, use overriden values
            if output_settings.use_custom_playback_range:
                self.totalFrameRange = output_settings.custom_end_frame - output_settings.custom_start_frame

            # else use default frame range of the level sequence
            else:
                level_sequence = unreal.EditorAssetLibrary.load_asset(
                    unreal.SystemLibrary.conv_soft_object_reference_to_string(
                        unreal.SystemLibrary.conv_soft_obj_path_to_soft_obj_ref(
                            job.sequence
                        )
                    )
                )
                if level_sequence is None:
                    unreal.log_error(f"Render Executor: Error: Level Sequence not loaded. Check if the sequence "
                                     f"exists and is valid")

                self.totalFrameRange = level_sequence.get_playback_end() - level_sequence.get_playback_start()

            if self.totalFrameRange == 0:
                unreal.log_error(f"Render Executor: Error: Cannot render the Queue with frame range of zero length")

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
                # TODO refactor if possible, check shot/job finished callbacks
                if progress <= 100:
                    unreal.log(f'Render Executor: Progress: {progress}')


class UnrealRenderStepHandler(BaseStepHandler):

    @staticmethod
    def regex_pattern_progress() -> list[re.Pattern]:
        return [re.compile(".*Render Executor: Progress: ([0-9.]+)")]

    @staticmethod
    def regex_pattern_complete() -> list[re.Pattern]:
        return [
            re.compile(".*Render Executor: Rendering is complete"),
            re.compile(".* finished ([0-9]+) jobs in .*")
        ]

    @staticmethod
    def regex_pattern_error() -> list[re.Pattern]:
        return [re.compile(".*Exception:.*|.*Render Executor: Error:.*|.*LogPython: Error:.*")]

    @staticmethod
    def executor_failed_callback(executor, pipeline, is_fatal, error):
        unreal.log_error(f"Render Executor: Error: {error}")

    @staticmethod
    def executor_finished_callback(movie_pipeline=None, results=None):
        unreal.log("Render Executor: Rendering is complete")

    @staticmethod
    def create_queue_from_manifest(
            movie_pipeline_queue_subsystem,
            queue_manifest_path: str
    ):
        """
        Create the unreal.MoviePipelineQueue object from the given queue manifest path

        :param movie_pipeline_queue_subsystem: The unreal.MoviePipelineQueueSubsystem instance
        :param queue_manifest_path: Path to the manifest file
        """
        queue_manifest_path = queue_manifest_path.replace("\\", "/")
        manifest_queue = unreal.MoviePipelineLibrary.load_manifest_file_from_string(queue_manifest_path)

        pipeline_queue = movie_pipeline_queue_subsystem.get_queue()
        pipeline_queue.delete_all_jobs()
        pipeline_queue.copy_from(manifest_queue)

    @staticmethod
    def create_queue_from_job_args(
            movie_pipeline_queue_subsystem,
            level_sequence_path: str,
            level_path: str,
            job_configuration_path: str,
            job_name: str = None
    ):
        """
        Create the unreal.MoviePipelineQueue object from the given job arguments

        :param movie_pipeline_queue_subsystem: The unreal.MoviePipelineQueueSubsystem instance
        :param level_sequence_path: Unreal path to the level sequence file (e.g. /Game/Path/To/LevelSequence)
        :param level_path: Unreal path to the level file (e.g. /Game/Path/To/Level)
        :param job_configuration_path: Unreal path to the job configuration file (e.g. /Game/Path/To/JobConfiguration)
        :param job_name: [OPTIONAL] Name of the job to create
        """

        project_settings = unreal.get_default_object(
            unreal.MovieRenderPipelineProjectSettings
        )

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

    def run_script(self, args: Optional[dict] = None) -> bool:
        """
        Create the unreal.MoviePipelineQueue object and render it with the render executor

        :param args: arguments for creating the unreal.MoviePipelineQueue object
        :return: always True, because the Unreal launch render always as async process.
            (https://docs.unrealengine.com/5.2/en-US/PythonAPI/class/MoviePipelineQueueEngineSubsystem.html#unreal.MoviePipelineQueueEngineSubsystem.render_queue_with_executor_instance)
        """
        unreal.log(f'{UnrealRenderStepHandler.run_script.__name__} executing with args: {args} ...')

        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
        asset_registry.wait_for_completion()

        subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)

        if args.get('queue_manifest_path'):
            UnrealRenderStepHandler.create_queue_from_manifest(
                movie_pipeline_queue_subsystem=subsystem,
                queue_manifest_path=args['queue_manifest_path']
            )
        else:
            UnrealRenderStepHandler.create_queue_from_job_args(
                movie_pipeline_queue_subsystem=subsystem,
                level_sequence_path=args.get('level_sequence_path'),
                level_path=args.get('level_path'),
                job_configuration_path=args.get('job_configuration_path')
            )

        # Initialize Render executor
        executor = RemoteRenderMoviePipelineEditorExecutor()

        # Add callbacks on complete and error actions to handle it and provide output to the Deadline Adaptor
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
        unreal.log('Render wait start')
        unreal.log('Render wait finish')
