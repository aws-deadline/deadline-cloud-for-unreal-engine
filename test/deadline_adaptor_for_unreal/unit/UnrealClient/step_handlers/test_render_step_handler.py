# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

unreal_mock = MagicMock()
unreal_mock.log = MagicMock()
sys.modules["unreal"] = unreal_mock


@pytest.fixture()
def unreal_render_step_handler():
    from deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler import (
        UnrealRenderStepHandler,
    )

    UnrealRenderStepHandler.cached_frame_range_start = None
    UnrealRenderStepHandler.cached_frame_range_end = None
    UnrealRenderStepHandler.active_executor = None
    UnrealRenderStepHandler.render_wait_started = False
    unreal_mock.DeadlineExecutorImplementationLibrary = None
    return UnrealRenderStepHandler()


class ShotInfoMock:

    def __init__(self, enabled: bool, outer_name: str, inner_name: str):
        self.enabled = enabled
        self.outer_name = outer_name
        self.inner_name = inner_name


class RenderJobMock:

    def __init__(self, shot_info: list[ShotInfoMock]):
        self.shot_info = shot_info


class TestUnrealRenderStepHandler:

    @pytest.mark.parametrize(
        "shots_count, enabled_shots_count, shots_per_task, task_index",
        [
            (29, 15, 5, 0),
            (29, 29, 5, 1),
            (1, 1, 10, 0),
            (1500, 1, 1501, 0),
            (10, 9, 3, 2),
        ],
    )
    def test_enable_shots_for_task(
        self,
        unreal_render_step_handler,
        shots_count,
        enabled_shots_count,
        shots_per_task,
        task_index,
    ):
        # GIVEN
        enabled_shots = [
            ShotInfoMock(enabled=True, outer_name=f"Enabled{i}", inner_name=f"Enabled{i}")
            for i in range(enabled_shots_count)
        ]
        disabled_shots = [
            ShotInfoMock(enabled=False, outer_name=f"Disabled{i}", inner_name=f"Disabled{i}")
            for i in range(shots_count - enabled_shots_count)
        ]
        render_job_mock = RenderJobMock(shot_info=enabled_shots + disabled_shots)

        enabled_job_shots = [shot for shot in render_job_mock.shot_info if shot.enabled]
        task_shots = enabled_job_shots[
            task_index * shots_per_task : (task_index + 1) * shots_per_task
        ]
        task_shot_names = [shot.outer_name for shot in task_shots]

        # WHEN
        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers."
            "unreal_render_step_handler.logger.info"
        ) as log_mock:
            unreal_render_step_handler.enable_shots_for_task(
                render_job_mock, shots_per_task, task_index
            )

            # THEN
            enabled_shots = [shot for shot in render_job_mock.shot_info if shot.enabled]
            assert all([shot.enabled for shot in enabled_shots])
            assert all([shot.outer_name.startswith("Enabled") for shot in task_shots])
            assert len(enabled_shots) <= shots_per_task and len(enabled_shots) <= shots_count

            disabled_shots = [
                shot for shot in render_job_mock.shot_info if shot.outer_name not in task_shot_names
            ]
            for shot in disabled_shots:
                assert not shot.enabled

            log_mock.assert_called_with(
                f"Shots in task: {[shot.outer_name for shot in enabled_shots]}"
            )


