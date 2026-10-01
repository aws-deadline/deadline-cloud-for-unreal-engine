# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import os
import re
import ast
import sys
import traceback
from unittest.mock import Mock, PropertyMock, patch, mock_open

import pytest
import jsonschema  # type: ignore


from deadline.unreal_adaptor.UnrealAdaptor import UnrealAdaptor
from deadline.unreal_adaptor.UnrealAdaptor.adaptor import UnrealNotRunningError


@pytest.fixture()
def init_data() -> dict:
    """
    Pytest Fixture to return an init_data dictionary that passes validation

    Returns:
        dict: An init_data dictionary
    """
    return {
        "project_path": "C:/LocalProjects/AWS_RND/AWS_RND.uproject",
    }


@pytest.fixture()
def run_data() -> dict:
    """
    Pytest Fixture to return a run_data dictionary that passes validation

    Returns:
        dict: A run_data dictionary
    """
    return {
        "handler": "render",
        "level_path": "/Game/Test/TestLevel",
        "level_sequence_path": "/Game/Test/TestLevelSequence",
        "job_configuration_path": "/Game/Test/Config",
        "queue_manifest_path": "C:/LocalProjects/AWS_RND/Saved/MovieRenderPipeline/QueueManifest.utxt",
        "script_path": "C:/path/to/custom_script.py",
        "script_args": "foo=1 bar=2 -force",
    }


