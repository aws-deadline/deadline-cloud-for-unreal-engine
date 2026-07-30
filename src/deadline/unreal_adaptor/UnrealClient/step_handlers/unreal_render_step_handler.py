# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

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
                        # Defensive fallback: if the LevelSequence can't be loaded
                        # (we have seen this happen in production for reasons that
                        # are not always reproducible), use the MRQ output_settings
                        # custom range if it is non-empty. This avoids crashing the
                        # render with an `AttributeError: 'NoneType' object has no
                        # attribute 'get_playback_end'` when something upstream
                        # caused the loader to return None.
                        if output_settings.custom_end_frame > output_settings.custom_start_frame:
                            logger.warning(
                                "Render Executor: Level Sequence not loaded; falling back to "
                                f"output_settings custom range "
                                f"[{output_settings.custom_start_frame}, "
                                f"{output_settings.custom_end_frame}]"
                            )
                            self.totalFrameRange += (
                                output_settings.custom_end_frame
                                - output_settings.custom_start_frame
                            )
                        else:
                            logger.error(
                                "Render Executor: Error: Level Sequence not loaded and "
                                "output_settings has no custom range. Check if the sequence "
                                "exists and is valid."
                            )
                            return
                    else:
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
    cached_frame_range_start = None
    cached_frame_range_end = None

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
    def _apply_task_index_to_filename(render_job, task_index: int) -> None:
        """
        Substitute ``{task_index}`` in MRQ's FileNameFormat with the per-task index so
        multi-task renders that produce a single file per task (e.g. .mov containers) do
        not collide on the same output filename. If the resolved format contains no
        per-task token (neither ``{task_index}`` nor ``{frame_number}``), warn that
        outputs from sibling tasks will overwrite each other.
        """
        output_settings = render_job.get_configuration().find_or_add_setting_by_class(
            unreal.MoviePipelineOutputSetting
        )
        file_name_format = output_settings.file_name_format or ""
        if "{task_index}" in file_name_format:
            output_settings.file_name_format = file_name_format.replace(
                "{task_index}", f"{task_index:04d}"
            )
        elif "{frame_number}" not in file_name_format:
            logger.warning(
                "FileNameFormat %r contains no per-task token; outputs from sibling "
                "tasks will overwrite each other. Add {task_index} to FileNameFormat "
                "to disambiguate per-task output (recommended for video containers "
                "such as .mov where {frame_number} is not present by default).",
                file_name_format,
            )

    @staticmethod
    def enable_shots_for_task(render_job, shots_per_task: int, task_index: int):

        all_shots_to_render = [shot for shot in render_job.shot_info if shot.enabled]
        task_shots = all_shots_to_render[
            task_index * shots_per_task : (task_index + 1) * shots_per_task
        ]
        for shot in render_job.shot_info:
            if shot in task_shots:
                shot.enabled = True
                logger.info(f"Shot to render: {shot.outer_name}: {shot.inner_name}")
            else:
                shot.enabled = False
        logger.info(f"Shots in task: {[shot.outer_name for shot in task_shots]}")

    @staticmethod
    def get_frame_range(output_settings, level_sequence):
        if UnrealRenderStepHandler.cached_frame_range_start is None:
            if output_settings.use_custom_playback_range:
                UnrealRenderStepHandler.cached_frame_range_start = (
                    output_settings.custom_start_frame
                )
                UnrealRenderStepHandler.cached_frame_range_end = output_settings.custom_end_frame
                logger.info(
                    f"Cached custom frame range from {UnrealRenderStepHandler.cached_frame_range_start} to {UnrealRenderStepHandler.cached_frame_range_end}"
                )
            elif level_sequence is None:
                # The caller passed a None LevelSequence (e.g. the loader returned
                # None for reasons that are not always reproducible). Fall back to
                # the MRQ output_settings custom range so multi-task renders can still
                # emit frames; otherwise we'd crash on
                # `NoneType.get_playback_range()` further down. If output_settings
                # has no non-empty range either, leave the cache unset and surface
                # an error so misconfigured jobs aren't silently masked.
                if output_settings.custom_end_frame > output_settings.custom_start_frame:
                    UnrealRenderStepHandler.cached_frame_range_start = (
                        output_settings.custom_start_frame
                    )
                    UnrealRenderStepHandler.cached_frame_range_end = (
                        output_settings.custom_end_frame
                    )
                    logger.warning(
                        "level_sequence is None in get_frame_range; using "
                        f"output_settings custom range "
                        f"[{UnrealRenderStepHandler.cached_frame_range_start}, "
                        f"{UnrealRenderStepHandler.cached_frame_range_end}]"
                    )
                else:
                    logger.error(
                        "level_sequence is None and output_settings has no custom range; "
                        "frame range cannot be determined"
                    )
                    return (None, None)
            else:
                UnrealRenderStepHandler.cached_frame_range_start = (
                    level_sequence.get_playback_range().get_start_frame()
                )
                UnrealRenderStepHandler.cached_frame_range_end = (
                    level_sequence.get_playback_range().get_end_frame()
                )
                logger.info(
                    f"Cached level sequence frame range from {UnrealRenderStepHandler.cached_frame_range_start} to {UnrealRenderStepHandler.cached_frame_range_end}"
                )
        return (
            UnrealRenderStepHandler.cached_frame_range_start,
            UnrealRenderStepHandler.cached_frame_range_end,
        )

    @staticmethod
    def parse_dynamic_chunked_frames(dynamic_chunked_frames: str) -> tuple[int, int]:
        """
        Parse a contiguous frame chunk expression into start and end frames.

        IMPORTANT: Only CONTIGUOUS rangeConstraint is supported. Non-contiguous frame lists
        (e.g., "1,5,10" or "1-5,10-15") are NOT supported because Unreal Engine's Movie Render
        Queue (MRQ) only accepts contiguous frame ranges via custom_start_frame/custom_end_frame.
        MRQ does not provide an API to render arbitrary non-contiguous frames in a single job.

        Supported format:
            Range: "<start>-<end>" (e.g., "1-10", "5-5", "0-100", "-100--76", "-50-10")

        :param dynamic_chunked_frames: Frame chunk expression string from TASK_CHUNKING extension
            (must be CONTIGUOUS rangeConstraint)
        :return: Tuple of (start_frame, end_frame)
        :raises ValueError: If dynamic_chunked_frames is empty, malformed, or not in range format
        """
        if not dynamic_chunked_frames or not dynamic_chunked_frames.strip():
            raise ValueError("dynamic_chunked_frames cannot be empty")

        dynamic_chunked_frames = dynamic_chunked_frames.strip()

        # CONTIGUOUS mode always returns range format: "<start>-<end>"
        match = re.match(r"^(-?\d+)-(-?\d+)$", dynamic_chunked_frames)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            if start > end:
                raise ValueError(
                    f"Invalid frame range: start ({start}) cannot be greater than end ({end})"
                )
            return (start, end)

        raise ValueError(
            f"Invalid dynamic_chunked_frames format: '{dynamic_chunked_frames}'. "
            "Expected range format '<start>-<end>' (e.g., '1-10', '5-5', '-100-100')"
        )

    @staticmethod
    def _apply_param_aliases(args: dict) -> dict:
        """Accept both the legacy and new run_data keys for the render
        partitioning parameters, for backwards compatibility during the
        parameter rename:

            chunk_size -> shots_per_task
            chunk_id   -> task_index

        The names are being changed on the submitter side to avoid colliding
        with OpenJD's own "ChunkSize" task-chunking term. This adaptor accepts
        both so it can run jobs from an older submitter (legacy keys) and a
        newer submitter (new keys) alike.

        The adaptor's own downstream logic uses the NEW keys; this normalizes
        the legacy keys onto the new ones in place. The new keys take
        precedence when both are present. Once older submitters are no longer
        in use, this aliasing (and the legacy keys in run_data.schema.json)
        can be removed without touching the rest of the adaptor.

        :param args: run_data arguments (mutated in place)
        :return: the same args dict, for convenience
        """
        if "chunk_size" in args and "shots_per_task" not in args:
            args["shots_per_task"] = args["chunk_size"]
        if "chunk_id" in args and "task_index" not in args:
            args["task_index"] = args["chunk_id"]
        return args

    def run_script(self, args: dict) -> bool:
        """
        Create the unreal.MoviePipelineQueue object and render it with the render executor

        :param args: arguments for creating the unreal.MoviePipelineQueue object
        :return: always True, because the Unreal launch render always as async process.
            (https://docs.unrealengine.com/5.4/en-US/PythonAPI/class/MoviePipelineQueueEngineSubsystem.html#unreal.MoviePipelineQueueEngineSubsystem.render_queue_with_executor_instance)
        """
        logger.info(
            f"{UnrealRenderStepHandler.run_script.__name__} executing with args: {args} ..."
        )

        UnrealRenderStepHandler._apply_param_aliases(args)

        asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
        asset_registry.wait_for_completion()

        subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)

        if args.get("queue_manifest_path"):
            UnrealRenderStepHandler.create_queue_from_manifest(
                movie_pipeline_queue_subsystem=subsystem,
                queue_manifest_path=args["queue_manifest_path"],
            )
        elif args.get("queue_path"):
            UnrealRenderStepHandler.create_queue_from_queue_asset(
                movie_pipeline_queue_subsystem=subsystem,
                movie_pipeline_queue_asset_path=args["queue_path"],
            )
        else:
            UnrealRenderStepHandler.create_queue_from_job_args(
                movie_pipeline_queue_subsystem=subsystem,
                level_sequence_path=args.get("level_sequence_path", ""),
                level_path=args.get("level_path", ""),
                job_configuration_path=args.get("job_configuration_path", ""),
            )

        output_settings = None
        if "task_index" in args:
            task_index: int = args["task_index"]
        for job in subsystem.get_queue().get_jobs():
            # Dynamic chunking, frame-based and shot-based chunking are mutually
            # exclusive modes, checked in that priority order.
            dynamic_chunk_start_frame: Optional[int] = None
            if "dynamic_chunked_frames" in args:
                # Dynamic chunking: the scheduler (TASK_CHUNKING extension) computes the
                # frame range and passes it pre-computed via dynamic_chunked_frames.
                start_frame, end_frame = self.parse_dynamic_chunked_frames(
                    args["dynamic_chunked_frames"]
                )
                # The scheduler returns inclusive frame ranges (e.g., "10-10" means 1 frame),
                # but Unreal's custom_end_frame is exclusive. Add 1 to convert the
                # inclusive scheduler end to Unreal's exclusive end.
                end_frame = end_frame + 1
                dynamic_chunk_start_frame = start_frame
                # Always resolve output settings for the CURRENT job - caching
                # across the queue loop would apply the first job's settings
                # object to every subsequent job in the queue.
                output_settings = job.get_configuration().find_or_add_setting_by_class(
                    unreal.MoviePipelineOutputSetting
                )
                level_sequence = unreal.EditorAssetLibrary.load_asset(
                    unreal.SystemLibrary.conv_soft_object_reference_to_string(
                        unreal.SystemLibrary.conv_soft_obj_path_to_soft_obj_ref(job.sequence)
                    )
                )
                # Dynamic chunking requires explicit custom playback range
                output_settings.use_custom_playback_range = True
                output_settings.custom_start_frame = start_frame
                output_settings.custom_end_frame = end_frame

                if level_sequence is not None:
                    level_sequence.set_playback_start(start_frame)
                    level_sequence.set_playback_end(end_frame)
                    logger.info(
                        f"Rendering custom frame range from {output_settings.custom_start_frame} to {output_settings.custom_end_frame} with sequence playback start {level_sequence.get_playback_start()} end {level_sequence.get_playback_end()}"
                    )
                else:
                    logger.warning(
                        "Rendering dynamic chunk frame range "
                        f"[{output_settings.custom_start_frame}, "
                        f"{output_settings.custom_end_frame}] without a resolved "
                        "LevelSequence; relying on output_settings.use_custom_playback_range"
                    )
            elif args.get("frames_per_task") and "task_index" in args:
                frames_per_task: int = args["frames_per_task"]
                if not output_settings:
                    output_settings = job.get_configuration().find_or_add_setting_by_class(
                        unreal.MoviePipelineOutputSetting
                    )
                level_sequence = unreal.EditorAssetLibrary.load_asset(
                    unreal.SystemLibrary.conv_soft_object_reference_to_string(
                        unreal.SystemLibrary.conv_soft_obj_path_to_soft_obj_ref(job.sequence)
                    )
                )
                frame_range_start, frame_range_end = self.get_frame_range(
                    output_settings, level_sequence
                )
                if frame_range_start is None or frame_range_end is None:
                    logger.error(
                        "Frame range unavailable; cannot compute the frame window for "
                        f"task_index={task_index} frames_per_task={frames_per_task}"
                    )
                    return False

                output_settings.custom_start_frame = frame_range_start + (
                    task_index * frames_per_task
                )
                output_settings.custom_end_frame = min(
                    output_settings.custom_start_frame + frames_per_task, frame_range_end
                )
                # Force MRQ to honour the per-task frame window set above. Without
                # this flag, MRQ falls back to the full range baked into the MRQ
                # preset whenever `use_custom_playback_range` is false on the output
                # settings -- which causes every task to redundantly re-render the
                # entire sequence. Observed in a 40-task render where each task
                # re-rendered frames 0..end instead of its assigned window.
                output_settings.use_custom_playback_range = True

                if level_sequence is not None:
                    level_sequence.set_playback_start(output_settings.custom_start_frame)
                    level_sequence.set_playback_end(output_settings.custom_end_frame)
                    logger.info(
                        f"Rendering custom frame range from {output_settings.custom_start_frame} to {output_settings.custom_end_frame} with sequence playback start {level_sequence.get_playback_start()} end {level_sequence.get_playback_end()}"
                    )
                else:
                    logger.warning(
                        "Rendering task frame range "
                        f"[{output_settings.custom_start_frame}, "
                        f"{output_settings.custom_end_frame}] without a resolved "
                        "LevelSequence; relying on output_settings.use_custom_playback_range"
                    )
            elif "shots_per_task" in args and "task_index" in args:
                shots_per_task: int = args["shots_per_task"]
                UnrealRenderStepHandler.enable_shots_for_task(
                    render_job=job,
                    shots_per_task=shots_per_task,
                    task_index=task_index,
                )

            if "dynamic_chunked_frames" in args and dynamic_chunk_start_frame is not None:
                # Dynamic chunking has no task_index in args (chunks are not indexed that
                # way). Chunk start frames are unique across chunks of a CONTIGUOUS range,
                # so substitute the chunk start frame for the {task_index} filename token
                # to keep per-task output filenames from colliding.
                logger.info(
                    "Dynamic chunking provides no task index; substituting the chunk "
                    f"start frame ({dynamic_chunk_start_frame}) for the {{task_index}} "
                    "filename token to disambiguate per-task output"
                )
                UnrealRenderStepHandler._apply_task_index_to_filename(
                    job, dynamic_chunk_start_frame
                )
            elif "task_index" in args and (args.get("frames_per_task") or "shots_per_task" in args):
                UnrealRenderStepHandler._apply_task_index_to_filename(job, task_index)

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