class TestApplyParamAliases:
    """Backwards-compatible run_data key aliasing.

    The adaptor's downstream logic uses the new keys (shots_per_task/task_index).
    For backwards compatibility during the parameter rename it also accepts the
    legacy keys (chunk_size/chunk_id), normalizing them onto the new keys. The
    new keys take precedence when both are present.
    """

    def test_legacy_keys_aliased_to_new(self, unreal_render_step_handler):
        args = {"handler": "render", "chunk_size": 5, "chunk_id": 2}
        unreal_render_step_handler._apply_param_aliases(args)
        assert args["shots_per_task"] == 5
        assert args["task_index"] == 2

    def test_new_keys_untouched_when_no_legacy_keys(self, unreal_render_step_handler):
        args = {"handler": "render", "shots_per_task": 7, "task_index": 3}
        unreal_render_step_handler._apply_param_aliases(args)
        assert args["shots_per_task"] == 7
        assert args["task_index"] == 3
        assert "chunk_size" not in args
        assert "chunk_id" not in args

    def test_new_keys_take_precedence_over_legacy(self, unreal_render_step_handler):
        # If both are present (e.g. a hand-edited template), the new keys win.
        args = {
            "handler": "render",
            "shots_per_task": 5,
            "task_index": 2,
            "chunk_size": 99,
            "chunk_id": 88,
        }
        unreal_render_step_handler._apply_param_aliases(args)
        assert args["shots_per_task"] == 5
        assert args["task_index"] == 2

    def test_partial_legacy_keys_each_aliased_independently(self, unreal_render_step_handler):
        # Only one legacy key present — it should be aliased, the new key that
        # is already present left as-is.
        args = {"handler": "render", "chunk_size": 4, "task_index": 1}
        unreal_render_step_handler._apply_param_aliases(args)
        assert args["shots_per_task"] == 4
        assert args["task_index"] == 1

    def test_no_partitioning_keys_is_noop(self, unreal_render_step_handler):
        args = {"handler": "render"}
        unreal_render_step_handler._apply_param_aliases(args)
        assert args == {"handler": "render"}

    def test_returns_same_dict(self, unreal_render_step_handler):
        args = {"handler": "render", "chunk_size": 1}
        assert unreal_render_step_handler._apply_param_aliases(args) is args


class TestCsvCaptureHelpers:
    @pytest.mark.parametrize(
        "args, expected",
        [
            ({}, 0),
            ({"csv_capture_frames": 120}, 120),
            ({"csv_capture_frames": "42"}, 42),
            ({"csv_capture_frames": 0}, 0),
            ({"csv_capture_frames": -5}, 0),
        ],
    )
    def test_get_csv_capture_frames(self, unreal_render_step_handler, args, expected):
        assert unreal_render_step_handler._get_csv_capture_frames(args) == expected

    def test_stop_executor_csv_capture_calls_hook(self, unreal_render_step_handler):
        executor = MagicMock()

        unreal_render_step_handler._stop_executor_csv_capture(executor, "render completed")

        executor._stop_csv_capture.assert_called_once_with("render completed")