class TestUnrealAdaptor_on_start:
    def test_extract_csv_capture_frames_arg(self):
        filtered_args, csv_capture_frames = UnrealAdaptor._extract_csv_capture_frames_arg(
            ["-csvGpuStats", "-csvCaptureFrames=120", "-trace=cpu,frame"]
        )

        assert filtered_args == ["-csvGpuStats", "-trace=cpu,frame"]
        assert csv_capture_frames == 120

    def test_extract_csv_capture_frames_preserves_following_switch(self):
        filtered_args, csv_capture_frames = UnrealAdaptor._extract_csv_capture_frames_arg(
            ["-csvCaptureFrames", "-unattended", "-trace=cpu,frame"]
        )

        assert filtered_args == ["-unattended", "-trace=cpu,frame"]
        assert csv_capture_frames is None

    def test_extract_memreport_arg(self):
        filtered_args, memreport_enabled = UnrealAdaptor._extract_memreport_arg(
            ["-stdout", "-MemReport", "-trace=cpu,frame"]
        )

        assert filtered_args == ["-stdout", "-trace=cpu,frame"]
        assert memreport_enabled is True

    def test_extract_insights_arg(self):
        filtered_args, insights_categories = UnrealAdaptor._extract_insights_arg(
            [
                "-stdout",
                "-DeadlineCloudInsights=cpu,frame,bookmark",
                "-trace=gpu",
            ]
        )

        assert filtered_args == ["-stdout", "-trace=gpu"]
        assert insights_categories == "cpu,frame,bookmark"

    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.logger")
    def test_extract_insights_arg_rejects_console_command_injection(self, mock_logger: Mock):
        filtered_args, insights_categories = UnrealAdaptor._extract_insights_arg(
            ["-DeadlineCloudInsights=cpu;quit"]
        )

        assert filtered_args == []
        assert insights_categories is None
        mock_logger.warning.assert_called_once()

    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_no_error(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_telemetry_client: Mock,
        init_data: dict,
    ) -> None:
        """Tests that on_start completes without error"""
        adaptor = UnrealAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        adaptor.on_start()

    @patch("time.sleep")
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test__wait_for_socket(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_telemetry_client: Mock,
        mock_sleep: Mock,
        init_data: dict,
    ) -> None:
        """Tests that the _wait_for_socket method sleeps until a socket is available"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)
        socket_mock = PropertyMock(
            side_effect=[None, None, None, "/tmp/9999", "/tmp/9999", "/tmp/9999"]
        )
        type(mock_server.return_value).server_path = socket_mock

        # WHEN
        adaptor.on_start()

        # THEN
        assert mock_sleep.call_count == 3

    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    @patch("threading.Thread")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_server_init_fail(
        self, mock_server: Mock, mock_thread: Mock, mock_telemetry_client: Mock, init_data: dict
    ) -> None:
        """Tests that an error is raised if no socket becomes available"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)

        with (
            patch.object(adaptor, "_SERVER_START_TIMEOUT_SECONDS", 0.01),
            pytest.raises(RuntimeError) as exc_info,
        ):
            # WHEN
            adaptor.on_start()

        # THEN
        assert (
            str(exc_info.value)
            == "Could not find a socket path because the server did not finish initializing"
        )

    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    @patch("threading.Thread")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_error_emits_stack_trace_telemetry(
        self, mock_server: Mock, mock_thread: Mock, mock_telemetry_client: Mock, init_data: dict
    ) -> None:
        """Tests that adaptor errors emit telemetry with stack traces via record_error_with_trace"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)
        mock_tc = mock_telemetry_client.return_value

        with (
            patch.object(adaptor, "_SERVER_START_TIMEOUT_SECONDS", 0.01),
            pytest.raises(RuntimeError),
        ):
            # WHEN
            adaptor.on_start()

        # THEN — record_error_with_trace is called (not record_error)
        mock_tc.record_error_with_trace.assert_called_once()
        call_kwargs = mock_tc.record_error_with_trace.call_args
        assert isinstance(call_kwargs.kwargs["exc"], RuntimeError)
        assert call_kwargs.kwargs["exception_scope"] == "on_start"
        assert call_kwargs.kwargs["extra_details"]["error_operation"] == "on_start"
        mock_tc.record_error.assert_not_called()

    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    def test_inline_exception_still_has_traceback(
        self, mock_telemetry_client: Mock, init_data: dict
    ) -> None:
        """
        Regression: call sites that construct the exception inline (e.g. on_run's
        UnrealNotRunningError path) must still emit a traceback naming the
        originating frame. The traceback must be inspected at record time via a
        side_effect — `raise` mutates `exc.__traceback__` in place, so checking
        it after the fact passes even if recording happened before the raise.
        """
        # GIVEN
        adaptor = UnrealAdaptor(init_data)
        mock_tc = mock_telemetry_client.return_value
        frames_at_record_time: list = []
        mock_tc.record_error_with_trace.side_effect = (
            lambda exc, **kw: frames_at_record_time.extend(traceback.extract_tb(exc.__traceback__))
        )

        # WHEN — on_run with _unreal_is_running False triggers the inline-exception path
        with pytest.raises(UnrealNotRunningError):
            adaptor.on_run({})

        # THEN — the traceback recorded at call time names the originating frame
        mock_tc.record_error_with_trace.assert_called_once()
        assert any(frame.name == "on_run" for frame in frames_at_record_time)

    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    @patch("threading.Thread")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_telemetry_failure_does_not_mask_original_error(
        self, mock_server: Mock, mock_thread: Mock, mock_telemetry_client: Mock, init_data: dict
    ) -> None:
        """Tests that if record_error_with_trace raises, the original exception is still raised"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)
        mock_tc = mock_telemetry_client.return_value
        mock_tc.record_error_with_trace.side_effect = Exception("telemetry broke")

        with (
            patch.object(adaptor, "_SERVER_START_TIMEOUT_SECONDS", 0.01),
            pytest.raises(RuntimeError, match="server did not finish initializing"),
        ):
            # WHEN
            adaptor.on_start()

        # THEN — telemetry was attempted but the original RuntimeError was raised, not the
        # telemetry Exception
        mock_tc.record_error_with_trace.assert_called_once()

    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.ActionsQueue.__len__", return_value=1)
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_unreal_init_timeout(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_telemetry_client: Mock,
        init_data: dict,
    ) -> None:
        """
        Tests that a TimeoutError is raised if the unreal client does not complete initialization
        tasks within a given time frame
        """
        # GIVEN
        adaptor = UnrealAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        new_timeout = 0.01

        with (
            patch.object(adaptor, "_UNREAL_START_TIMEOUT_SECONDS", new_timeout),
            pytest.raises(TimeoutError) as exc_info,
        ):
            # WHEN
            adaptor.on_start()

        # THEN
        error_msg = (
            f"Unreal did not complete initialization actions in {new_timeout} seconds and "
            "failed to start."
        )
        assert str(exc_info.value) == error_msg

    @patch.object(UnrealAdaptor, "_unreal_is_running", False)
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.ActionsQueue.__len__", return_value=1)
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_unreal_init_fail(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_telemetry_client: Mock,
        init_data: dict,
    ) -> None:
        """
        Tests that an RuntimeError is raised if the unreal client encounters an exception
        """
        # GIVEN
        adaptor = UnrealAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"

        with pytest.raises(RuntimeError) as exc_info:
            # WHEN
            adaptor.on_start()

        # THEN
        error_msg = (
            "Unreal encountered an error and was not able to complete initialization actions."
        )
        assert str(exc_info.value) == error_msg

    @patch.object(UnrealAdaptor, "_unreal_is_running", False)
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.ActionsQueue.__len__", return_value=1)
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_init_data_wrong_schema(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
    ) -> None:
        """
        Tests that an RuntimeError is raised if the unreal client encounters an exception
        """
        # GIVEN
        init_data = {"doesNot": "conform", "thisData": "isBad"}
        adaptor = UnrealAdaptor(init_data)

        with pytest.raises(jsonschema.exceptions.ValidationError) as exc_info:
            # WHEN
            adaptor.on_start()

        # THEN
        error_msg = " is a required property"
        assert error_msg in exc_info.value.message

    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.unreal_client_path",
        new_callable=PropertyMock,
    )
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_regex_callbacks",
        return_value=[],
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.logger")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    def test__start_unreal_client_default(
        self,
        mock_subprocess: Mock,
        mock_logger: Mock,
        mock_get_regex_callbacks: Mock,
        mock_unreal_client_path: Mock,
        init_data: dict,
    ):
        """Tests that an UnrealAdaptor starts UE properly with default executable and project path from init_data"""

        # GIVEN
        unreal_client_path = "UnrealClient.py"
        mock_unreal_client_path.side_effect = [unreal_client_path]
        adaptor = UnrealAdaptor(init_data)

        # WHEN
        adaptor._start_unreal_client()

        # THEN
        log_calls = mock_logger.mock_calls

        assert log_calls[0].args == ("execcmds: None",)

        launch_ue_with_message: str = (
            log_calls[1].args[0].replace("Starting Unreal Engine with args: ", "")
        )
        launch_args = ast.literal_eval(launch_ue_with_message)
        assert launch_args[0] == "UnrealEditor-Cmd"
        assert launch_args[1] == init_data["project_path"]
        assert unreal_client_path in launch_args[-1]

    @patch("os.path.exists", return_value=True)
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.unreal_client_path",
        new_callable=PropertyMock,
    )
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_regex_callbacks",
        return_value=[],
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.logger")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    def test__start_unreal_client_with_extra_cmd_args(
        self,
        mock_subprocess: Mock,
        mock_logger: Mock,
        mock_get_regex_callbacks: Mock,
        mock_unreal_client_path: Mock,
        os_path_exists: Mock,
        init_data: dict,
    ):
        """Tests that an UnrealAdaptor starts UE properly with additional cmd arguments"""

        # GIVEN
        extra_cmd_flag = "-ExtraCmdFlag"
        extra_cmd_arg = "-ExtraCmdNamedArg=ExtraCmdValue"
        init_data["extra_cmd_args_file"] = "path/to/args/file.txt"

        unreal_client_path = "UnrealClient.py"
        mock_unreal_client_path.side_effect = [unreal_client_path]
        adaptor = UnrealAdaptor(init_data)

        # WHEN
        with patch(
            "builtins.open",
            new_callable=mock_open,
            read_data=extra_cmd_flag + " " + extra_cmd_arg,
        ):
            adaptor._start_unreal_client()

        # THEN
        log_calls = mock_logger.mock_calls

        launch_ue_with_message: str = (
            log_calls[1].args[0].replace("Starting Unreal Engine with args: ", "")
        )
        launch_args = ast.literal_eval(launch_ue_with_message)
        assert extra_cmd_flag in launch_args
        assert extra_cmd_arg in launch_args
        assert unreal_client_path in launch_args[-1]

    @patch("os.path.exists", return_value=True)
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.unreal_client_path",
        new_callable=PropertyMock,
    )
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_regex_callbacks",
        return_value=[],
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.logger")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    def test__start_unreal_client_defers_csv_capture_frames(
        self,
        mock_subprocess: Mock,
        mock_logger: Mock,
        mock_get_regex_callbacks: Mock,
        mock_unreal_client_path: Mock,
        os_path_exists: Mock,
        init_data: dict,
    ):
        init_data["extra_cmd_args_file"] = "path/to/args/file.txt"

        unreal_client_path = "UnrealClient.py"
        mock_unreal_client_path.side_effect = [unreal_client_path]
        adaptor = UnrealAdaptor(init_data)

        with patch(
            "builtins.open",
            new_callable=mock_open,
            read_data="-csvGpuStats -csvCaptureFrames=120",
        ):
            adaptor._start_unreal_client()

        launch_ue_with_message = (
            mock_logger.mock_calls[-1].args[0].replace("Starting Unreal Engine with args: ", "")
        )
        launch_args = ast.literal_eval(launch_ue_with_message)

        assert "-csvGpuStats" in launch_args
        assert not any(arg.startswith("-csvCaptureFrames") for arg in launch_args)
        assert adaptor._csv_capture_frames == 120

    @patch("os.path.exists", return_value=True)
    @patch("os.makedirs")
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.unreal_client_path",
        new_callable=PropertyMock,
    )
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_regex_callbacks",
        return_value=[],
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.logger")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    def test__start_unreal_client_defers_memreport(
        self,
        mock_subprocess: Mock,
        mock_logger: Mock,
        mock_get_regex_callbacks: Mock,
        mock_unreal_client_path: Mock,
        mock_makedirs: Mock,
        os_path_exists: Mock,
        init_data: dict,
    ):
        init_data["extra_cmd_args_file"] = "path/to/args/file.txt"

        unreal_client_path = "UnrealClient.py"
        mock_unreal_client_path.side_effect = [unreal_client_path]
        adaptor = UnrealAdaptor(init_data)

        with patch(
            "builtins.open",
            new_callable=mock_open,
            read_data="-MemReport -trace=cpu,frame",
        ):
            adaptor._start_unreal_client()

        launch_ue_with_message = (
            mock_logger.mock_calls[-1].args[0].replace("Starting Unreal Engine with args: ", "")
        )
        launch_args = ast.literal_eval(launch_ue_with_message)

        assert "-MemReport" not in launch_args
        assert adaptor._memreport_enabled is True

    @patch("time.strftime", return_value="deadline-cloud-insights-20260803-220000.utrace")
    @patch("os.makedirs")
    @patch("os.path.exists", return_value=True)
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.unreal_client_path",
        new_callable=PropertyMock,
    )
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_regex_callbacks",
        return_value=[],
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.logger")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    def test__start_unreal_client_adds_tracefile_for_trace_capture(
        self,
        mock_subprocess: Mock,
        mock_logger: Mock,
        mock_get_regex_callbacks: Mock,
        mock_unreal_client_path: Mock,
        mock_os_path_exists: Mock,
        mock_os_makedirs: Mock,
        mock_strftime: Mock,
        init_data: dict,
    ):
        unreal_client_path = "UnrealClient.py"
        mock_unreal_client_path.side_effect = [unreal_client_path]
        init_data["extra_cmd_args_file"] = "path/to/args/file.txt"
        adaptor = UnrealAdaptor(init_data)

        with patch(
            "builtins.open",
            new_callable=mock_open,
            read_data="-trace=cpu,frame,bookmark,loadtime",
        ):
            adaptor._start_unreal_client()

        launch_ue_with_message = (
            mock_logger.mock_calls[1].args[0].replace("Starting Unreal Engine with args: ", "")
        )
        launch_args = ast.literal_eval(launch_ue_with_message)

        assert any(arg.startswith("-trace=") for arg in launch_args)
        assert (
            "-tracefile=C:/LocalProjects/AWS_RND/Saved/Profiling/DeadlineCloud/"
            "deadline-cloud-insights-20260803-220000.utrace"
        ) in launch_args
        mock_os_makedirs.assert_called_once_with(
            "C:/LocalProjects/AWS_RND/Saved/Profiling/DeadlineCloud", exist_ok=True
        )

    @patch("os.makedirs")
    @patch("os.path.exists", return_value=True)
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.unreal_client_path",
        new_callable=PropertyMock,
    )
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_regex_callbacks",
        return_value=[],
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.logger")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    @pytest.mark.parametrize("insights_categories", ["cpu,frame", "cpu,frame,memory"])
    def test__start_unreal_client_starts_feature_insights_at_launch(
        self,
        mock_subprocess: Mock,
        mock_logger: Mock,
        mock_get_regex_callbacks: Mock,
        mock_unreal_client_path: Mock,
        mock_os_path_exists: Mock,
        mock_os_makedirs: Mock,
        init_data: dict,
        insights_categories: str,
    ):
        mock_unreal_client_path.side_effect = ["UnrealClient.py"]
        init_data["extra_cmd_args_file"] = "path/to/args/file.txt"
        adaptor = UnrealAdaptor(init_data)

        with patch(
            "builtins.open",
            new_callable=mock_open,
            read_data=f"-DeadlineCloudInsights={insights_categories} -stdout",
        ):
            adaptor._start_unreal_client()

        launch_ue_with_message = next(
            call.args[0].replace("Starting Unreal Engine with args: ", "")
            for call in mock_logger.mock_calls
            if call.args and str(call.args[0]).startswith("Starting Unreal Engine with args:")
        )
        launch_args = ast.literal_eval(launch_ue_with_message)

        assert f"-trace={insights_categories}" in launch_args
        assert any(
            "deadline-cloud-insights-startup-" in arg and arg.endswith(".utrace")
            for arg in launch_args
            if arg.lower().startswith("-tracefile=")
        )
        assert not any(arg.lower().startswith("-deadlinecloudinsights") for arg in launch_args)
        assert adaptor._insights_categories == insights_categories
        mock_os_makedirs.assert_called_once()

    @patch("os.path.exists", return_value=True)
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.unreal_client_path",
        new_callable=PropertyMock,
    )
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_regex_callbacks",
        return_value=[],
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.logger")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    def test_raw_trace_takes_precedence_over_feature_insights(
        self,
        mock_subprocess: Mock,
        mock_logger: Mock,
        mock_get_regex_callbacks: Mock,
        mock_unreal_client_path: Mock,
        mock_os_path_exists: Mock,
        init_data: dict,
    ):
        mock_unreal_client_path.side_effect = ["UnrealClient.py"]
        init_data["extra_cmd_args_file"] = "path/to/args/file.txt"
        adaptor = UnrealAdaptor(init_data)

        with (
            patch(
                "builtins.open",
                new_callable=mock_open,
                read_data=(
                    "-DeadlineCloudInsights=cpu,frame " "-trace=gpu -tracefile=C:/manual.utrace"
                ),
            ),
            patch("os.makedirs"),
        ):
            adaptor._start_unreal_client()

        launch_ue_with_message = next(
            call.args[0].replace("Starting Unreal Engine with args: ", "")
            for call in mock_logger.mock_calls
            if call.args and str(call.args[0]).startswith("Starting Unreal Engine with args:")
        )
        launch_args = ast.literal_eval(launch_ue_with_message)

        assert "-trace=gpu" in launch_args
        assert "-tracefile=C:/manual.utrace" in launch_args
        assert adaptor._insights_categories is None
        assert any(
            call.args and str(call.args[0]).startswith("Raw -trace arguments take precedence")
            for call in mock_logger.warning.mock_calls
        )

    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.logger")
    @patch("os.makedirs", side_effect=PermissionError("access denied"))
    def test_get_tracefile_arg_ignores_unwritable_output_directory(
        self, mock_os_makedirs: Mock, mock_logger: Mock
    ):
        tracefile_arg = UnrealAdaptor._get_tracefile_arg(
            "C:/LocalProjects/AWS_RND/AWS_RND.uproject", "-trace=cpu,frame"
        )

        assert tracefile_arg is None
        mock_os_makedirs.assert_called_once()
        mock_logger.warning.assert_called_once()

    @patch("os.path.exists", return_value=True)
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.unreal_client_path",
        new_callable=PropertyMock,
    )
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_regex_callbacks",
        return_value=[],
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.logger")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    def test__start_unreal_client_with_extra_execcmds_arg(
        self,
        mock_subprocess: Mock,
        mock_logger: Mock,
        mock_get_regex_callbacks: Mock,
        mock_unreal_client_path: Mock,
        mock_os_path_exists: Mock,
        init_data: dict,
    ):
        """Tests that an UnrealAdaptor starts UE properly with additional cmd arguments"""

        # GIVEN
        extra_exec_cmds_value = "r.HLOD 123456"
        extra_exec_cmds_arg = f'-execcmds="{extra_exec_cmds_value}"'
        init_data["extra_cmd_args_file"] = "path/to/args/file.txt"

        unreal_client_path = "UnrealClient.py"
        mock_unreal_client_path.side_effect = [unreal_client_path]
        adaptor = UnrealAdaptor(init_data)

        expected_exec_cmds = f"-execcmds={extra_exec_cmds_value},py {unreal_client_path}"

        # WHEN
        with patch(
            "builtins.open",
            new_callable=mock_open,
            read_data=extra_exec_cmds_arg,
        ):
            adaptor._start_unreal_client()

        # THEN
        log_calls = mock_logger.mock_calls

        assert log_calls[0].args == (f"execcmds: {extra_exec_cmds_value}",)

        launch_ue_with_message: str = (
            log_calls[1].args[0].replace("Starting Unreal Engine with args: ", "")
        )
        launch_args = ast.literal_eval(launch_ue_with_message)
        assert expected_exec_cmds in launch_args

    @patch.object(sys, "path", [])
    def test__unreal_client_path_not_found(self, init_data: dict):
        # GIVEN
        adaptor = UnrealAdaptor(init_data)

        # WHEN
        with pytest.raises(FileNotFoundError) as exc_info:
            _ = adaptor.unreal_client_path

        # THEN
        assert (
            str(exc_info.value) == "Could not find unreal_client.py. "
            "Check that the UnrealClient package is in one of the "
            "following directories: []"
        )


