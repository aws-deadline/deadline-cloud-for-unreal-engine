# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import json
import sys
from unittest.mock import Mock, patch, MagicMock
import pytest

# Mock the deadline.client.api module before importing the wrapper
sys.modules["deadline.client.api"] = MagicMock()

from deadline.unreal_submitter.job_submit_wrapper import (  # noqa: E402
    hash_progress_callback,
    upload_progress_callback,
    create_job_result_callback,
    interactive_confirmation_callback,
    print_function_callback,
    main,
)


class TestJobSubmitWrapper:

    def test_hash_progress_callback(self, capsys):
        """Test hash progress callback outputs correct JSON"""
        metadata = Mock()
        metadata.progress = 50.0
        metadata.progressMessage = "Hashing files"

        result = hash_progress_callback(metadata)

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert output["type"] == "hash_progress"
        assert int(output["progress"]) == int(50.0)
        assert output["message"] == "Hashing files"
        assert result is True

    def test_upload_progress_callback(self, capsys):
        """Test upload progress callback outputs correct JSON"""
        metadata = Mock()
        metadata.progress = 75.0
        metadata.progressMessage = "Uploading files"

        result = upload_progress_callback(metadata)

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert output["type"] == "upload_progress"
        assert int(output["progress"]) == int(75.0)
        assert output["message"] == "Uploading files"
        assert result is True

    def test_create_job_result_callback(self, capsys):
        """Test create job result callback outputs correct JSON"""
        result = create_job_result_callback()

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert output["type"] == "create_job_result"
        assert result is True

    def test_interactive_confirmation_callback(self, capsys):
        """Test interactive confirmation callback"""
        result = interactive_confirmation_callback("Test message", True)

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert output["type"] == "debug"
        assert "Test message" in output["message"]
        assert result is True

    def test_print_function_callback(self, capsys):
        """Test print function callback outputs correct JSON"""
        print_function_callback("API message")

        captured = capsys.readouterr()
        output = json.loads(captured.out.strip())

        assert output["type"] == "api_message"
        assert output["message"] == "API message"

    @patch("deadline.unreal_submitter.job_submit_wrapper.create_job_from_job_bundle")
    def test_main_success(self, mock_create_job, capsys):
        """Test main function success case"""
        mock_create_job.return_value = "job-123"

        with patch("sys.argv", ["wrapper.py", "/path/to/bundle", "/project/path"]):
            main()

        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")

        # Check debug messages
        debug_msg = json.loads(lines[0])
        assert debug_msg["type"] == "debug"
        assert "/path/to/bundle" in debug_msg["message"]

        # Check job created message
        job_msg = json.loads(lines[-1])
        assert job_msg["type"] == "job_created"
        assert job_msg["job_id"] == "job-123"

    @patch("deadline.unreal_submitter.job_submit_wrapper.create_job_from_job_bundle")
    def test_main_with_known_asset_path(self, mock_create_job, capsys):
        """Test main function with known asset path"""
        mock_create_job.return_value = "job-456"

        with patch("sys.argv", ["wrapper.py", "/path/to/bundle", "/project/path"]):
            main()

        # Verify create_job_from_job_bundle was called with known_asset_paths
        mock_create_job.assert_called_once()
        call_kwargs = mock_create_job.call_args[1]
        assert "known_asset_paths" in call_kwargs
        assert call_kwargs["known_asset_paths"] == ["/project/path"]

    @patch("deadline.unreal_submitter.job_submit_wrapper.create_job_from_job_bundle")
    def test_main_without_known_asset_path(self, mock_create_job, capsys):
        """Test main function without known asset path"""
        mock_create_job.return_value = "job-789"

        with patch("sys.argv", ["wrapper.py", "/path/to/bundle"]):
            main()

        # Verify create_job_from_job_bundle was with known_asset_paths None
        mock_create_job.assert_called_once()
        call_kwargs = mock_create_job.call_args[1]
        assert call_kwargs["known_asset_paths"] is None

    def test_main_invalid_args(self, capsys):
        """Test main function with invalid arguments"""
        with patch("sys.argv", ["wrapper.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

            captured = capsys.readouterr()
            output = json.loads(captured.out.strip())
            assert output["type"] == "error"
            assert "Usage:" in output["message"]

    @patch("deadline.unreal_submitter.job_submit_wrapper.create_job_from_job_bundle")
    def test_main_exception(self, mock_create_job, capsys):
        """Test main function with exception"""
        mock_create_job.side_effect = Exception("Test error")

        with patch("sys.argv", ["wrapper.py", "/path/to/bundle"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

            captured = capsys.readouterr()
            lines = captured.out.strip().split("\n")
            error_msg = json.loads(lines[-1])
            assert error_msg["type"] == "error"
            assert "Test error" in error_msg["message"]