class TestExecutorProfilingLifecycle:
    @staticmethod
    def _executor(**overrides):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler,
        )

        executor = SimpleNamespace()
        unreal_render_step_handler._initialize_executor_profiling_state(executor)
        for name, value in overrides.items():
            setattr(executor, name, value)
        return executor

    def test_disabled_profiling_completion_runs_no_console_commands(self):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler,
        )

        executor = self._executor()
        with (
            patch.object(
                unreal_render_step_handler, "_execute_editor_console_command"
            ) as execute_command,
            patch.object(unreal_render_step_handler.logger, "info") as log_info,
        ):
            unreal_render_step_handler._handle_executor_render_completion(executor)

        execute_command.assert_not_called()
        log_info.assert_called_once_with("Render Executor: Rendering is complete")
        assert executor.renderCompletionHandled is True
        assert executor.csvFinished is True
        assert executor.memreportGenerated is False

    def test_csv_capture_stops_after_requested_render_frames(self):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler,
        )

        executor = self._executor(csvCaptureFrames=2)
        with patch.object(
            unreal_render_step_handler,
            "_execute_editor_console_command",
            return_value=True,
        ) as execute_command:
            unreal_render_step_handler._observe_executor_csv_frame(executor)
            assert executor.csvStarted is True
            assert executor.csvFramesObserved == 1

            unreal_render_step_handler._observe_executor_csv_frame(executor)

        assert execute_command.call_args_list == [
            call("CsvProfile Start"),
            call("CsvProfile Stop"),
        ]
        assert executor.csvFramesObserved == 2
        assert executor.csvStarted is False
        assert executor.csvFinished is True

    def test_csv_capture_is_not_retried_when_start_fails(self):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler,
        )

        executor = self._executor(csvCaptureFrames=2)
        with patch.object(
            unreal_render_step_handler,
            "_execute_editor_console_command",
            return_value=False,
        ) as execute_command:
            unreal_render_step_handler._observe_executor_csv_frame(executor)
            unreal_render_step_handler._observe_executor_csv_frame(executor)

        execute_command.assert_called_once_with("CsvProfile Start")
        assert executor.csvStarted is False
        assert executor.csvFinished is True

    def test_memreport_is_generated_only_once(self):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler,
        )

        executor = self._executor(memreportEnabled=True)
        with patch.object(
            unreal_render_step_handler,
            "_execute_editor_console_command",
            return_value=True,
        ) as execute_command:
            unreal_render_step_handler._generate_executor_memreport(executor)
            unreal_render_step_handler._generate_executor_memreport(executor)

        execute_command.assert_called_once_with("MemReport -full")
        assert executor.memreportGenerated is True

    def test_insights_trace_starts_and_stops_once(self):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler,
        )

        executor = self._executor(
            insightsCategories="cpu,frame",
            insightsTraceFile="DeadlineCloud/task-0.utrace",
        )
        with (
            patch.object(
                unreal_render_step_handler,
                "unreal",
                SimpleNamespace(
                    Paths=SimpleNamespace(
                        profiling_dir=lambda: "../../../Project/Saved/Profiling",
                        convert_relative_path_to_full=lambda _: "C:/Project/Saved/Profiling",
                    )
                ),
            ),
            patch.object(
                unreal_render_step_handler,
                "_execute_editor_console_command",
                return_value=True,
            ) as execute_command,
            patch.object(
                unreal_render_step_handler,
                "_wait_for_finalized_insights_trace",
                return_value=True,
            ) as wait_for_trace,
        ):
            unreal_render_step_handler._start_executor_insights_trace(executor)
            unreal_render_step_handler._start_executor_insights_trace(executor)
            unreal_render_step_handler._stop_executor_insights_trace(executor, "render completed")
            unreal_render_step_handler._stop_executor_insights_trace(executor, "render completed")

        assert execute_command.call_args_list == [
            call("Trace.File DeadlineCloud/task-0.utrace cpu,frame"),
            call("Trace.Stop"),
        ]
        wait_for_trace.assert_called_once_with(
            unreal_render_step_handler.os.path.join(
                "C:/Project/Saved/Profiling", "DeadlineCloud/task-0.utrace"
            )
        )
        assert executor.insightsStarted is False
        assert executor.insightsFinished is True

    def test_startup_insights_trace_waits_for_async_stop_before_task_trace(self):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler,
        )

        trace_file = "C:/Project/Saved/Profiling/DeadlineCloud/startup.utrace"
        with (
            patch.object(
                unreal_render_step_handler,
                "_execute_editor_console_command",
                return_value=True,
            ) as execute_command,
            patch.object(
                unreal_render_step_handler,
                "_wait_for_finalized_insights_trace",
                return_value=True,
            ) as wait_for_trace,
        ):
            assert unreal_render_step_handler._finalize_startup_insights_trace(trace_file)

        execute_command.assert_called_once_with("Trace.Stop")
        wait_for_trace.assert_called_once_with(trace_file)

    def test_wait_for_finalized_insights_trace_retries_windows_lock(self):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler,
        )

        with (
            patch.object(
                unreal_render_step_handler.os,
                "open",
                side_effect=[PermissionError("locked"), 42],
            ) as open_trace,
            patch.object(unreal_render_step_handler.os, "close") as close_trace,
            patch.object(unreal_render_step_handler.time, "sleep") as sleep,
        ):
            finalized = unreal_render_step_handler._wait_for_finalized_insights_trace(
                "startup.utrace"
            )

        assert finalized is True
        assert open_trace.call_count == 2
        close_trace.assert_called_once_with(42)
        sleep.assert_called_once_with(0.1)

    def test_task_insights_trace_uses_native_profiling_subdirectory(self):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler,
        )

        with patch.object(
            unreal_render_step_handler.uuid,
            "uuid4",
            return_value=SimpleNamespace(hex="abc123"),
        ):
            trace_file = unreal_render_step_handler._get_task_insights_trace_file({"task_index": 3})

        expected_trace_file = "DeadlineCloud/deadline-cloud-insights-task-3-abc123.utrace"
        assert trace_file == expected_trace_file

    def test_completion_attempts_all_profilers_and_is_idempotent(self):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler,
        )

        executor = self._executor(
            csvCaptureFrames=10,
            csvStarted=True,
            memreportEnabled=True,
            insightsCategories="cpu,frame",
            insightsTraceFile="DeadlineCloud/task-0.utrace",
            insightsStarted=True,
        )
        with (
            patch.object(
                unreal_render_step_handler,
                "_execute_editor_console_command",
                return_value=True,
            ) as execute_command,
            patch.object(
                unreal_render_step_handler,
                "_wait_for_finalized_insights_trace",
                return_value=True,
            ),
            patch.object(
                unreal_render_step_handler,
                "_resolve_insights_trace_file",
                return_value="C:/Project/Saved/Profiling/DeadlineCloud/task-0.utrace",
            ),
        ):
            unreal_render_step_handler._handle_executor_render_completion(executor)
            unreal_render_step_handler._handle_executor_render_completion(executor)

        assert execute_command.call_args_list == [
            call("CsvProfile Stop"),
            call("MemReport -full"),
            call("Trace.Stop"),
        ]
        assert executor.csvFinished is True
        assert executor.memreportGenerated is True
        assert executor.insightsFinished is True
        assert executor.renderCompletionHandled is True

    def test_profiler_failure_cannot_suppress_render_completion(self):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler,
        )

        executor = self._executor(memreportEnabled=True)
        with (
            patch.object(
                unreal_render_step_handler,
                "_stop_executor_csv_capture",
                side_effect=RuntimeError("CSV failure"),
            ),
            patch.object(
                unreal_render_step_handler,
                "_generate_executor_memreport",
                side_effect=RuntimeError("MemReport failure"),
            ),
            patch.object(
                unreal_render_step_handler,
                "_stop_executor_insights_trace",
                side_effect=RuntimeError("Insights failure"),
            ),
            patch.object(unreal_render_step_handler.logger, "info") as log_info,
        ):
            unreal_render_step_handler._handle_executor_render_completion(executor)

        log_info.assert_called_once_with("Render Executor: Rendering is complete")
        assert executor.renderCompletionHandled is True