class TestUnrealAdaptor_on_run:
    @patch("time.sleep")
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_on_run(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_telemetry_client: Mock,
        mock_sleep: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_run completes without error, and waits"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        # First side_effect value consumed by setter
        is_rendering_mock = PropertyMock(side_effect=[None, True, False])
        UnrealAdaptor._is_rendering = is_rendering_mock
        adaptor.on_start()

        # WHEN
        adaptor.on_run(run_data)

        # THEN
        mock_sleep.assert_called_once_with(1)

    @patch.object(UnrealAdaptor, "_maybe_submit_renders_to_perforce")
    @patch.object(UnrealAdaptor, "_snapshot_output_files", return_value={})
    @patch("time.sleep")
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.ActionsQueue.enqueue_action")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_on_run_injects_deferred_profiling_run_data(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue_len: Mock,
        mock_enqueue_action: Mock,
        mock_telemetry_client: Mock,
        mock_sleep: Mock,
        mock_snapshot_output_files: Mock,
        mock_submit_renders_to_perforce: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        adaptor = UnrealAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        is_rendering_mock = PropertyMock(side_effect=[None, True, False])
        UnrealAdaptor._is_rendering = is_rendering_mock
        adaptor.on_start()
        adaptor._csv_capture_frames = 120
        adaptor._memreport_enabled = True
        adaptor._insights_categories = "cpu,frame"
        adaptor._startup_insights_trace_file = (
            "C:/LocalProjects/AWS_RND/Saved/Profiling/DeadlineCloud/"
            "deadline-cloud-insights-startup.utrace"
        )

        adaptor.on_run(run_data)

        run_script_action = next(
            call.args[0]
            for call in mock_enqueue_action.call_args_list
            if call.args and getattr(call.args[0], "name", None) == "run_script"
        )

        assert run_script_action.args["csv_capture_frames"] == 120
        assert run_script_action.args["memreport"] is True
        assert run_script_action.args["insights_categories"] == "cpu,frame"
        assert run_script_action.args["startup_insights_trace_file"].endswith(
            "deadline-cloud-insights-startup.utrace"
        )
        assert adaptor._startup_insights_trace_file is None
        assert "csv_capture_frames" not in run_data
        assert "memreport" not in run_data
        assert "insights_categories" not in run_data

    @patch("time.sleep")
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._is_rendering",
        new_callable=PropertyMock,
    )
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._unreal_is_running",
        new_callable=PropertyMock,
    )
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_on_run_render_fail(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_telemetry_client: Mock,
        mock_unreal_is_running: Mock,
        mock_is_rendering: Mock,
        mock_sleep: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_run raises an error if the render fails"""
        # GIVEN
        mock_is_rendering.side_effect = [None, True, False]
        mock_unreal_is_running.side_effect = [True, True, True, False, False]
        mock_logging_subprocess.return_value.returncode = 1
        adaptor = UnrealAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        adaptor.on_start()

        # Capture the traceback at record time — `raise` mutates exc.__traceback__
        # in place, so an after-the-fact assertion would pass even if the exception
        # were recorded before being raised.
        frames_at_record_time: list = []
        mock_telemetry_client.return_value.record_error_with_trace.side_effect = (
            lambda exc, **kw: frames_at_record_time.extend(traceback.extract_tb(exc.__traceback__))
        )

        # WHEN
        with pytest.raises(RuntimeError) as exc_info:
            adaptor.on_run(run_data)

        # THEN
        mock_sleep.assert_called_once_with(1)
        assert str(exc_info.value) == (
            "Unreal exited early and did not render successfully, "
            "please check render logs. "
            "Exit code 1"
        )
        # The exit-code exception is constructed inline, so it must be raised and
        # caught before recording for the trace to name the originating frame.
        assert any(frame.name == "on_run" for frame in frames_at_record_time)

    @patch("time.sleep")
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_run_data_wrong_schema(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_telemetry_client: Mock,
        mock_sleep: Mock,
        init_data: dict,
    ) -> None:
        """Tests that on_run completes without error, and waits"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        # First side_effect value consumed by setter
        is_rendering_mock = PropertyMock(side_effect=[None, True, False])
        UnrealAdaptor._is_rendering = is_rendering_mock
        adaptor.on_start()
        run_data = {"bad": "data"}

        with pytest.raises(jsonschema.exceptions.ValidationError) as exc_info:
            # WHEN
            adaptor.on_run(run_data)

        # THEN
        error_msg = " is a required property"
        assert error_msg in exc_info.value.message


class TestUnrealAdaptor_on_stop:
    @patch("time.sleep")
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_on_stop(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_telemetry_client: Mock,
        mock_sleep: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_stop completes without error"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        is_rendering_mock = PropertyMock(return_value=False)
        UnrealAdaptor._is_rendering = is_rendering_mock
        adaptor.on_start()
        adaptor.on_run(run_data)

        # WHEN
        adaptor.on_stop()


class TestUnrealAdaptor_on_cleanup:
    @patch("time.sleep")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.logger")
    def test_on_cleanup_unreal_not_graceful_shutdown(
        self, mock_logger: Mock, mock_sleep: Mock, init_data: dict
    ) -> None:
        """Tests that on_cleanup reports when unreal does not gracefully shutdown"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)

        with (
            patch(
                "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._unreal_is_running",
                new_callable=lambda: True,
            ),
            patch.object(adaptor, "_UNREAL_END_TIMEOUT_SECONDS", 0.01),
            patch.object(adaptor, "_unreal_client") as mock_client,
        ):
            # WHEN
            adaptor.on_cleanup()

        # THEN
        mock_logger.error.assert_called_once_with(
            "Unreal did not complete cleanup actions and failed to gracefully shutdown. Terminating."
        )
        mock_client.terminate.assert_called_once()

    @patch("time.sleep")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.logger")
    def test_on_cleanup_server_not_graceful_shutdown(
        self, mock_logger: Mock, mock_sleep: Mock, init_data: dict
    ) -> None:
        """Tests that on_cleanup reports when the server does not shutdown"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)

        with (
            patch(
                "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._unreal_is_running",
                new_callable=lambda: False,
            ),
            patch.object(adaptor, "_SERVER_END_TIMEOUT_SECONDS", 0.01),
            patch.object(adaptor, "_server_thread") as mock_server_thread,
        ):
            mock_server_thread.is_alive.return_value = True
            # WHEN
            adaptor.on_cleanup()

        # THEN
        mock_logger.error.assert_called_once_with("Failed to shutdown the Unreal Adaptor server.")
        mock_server_thread.join.assert_called_once_with(timeout=0.01)

    @patch("time.sleep")
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.telemetry_client",
        new_callable=PropertyMock,
    )
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealSubprocessWithLogs")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_on_cleanup(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_telemetry_client: Mock,
        mock_sleep: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_stop completes without error"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        is_rendering_mock = PropertyMock(return_value=False)
        UnrealAdaptor._is_rendering = is_rendering_mock

        adaptor.on_start()
        adaptor.on_run(run_data)
        adaptor.on_stop()

        with patch(
            "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._unreal_is_running",
            new_callable=lambda: False,
        ):
            # WHEN
            adaptor.on_cleanup()

    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.update_status")
    def test_handle_complete(self, mock_update_status: Mock, init_data: dict):
        """Tests that the _handle_complete method updates the progress correctly"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)
        regex_callbacks = adaptor._get_regex_callbacks()
        complete_regex = regex_callbacks[2].regex_list[0]

        # WHEN
        match = complete_regex.search("Render Executor: Rendering is complete")
        if match:
            adaptor._handle_complete(match)

        # THEN
        assert match is not None
        mock_update_status.assert_called_once_with(progress=100)

    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.update_status")
    def test_engine_completion_waits_only_when_profiling_is_enabled(
        self, mock_update_status: Mock, init_data: dict
    ):
        adaptor = UnrealAdaptor(init_data)
        complete_regex = adaptor._get_regex_callbacks()[2].regex_list[1]
        match = complete_regex.search(
            "MoviePipelineLinearExecutorBase finished 1 jobs in +00:00:04.017."
        )
        assert match is not None

        adaptor._unreal_is_rendering = True
        adaptor._handle_complete(match)
        mock_update_status.assert_called_once_with(progress=100)

        adaptor._unreal_is_rendering = True
        adaptor._memreport_enabled = True
        adaptor._handle_complete(match)
        mock_update_status.assert_called_once_with(progress=100)

    handle_progress_params = [(0, "Render Executor: Progress: 99.0", 99)]

    @pytest.mark.parametrize("regex_index, stdout, expected_progress", handle_progress_params)
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor.update_status")
    def test_handle_progress(
        self,
        mock_update_status: Mock,
        regex_index: int,
        stdout: str,
        expected_progress: float,
        init_data: dict,
    ) -> None:
        """Tests that the _handle_progress method updates the progress correctly"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)
        regex_callbacks = adaptor._get_regex_callbacks()
        progress_regex = regex_callbacks[1].regex_list[regex_index]

        # WHEN
        match = progress_regex.search(stdout)
        if match:
            adaptor._handle_progress(match)

        # THEN
        assert match is not None
        mock_update_status.assert_called_once_with(progress=expected_progress)

    @pytest.mark.parametrize(
        "stdout, error_regex",
        [
            (
                "Render Executor: Error: Error encountered when initializing Unreal - Please check the logs.",
                re.compile(".*Exception:.*|.*Render Executor: Error:.*"),
            )
        ],
    )
    def test_handle_error(self, init_data: dict, stdout: str, error_regex: re.Pattern) -> None:
        """Tests that the _handle_error method throws a runtime error correctly"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)
        print(stdout)
        print(error_regex)

        # WHEN
        match = error_regex.search(stdout)
        if match:
            adaptor._handle_error(match)

        # THEN
        assert match is not None
        assert str(adaptor._exc_info) == f"Unreal Encountered an Error: {stdout}"

    @pytest.mark.parametrize("adaptor_exc_info", [RuntimeError("Something Bad Happened!"), None])
    def test_has_exception(self, init_data: dict, adaptor_exc_info: Exception | None) -> None:
        """
        Validates that the adaptor._has_exception property raises when adaptor._exc_info is not None
        and returns false when adaptor._exc_info is None
        """
        adaptor = UnrealAdaptor(init_data)
        adaptor._exc_info = adaptor_exc_info

        if adaptor_exc_info:
            with pytest.raises(RuntimeError) as exc_info:
                adaptor._has_exception

            assert exc_info.value == adaptor_exc_info
        else:
            assert not adaptor._has_exception

    @patch.object(
        UnrealAdaptor, "_unreal_is_running", new_callable=PropertyMock(return_value=False)
    )
    def test_raises_if_unreal_not_running(
        self,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_run raises a unrealNotRunningError if unreal is not running"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)

        # WHEN
        with pytest.raises(UnrealNotRunningError) as raised_err:
            adaptor.on_run(run_data)

        # THEN
        assert raised_err.match("Cannot render because Unreal is not running")


class TestUnrealAdaptor_on_cancel:
    """Tests for UnrealAdaptor.on_cancel"""

    def test_terminates_unreal_client(self, init_data: dict, caplog: pytest.LogCaptureFixture):
        """Tests that the unreal client is terminated on cancel"""
        # GIVEN
        caplog.set_level(0)
        adaptor = UnrealAdaptor(init_data)
        adaptor._unreal_client = mock_client = Mock()

        # WHEN
        adaptor.on_cancel()

        # THEN
        mock_client.terminate.assert_called_once_with(grace_time_s=0)
        assert "CANCEL REQUESTED" in caplog.text

    def test_does_nothing_if_unreal_not_running(
        self, init_data: dict, caplog: pytest.LogCaptureFixture
    ):
        """Tests that nothing happens if a cancel is requested when unreal is not running"""
        # GIVEN
        caplog.set_level(0)
        adaptor = UnrealAdaptor(init_data)
        adaptor._unreal_client = None

        # WHEN
        adaptor.on_cancel()

        # THEN
        assert "CANCEL REQUESTED" in caplog.text
        assert "Nothing to cancel because Unreal is not running" in caplog.text


class TestUnrealAdaptor_maybe_submit_renders_to_perforce:
    """Tests for the post-render Perforce submit hook."""

    def _adaptor(self, init_data: dict) -> UnrealAdaptor:
        # The hook only reads run_data and imports app lazily, so we don't
        # actually need on_start to have run.
        return UnrealAdaptor(init_data)

    def _full_run_data(self, output_path: str, mode: str = "submit") -> dict:
        """Helper: a run_data dict with all fields the staging path needs."""
        return {
            "submit_mode": mode,
            "output_path": output_path,
            "project_name": "MyProject",
            "project_relative_path": "MyProject/MyProject.uproject",
        }

    def _populated_session_output(self, tmp_path):
        """
        Build a fake session output dir under tmp_path with a couple of files
        for the per-file shutil.copy2 staging loop to pick up.
        """
        session_output = tmp_path / "session" / "assetroot" / "MovieRenders"
        session_output.mkdir(parents=True)
        (session_output / "frame.0001.png").write_bytes(b"x" * 16)
        (session_output / "frame.0002.png").write_bytes(b"x" * 16)
        return session_output

    # --- early-out cases (no P4 contact, no copy) ---

    def test_no_op_when_submit_mode_missing(self, init_data: dict):
        adaptor = self._adaptor(init_data)
        run_data = {"output_path": "C:/renders/MyProject"}  # no submit_mode

        with patch("deadline.unreal_perforce_utils.app.submit_renders") as submit_mock:
            adaptor._maybe_submit_renders_to_perforce(run_data)

        submit_mock.assert_not_called()

    def test_no_op_when_submit_mode_empty_string(self, init_data: dict):
        adaptor = self._adaptor(init_data)
        run_data = {"submit_mode": "", "output_path": "C:/renders/MyProject"}

        with patch("deadline.unreal_perforce_utils.app.submit_renders") as submit_mock:
            adaptor._maybe_submit_renders_to_perforce(run_data)

        submit_mock.assert_not_called()

    # Missing-prerequisite tests: SubmitMode disables JA output upload
    # upstream, so any missing input means the frames would land nowhere.
    # These paths must RAISE (task fails, Deadline retries), not warn-and-
    # skip (silent data loss).

    def test_raises_when_output_path_missing(self, init_data: dict):
        adaptor = self._adaptor(init_data)
        run_data = {"submit_mode": "submit"}  # no output_path

        with patch("deadline.unreal_perforce_utils.app.submit_renders") as submit_mock:
            with pytest.raises(RuntimeError, match="no output_path"):
                adaptor._maybe_submit_renders_to_perforce(run_data)

        submit_mock.assert_not_called()

    def test_raises_when_project_name_missing(self, init_data: dict):
        adaptor = self._adaptor(init_data)
        run_data = {
            "submit_mode": "submit",
            "output_path": "C:/Perforce/ws/MyProject/Saved/MovieRenders",
        }

        with patch("deadline.unreal_perforce_utils.app.submit_renders") as submit_mock:
            with pytest.raises(RuntimeError, match="no project_name"):
                adaptor._maybe_submit_renders_to_perforce(run_data)

        submit_mock.assert_not_called()

    def test_raises_when_project_relative_path_missing(self, init_data: dict):
        adaptor = self._adaptor(init_data)
        run_data = {
            "submit_mode": "submit",
            "output_path": "C:/renders/MyProject",
            "project_name": "MyProject",
            # project_relative_path missing
        }

        with patch("deadline.unreal_perforce_utils.app.submit_renders") as submit_mock:
            with pytest.raises(RuntimeError, match="no.*project_relative_path"):
                adaptor._maybe_submit_renders_to_perforce(run_data)

        submit_mock.assert_not_called()

    def test_raises_when_p4_client_directory_env_unset(self, init_data: dict, tmp_path):
        # GIVEN P4_CLIENT_DIRECTORY env var is unset (P4 sync env didn't run)
        adaptor = self._adaptor(init_data)
        session_output = self._populated_session_output(tmp_path)
        run_data = self._full_run_data(str(session_output))

        env_no_p4 = {k: v for k, v in os.environ.items() if k != "P4_CLIENT_DIRECTORY"}
        with (
            patch.dict(os.environ, env_no_p4, clear=True),
            patch("deadline.unreal_perforce_utils.app.submit_renders") as submit_mock,
        ):
            with pytest.raises(RuntimeError, match="P4_CLIENT_DIRECTORY env var"):
                adaptor._maybe_submit_renders_to_perforce(run_data)

        submit_mock.assert_not_called()

    # --- staging + submit happy path ---

    def test_stages_into_workspace_then_submits(self, init_data: dict, tmp_path):
        # GIVEN session-side output and a fake P4_CLIENT_DIRECTORY
        adaptor = self._adaptor(init_data)
        session_output = self._populated_session_output(tmp_path)
        p4_client_dir = tmp_path / "Perforce" / "ws-1"
        p4_client_dir.mkdir(parents=True)
        run_data = self._full_run_data(str(session_output))

        # WHEN
        with (
            patch.dict(os.environ, {"P4_CLIENT_DIRECTORY": str(p4_client_dir)}, clear=False),
            patch("deadline.unreal_perforce_utils.app.submit_renders") as submit_mock,
        ):
            adaptor._maybe_submit_renders_to_perforce(run_data)

        # THEN — files were copied into the workspace at
        # <P4_CLIENT_DIR>/MyProject/Saved/MovieRenders/
        expected_dest = p4_client_dir / "MyProject" / "Saved" / "MovieRenders"
        assert (expected_dest / "frame.0001.png").exists()
        assert (expected_dest / "frame.0002.png").exists()
        # session originals are still there for JA
        assert (session_output / "frame.0001.png").exists()

        # AND submit_renders was called with the workspace path, not the session path.
        # The adaptor now always shelves internally regardless of user's SubmitMode
        # ('submit' or 'shelve'); AssembleShelves is the step that finalizes the
        # aggregate CL based on user's SubmitMode. So mode='shelve' here even
        # though run_data submit_mode='submit'.
        #
        # The adaptor also scopes each task's shelve to the exact files it
        # produced (identified via pre/post-render mtime diff) rather than
        # reconciling the whole output_directories tree, so output_directories
        # is empty and explicit_files holds the per-file staged paths.
        submit_mock.assert_called_once()
        kwargs = submit_mock.call_args.kwargs
        assert kwargs["unreal_project_name"] == "MyProject"
        assert kwargs["mode"] == "shelve"
        assert kwargs["output_directories"] == []
        assert set(kwargs["explicit_files"]) == {
            str(expected_dest / "frame.0001.png"),
            str(expected_dest / "frame.0002.png"),
        }

    def test_preserves_custom_output_dir_leaf_name(self, init_data: dict, tmp_path):
        # GIVEN customer renamed their MRQ output to ShotA_Renders rather than
        # the default MovieRenders. The destination should match.
        adaptor = self._adaptor(init_data)
        session_output = tmp_path / "session" / "assetroot" / "ShotA_Renders"
        session_output.mkdir(parents=True)
        (session_output / "frame.png").write_bytes(b"x")
        p4_client_dir = tmp_path / "Perforce" / "ws-1"
        p4_client_dir.mkdir(parents=True)
        run_data = self._full_run_data(str(session_output))

        with (
            patch.dict(os.environ, {"P4_CLIENT_DIRECTORY": str(p4_client_dir)}, clear=False),
            patch("deadline.unreal_perforce_utils.app.submit_renders") as submit_mock,
        ):
            adaptor._maybe_submit_renders_to_perforce(run_data)

        expected_dest = p4_client_dir / "MyProject" / "Saved" / "ShotA_Renders"
        assert (expected_dest / "frame.png").exists()
        assert submit_mock.call_args.kwargs["output_directories"] == []
        assert submit_mock.call_args.kwargs["explicit_files"] == [str(expected_dest / "frame.png")]

    def test_calls_submit_renders_when_mode_is_shelve(self, init_data: dict, tmp_path):
        adaptor = self._adaptor(init_data)
        session_output = self._populated_session_output(tmp_path)
        p4_client_dir = tmp_path / "Perforce" / "ws-1"
        p4_client_dir.mkdir(parents=True)
        run_data = self._full_run_data(str(session_output), mode="shelve")

        with (
            patch.dict(os.environ, {"P4_CLIENT_DIRECTORY": str(p4_client_dir)}, clear=False),
            patch("deadline.unreal_perforce_utils.app.submit_renders") as submit_mock,
        ):
            adaptor._maybe_submit_renders_to_perforce(run_data)

        submit_mock.assert_called_once()
        assert submit_mock.call_args.kwargs["mode"] == "shelve"

    # --- failure handling ---

    def test_raises_when_all_copy2_fail(
        self, init_data: dict, caplog: pytest.LogCaptureFixture, tmp_path
    ):
        # GIVEN every per-file staging copy raises (e.g., destination disk full).
        # SubmitMode is active, so JA output upload is disabled upstream —
        # silent-success would drop every frame on the floor. The task must
        # fail so Deadline retries or surfaces the failure.
        import logging

        adaptor = self._adaptor(init_data)
        session_output = self._populated_session_output(tmp_path)
        p4_client_dir = tmp_path / "Perforce" / "ws-1"
        p4_client_dir.mkdir(parents=True)
        run_data = self._full_run_data(str(session_output))

        with (
            patch.dict(os.environ, {"P4_CLIENT_DIRECTORY": str(p4_client_dir)}, clear=False),
            patch("shutil.copy2", side_effect=OSError("No space left on device")),
            patch("deadline.unreal_perforce_utils.app.submit_renders") as submit_mock,
            caplog.at_level(logging.WARNING),
        ):
            with pytest.raises(RuntimeError, match="failed to stage to the P4 workspace"):
                adaptor._maybe_submit_renders_to_perforce(run_data)

        # submit_renders was never called because staging failed.
        submit_mock.assert_not_called()
        # Per-file failures still logged at WARNING for postmortem visibility.
        assert "No space left on device" in caplog.text

    def test_raises_on_partial_copy2_failure(
        self, init_data: dict, caplog: pytest.LogCaptureFixture, tmp_path
    ):
        # GIVEN some per-file staging copies succeed and one fails. SubmitMode
        # is the sole delivery path in this mode, so a partial stage would
        # silently drop the un-staged frames — the render task would report
        # success, downstream `assemble_shelves` would aggregate an incomplete
        # set, and no one would be alerted. Must fail instead.
        import logging

        adaptor = self._adaptor(init_data)
        session_output = self._populated_session_output(tmp_path)  # produces 2 files
        p4_client_dir = tmp_path / "Perforce" / "ws-1"
        p4_client_dir.mkdir(parents=True)
        run_data = self._full_run_data(str(session_output))

        # First copy2 succeeds, second raises. That's the partial-failure case:
        # one frame is delivered, one is dropped — the exact scenario the
        # reviewer flagged.
        import shutil

        real_copy2 = shutil.copy2
        call_count = {"n": 0}

        def flaky_copy2(src, dst, *args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise OSError("PermissionError on frame.0002.png")
            return real_copy2(src, dst, *args, **kwargs)

        with (
            patch.dict(os.environ, {"P4_CLIENT_DIRECTORY": str(p4_client_dir)}, clear=False),
            patch("shutil.copy2", side_effect=flaky_copy2),
            patch("deadline.unreal_perforce_utils.app.submit_renders") as submit_mock,
            caplog.at_level(logging.WARNING),
        ):
            with pytest.raises(
                RuntimeError, match=r"1 of 2 task-produced file\(s\) failed to stage"
            ):
                adaptor._maybe_submit_renders_to_perforce(run_data)

        # Critically, submit_renders was NOT called with the partial file list —
        # we raised before reaching the shelve step so no incomplete CL is
        # produced.
        submit_mock.assert_not_called()
        # Per-file failure detail is preserved in the WARNING log.
        assert "PermissionError on frame.0002.png" in caplog.text

    def test_p4_failure_raises_when_submit_mode_active(
        self, init_data: dict, caplog: pytest.LogCaptureFixture, tmp_path
    ):
        # BEHAVIOR CHANGE: with the JA-skip feature, when SubmitMode is set the
        # frames go through P4 exclusively. If shelve fails, silent success
        # would mean render outputs vanish. Fail the task so Deadline retries
        # or surfaces the failure — matches the customer's explicit opt-in.
        import logging

        adaptor = self._adaptor(init_data)
        session_output = self._populated_session_output(tmp_path)
        p4_client_dir = tmp_path / "Perforce" / "ws-1"
        p4_client_dir.mkdir(parents=True)
        run_data = self._full_run_data(str(session_output))

        with (
            patch.dict(os.environ, {"P4_CLIENT_DIRECTORY": str(p4_client_dir)}, clear=False),
            patch(
                "deadline.unreal_perforce_utils.app.submit_renders",
                side_effect=RuntimeError("p4 server unreachable"),
            ),
            caplog.at_level(logging.ERROR),
        ):
            with pytest.raises(RuntimeError, match="p4 server unreachable"):
                adaptor._maybe_submit_renders_to_perforce(run_data)

        # Staging still happened before the shelve attempt, and the error
        # was logged loudly before propagating.
        expected_dest = p4_client_dir / "MyProject" / "Saved" / "MovieRenders"
        assert (expected_dest / "frame.0001.png").exists()
        assert "Perforce shelve failed" in caplog.text

    # --- positive confirmation logging on success ---

    def test_logs_confirmation_with_cl_number_when_submit_mode_is_submit(
        self, init_data: dict, caplog: pytest.LogCaptureFixture, tmp_path
    ):
        # GIVEN submit_renders returns the shelved CL number. The user's
        # SubmitMode='submit' — the aggregate is what will get submitted; each
        # task shelves so AssembleShelves can gather them.
        import logging

        adaptor = self._adaptor(init_data)
        session_output = self._populated_session_output(tmp_path)
        p4_client_dir = tmp_path / "Perforce" / "ws-1"
        p4_client_dir.mkdir(parents=True)
        run_data = self._full_run_data(str(session_output), mode="submit")

        with (
            patch.dict(os.environ, {"P4_CLIENT_DIRECTORY": str(p4_client_dir)}, clear=False),
            patch("deadline.unreal_perforce_utils.app.submit_renders", return_value=42),
            caplog.at_level(logging.INFO),
        ):
            adaptor._maybe_submit_renders_to_perforce(run_data)

        # Task-level log always says "shelve complete" now — the final submit
        # decision is deferred to the AssembleShelves step. Log includes both
        # the shelved CL and the user-facing SubmitMode for traceability.
        assert "Perforce shelve complete: CL 42 shelved" in caplog.text
        assert "SHELVED_CL=42" in caplog.text
        assert "SubmitMode='submit'" in caplog.text

    def test_logs_confirmation_with_cl_number_after_shelve(
        self, init_data: dict, caplog: pytest.LogCaptureFixture, tmp_path
    ):
        import logging

        adaptor = self._adaptor(init_data)
        session_output = self._populated_session_output(tmp_path)
        p4_client_dir = tmp_path / "Perforce" / "ws-1"
        p4_client_dir.mkdir(parents=True)
        run_data = self._full_run_data(str(session_output), mode="shelve")

        with (
            patch.dict(os.environ, {"P4_CLIENT_DIRECTORY": str(p4_client_dir)}, clear=False),
            patch("deadline.unreal_perforce_utils.app.submit_renders", return_value=99),
            caplog.at_level(logging.INFO),
        ):
            adaptor._maybe_submit_renders_to_perforce(run_data)

        # THEN
        assert "Perforce shelve complete: CL 99 shelved" in caplog.text

    def test_logs_confirmation_when_nothing_changed(
        self, init_data: dict, caplog: pytest.LogCaptureFixture, tmp_path
    ):
        # GIVEN submit_renders returns None — reconcile found nothing to commit
        import logging

        adaptor = self._adaptor(init_data)
        session_output = self._populated_session_output(tmp_path)
        p4_client_dir = tmp_path / "Perforce" / "ws-1"
        p4_client_dir.mkdir(parents=True)
        run_data = self._full_run_data(str(session_output))

        with (
            patch.dict(os.environ, {"P4_CLIENT_DIRECTORY": str(p4_client_dir)}, clear=False),
            patch("deadline.unreal_perforce_utils.app.submit_renders", return_value=None),
            caplog.at_level(logging.INFO),
        ):
            adaptor._maybe_submit_renders_to_perforce(run_data)

        # THEN — operator gets a clear "no CL was created" message, not silence
        assert "Perforce shelve complete" in caplog.text
        assert "no files changed" in caplog.text

    def test_clears_readonly_on_destination_files_before_copy2(self, init_data: dict, tmp_path):
        # GIVEN a prior P4 submit left files read-only at the destination
        import stat

        adaptor = self._adaptor(init_data)
        session_output = self._populated_session_output(tmp_path)
        p4_client_dir = tmp_path / "Perforce" / "ws-1"
        prior_dest = p4_client_dir / "MyProject" / "Saved" / "MovieRenders"
        prior_dest.mkdir(parents=True)
        # Simulate previously-submitted frames marked read-only by P4 sync
        prior_frame = prior_dest / "frame.0001.png"
        prior_frame.write_bytes(b"old")
        prior_frame.chmod(stat.S_IREAD)
        run_data = self._full_run_data(str(session_output))

        with (
            patch.dict(os.environ, {"P4_CLIENT_DIRECTORY": str(p4_client_dir)}, clear=False),
            patch("deadline.unreal_perforce_utils.app.submit_renders"),
        ):
            # WHEN — must NOT raise PermissionError on the read-only file
            adaptor._maybe_submit_renders_to_perforce(run_data)

        # THEN — file was overwritten (new content from session_output)
        assert prior_frame.read_bytes() == b"x" * 16
