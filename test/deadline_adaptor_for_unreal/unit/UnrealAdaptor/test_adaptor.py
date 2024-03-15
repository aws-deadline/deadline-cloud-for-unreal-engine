# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import re
from unittest.mock import Mock, PropertyMock, patch

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
        "script_args": {"foo": 1, "bar": "2"},
    }


class TestUnrealAdaptor_on_start:
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_deadline_telemetry_client"
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
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_deadline_telemetry_client"
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

    @patch("threading.Thread")
    @patch("deadline.unreal_adaptor.UnrealAdaptor.adaptor.AdaptorServer")
    def test_server_init_fail(self, mock_server: Mock, mock_thread: Mock, init_data: dict) -> None:
        """Tests that an error is raised if no socket becomes available"""
        # GIVEN
        adaptor = UnrealAdaptor(init_data)

        with patch.object(adaptor, "_SERVER_START_TIMEOUT_SECONDS", 0.01), pytest.raises(
            RuntimeError
        ) as exc_info:
            # WHEN
            adaptor.on_start()

        # THEN
        assert (
            str(exc_info.value)
            == "Could not find a socket path because the server did not finish initializing"
        )

    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_deadline_telemetry_client"
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

        with patch.object(adaptor, "_UNREAL_START_TIMEOUT_SECONDS", new_timeout), pytest.raises(
            TimeoutError
        ) as exc_info:
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
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_deadline_telemetry_client"
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


class TestUnrealAdaptor_on_run:
    @patch("time.sleep")
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_deadline_telemetry_client"
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
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_deadline_telemetry_client"
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

        # WHEN
        with pytest.raises(RuntimeError) as exc_info:
            adaptor.on_run(run_data)

        # THEN
        mock_sleep.assert_called_once_with(1)
        assert str(exc_info.value) == (
            "Unreal exited early and did not render successfully, please check render logs. "
            "Exit code 1"
        )

    @patch("time.sleep")
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_deadline_telemetry_client"
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
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_deadline_telemetry_client"
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

        with patch(
            "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._unreal_is_running",
            new_callable=lambda: True,
        ), patch.object(adaptor, "_UNREAL_END_TIMEOUT_SECONDS", 0.01), patch.object(
            adaptor, "_unreal_client"
        ) as mock_client:
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

        with patch(
            "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._unreal_is_running",
            new_callable=lambda: False,
        ), patch.object(adaptor, "_SERVER_END_TIMEOUT_SECONDS", 0.01), patch.object(
            adaptor, "_server_thread"
        ) as mock_server_thread:
            mock_server_thread.is_alive.return_value = True
            # WHEN
            adaptor.on_cleanup()

        # THEN
        mock_logger.error.assert_called_once_with("Failed to shutdown the Unreal Adaptor server.")
        mock_server_thread.join.assert_called_once_with(timeout=0.01)

    @patch("time.sleep")
    @patch(
        "deadline.unreal_adaptor.UnrealAdaptor.adaptor.UnrealAdaptor._get_deadline_telemetry_client"
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
        complete_regex = regex_callbacks[1].regex_list[0]

        # WHEN
        match = complete_regex.search("Render Executor: Rendering is complete")
        if match:
            adaptor._handle_complete(match)

        # THEN
        assert match is not None
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
        progress_regex = regex_callbacks[0].regex_list[regex_index]

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

        print(raised_err)
        # THEN
        assert raised_err.match("Cannot render because Unreal is not running.")


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