class TestMemreportHelpers:
    @pytest.mark.parametrize(
        "args, expected",
        [
            ({}, False),
            ({"memreport": True}, True),
            ({"memreport": 1}, True),
            ({"memreport": "true"}, True),
            ({"memreport": "false"}, False),
            ({"memreport": 0}, False),
        ],
    )
    def test_get_memreport_enabled(self, unreal_render_step_handler, args, expected):
        assert unreal_render_step_handler._get_memreport_enabled(args) is expected

    def test_generate_executor_memreport_calls_hook(self, unreal_render_step_handler):
        executor = MagicMock()

        unreal_render_step_handler._generate_executor_memreport(executor)

        executor._generate_memreport.assert_called_once_with()

    def test_handle_executor_completion_prefers_executor_hook(self, unreal_render_step_handler):
        executor = MagicMock()

        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler."
            "UnrealRenderStepHandler._stop_executor_csv_capture"
        ) as stop_capture_mock:
            with patch(
                "deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler."
                "UnrealRenderStepHandler._generate_executor_memreport"
            ) as generate_memreport_mock:
                unreal_render_step_handler._handle_executor_completion(executor)

        executor._handle_render_completion.assert_called_once_with()
        stop_capture_mock.assert_not_called()
        generate_memreport_mock.assert_not_called()

    def test_handle_executor_completion_falls_back_to_legacy_hooks(
        self, unreal_render_step_handler
    ):
        executor = object()

        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler."
            "UnrealRenderStepHandler._stop_executor_csv_capture"
        ) as stop_capture_mock:
            with patch(
                "deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler."
                "UnrealRenderStepHandler._generate_executor_memreport"
            ) as generate_memreport_mock:
                with patch(
                    "deadline.unreal_adaptor.UnrealClient.step_handlers."
                    "unreal_render_step_handler.UnrealRenderStepHandler."
                    "_stop_executor_insights_trace"
                ) as stop_insights_mock:
                    unreal_render_step_handler._handle_executor_completion(executor)

        stop_capture_mock.assert_called_once_with(executor, "render completed")
        generate_memreport_mock.assert_called_once_with(executor)
        stop_insights_mock.assert_called_once_with(executor, "render completed")

    def test_executor_finished_callback_requests_memreport(self, unreal_render_step_handler):
        executor = MagicMock()

        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler."
            "UnrealRenderStepHandler._handle_executor_completion"
        ) as handle_completion_mock:
            unreal_render_step_handler.executor_finished_callback(executor, True)

        handle_completion_mock.assert_called_once_with(executor)

    def test_executor_finished_callback_uses_active_executor(self, unreal_render_step_handler):
        executor = MagicMock()
        type(unreal_render_step_handler).active_executor = executor

        with patch.object(
            type(unreal_render_step_handler), "_handle_executor_completion"
        ) as handle_completion:
            unreal_render_step_handler.executor_finished_callback()

        handle_completion.assert_called_once_with(executor)

    def test_executor_failed_callback_uses_active_executor(self, unreal_render_step_handler):
        executor = MagicMock()
        type(unreal_render_step_handler).active_executor = executor

        with (
            patch.object(
                type(unreal_render_step_handler), "_stop_executor_csv_capture"
            ) as stop_csv,
            patch.object(
                type(unreal_render_step_handler), "_stop_executor_insights_trace"
            ) as stop_insights,
        ):
            unreal_render_step_handler.executor_failed_callback(
                None,
                None,
                True,
                "failed",
            )

        stop_csv.assert_called_once_with(executor, "render error")
        stop_insights.assert_called_once_with(executor, "render error")


class TestRenderWaitResult:
    def test_regex_pattern_complete_supports_explicit_and_engine_completion(
        self, unreal_render_step_handler
    ):
        regexes = unreal_render_step_handler.regex_pattern_complete()

        assert regexes[0].search("Render Executor: Rendering is complete")
        assert regexes[1].search(
            "LogMovieRenderPipeline: MoviePipelineLinearExecutorBase finished 1 jobs in +00:00:04.017."
        )

    def test_wait_result_keeps_waiting_until_completion_is_handled(
        self, unreal_render_step_handler
    ):
        executor = MagicMock()
        executor.renderCompletionHandled = False
        type(unreal_render_step_handler).active_executor = executor

        unreal_render_step_handler.wait_result()

        assert type(unreal_render_step_handler).active_executor is executor
        assert type(unreal_render_step_handler).render_wait_started is True

    def test_wait_result_finishes_after_delegate_handles_completion(
        self, unreal_render_step_handler
    ):
        executor = MagicMock()
        executor.renderCompletionHandled = True
        type(unreal_render_step_handler).active_executor = executor
        type(unreal_render_step_handler).render_wait_started = True

        unreal_render_step_handler.wait_result()

        assert type(unreal_render_step_handler).active_executor is None
        assert type(unreal_render_step_handler).render_wait_started is False

    def test_wait_result_finishes_after_native_profiling_operations(
        self, unreal_render_step_handler
    ):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler as render_module,
        )

        executor = SimpleNamespace()
        render_module._initialize_executor_profiling_state(executor)
        executor.csvStarted = True
        executor.memreportEnabled = True
        type(unreal_render_step_handler).active_executor = executor
        implementation_library = SimpleNamespace(
            stop_csv_capture=MagicMock(),
            request_mem_report=MagicMock(),
            is_csv_capture_complete=MagicMock(side_effect=[False, True]),
            is_mem_report_complete=MagicMock(side_effect=[False, True]),
        )

        with patch.object(
            render_module,
            "unreal",
            SimpleNamespace(DeadlineExecutorImplementationLibrary=implementation_library),
        ):
            render_module._handle_executor_render_completion(executor)
            unreal_render_step_handler.wait_result()

            assert executor.renderCompletionHandled is False
            assert type(unreal_render_step_handler).active_executor is executor

            unreal_render_step_handler.wait_result()

        implementation_library.stop_csv_capture.assert_called_once_with()
        implementation_library.request_mem_report.assert_called_once_with()
        assert executor.renderCompletionHandled is True
        assert type(unreal_render_step_handler).active_executor is None

    def test_wait_result_releases_profiling_completion_after_timeout(
        self, unreal_render_step_handler
    ):
        from deadline.unreal_adaptor.UnrealClient.step_handlers import (
            unreal_render_step_handler as render_module,
        )

        executor = SimpleNamespace()
        render_module._initialize_executor_profiling_state(executor)
        executor.renderCompletionRequested = True
        executor.csvCompletionPending = True
        executor.profilingWaitStartedAt = 100
        type(unreal_render_step_handler).active_executor = executor
        implementation_library = SimpleNamespace(
            is_csv_capture_complete=MagicMock(return_value=False)
        )

        with (
            patch.object(
                render_module,
                "unreal",
                SimpleNamespace(DeadlineExecutorImplementationLibrary=implementation_library),
            ),
            patch.object(render_module.time, "monotonic", return_value=401),
            patch.object(render_module.logger, "warning") as log_warning,
        ):
            unreal_render_step_handler.wait_result()

        log_warning.assert_called_once_with(
            "Render Executor: Profiling finalization timed out after %s seconds",
            render_module.PROFILING_COMPLETION_TIMEOUT_SECONDS,
        )
        assert executor.renderCompletionHandled is True
        assert type(unreal_render_step_handler).active_executor is None


class TestConsoleCommandWorld:
    @staticmethod
    def _module():
        from deadline.unreal_adaptor.UnrealClient.step_handlers import unreal_render_step_handler

        unreal_render_step_handler.unreal = unreal_mock
        unreal_mock.reset_mock()
        return unreal_render_step_handler

    def test_prefers_pie_world(self):
        unreal_render_step_handler = self._module()
        pie_world = object()
        unreal_render_step_handler.unreal.EditorLevelLibrary.get_pie_worlds.return_value = [
            pie_world
        ]

        assert unreal_render_step_handler._get_command_world() is pie_world

    def test_falls_back_to_game_world(self):
        unreal_render_step_handler = self._module()
        game_world = object()
        unreal_render_step_handler.unreal.EditorLevelLibrary.get_pie_worlds.return_value = []
        unreal_render_step_handler.unreal.EditorLevelLibrary.get_game_world.return_value = (
            game_world
        )

        assert unreal_render_step_handler._get_command_world() is game_world

    def test_falls_back_to_editor_world(self):
        unreal_render_step_handler = self._module()
        editor_world = object()
        unreal_render_step_handler.unreal.EditorLevelLibrary.get_pie_worlds.return_value = []
        unreal_render_step_handler.unreal.EditorLevelLibrary.get_game_world.return_value = None
        unreal_render_step_handler.unreal.get_editor_subsystem.return_value = None
        unreal_render_step_handler.unreal.EditorLevelLibrary.get_editor_world.return_value = (
            editor_world
        )

        assert unreal_render_step_handler._get_command_world() is editor_world

    def test_console_command_failure_is_nonfatal(self):
        unreal_render_step_handler = self._module()
        pie_world = object()
        unreal_render_step_handler.unreal.EditorLevelLibrary.get_pie_worlds.return_value = [
            pie_world
        ]
        unreal_render_step_handler.unreal.SystemLibrary.execute_console_command.side_effect = (
            RuntimeError("console unavailable")
        )

        assert (
            unreal_render_step_handler._execute_editor_console_command("MemReport -full") is False
        )
