# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
from unittest.mock import MagicMock
from unittest import mock

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock


from deadline.unreal_submitter import common  # noqa: E402
from deadline.unreal_submitter import exceptions  # noqa: E402


class TestCommon:

    @pytest.mark.parametrize(
        "path",
        [
            "C:/users/JD/test/test.txt",
            "usr/JD/test/test.txt",
            r"C:\users\JD\test\test.txt",
            r"usr\JD\test\test.txt",
            "{project_dir}/Saved/MovieRenders/{day}{mont}{year}",
            "0123456789!@#$%^&()-_=+{}[];:',./",
        ],
    )
    def test_validate_non_valid_chars_in_path_passed(self, path: str):
        # WHEN
        result = common.validate_path_does_not_contain_non_valid_chars(path)

        # THEN
        assert result

    @pytest.mark.parametrize(
        "path",
        [
            '"{project_dir}/Saved/MovieRenders/Output"',
            '{project_dir}/Saved/MovieRenders/"CopiedAsPath"',
            "{project_dir}/Saved/MovieRenders/MyOutput|NightlyRender",
            '{project_dir}/Saved/MovieRenders/"CopiedAsPath"-*mycomment*',
            '{project_dir}/Saved/MovieRenders/"CopiedAsPath"-notready?',
            '{project_dir}/Saved/MovieRenders/"CopiedAsPath"-<description>',
        ],
    )
    def test_validate_non_valid_chars_in_path_failed(self, path: str):
        # THEN
        with pytest.raises(exceptions.PathContainsNonValidCharacters):
            # WHEN
            common.validate_path_does_not_contain_non_valid_chars(path)

    @pytest.mark.parametrize(
        "deadline_args",
        [
            "-somearg=1",
            "-somearg=1 -Otherarg=1",
            "-somearg=1 -Otherarg=1 -thirdarg",
        ],
    )
    @pytest.mark.parametrize(
        "argstring",
        [
            '-arg1 -arg2 -deadlineargs="<DEADLINEARGS>" -arg3=4',
            '-Deadlineargs="<DEADLINEARGS>" -arg3=4 -arg3=5',
            '-arg1 -arg2 -deadlineargs="<DEADLINEARGS>"',
            "-arg1 -arg2 -deadlineArgs='<DEADLINEARGS>' -arg3=4",
            "-deadlineargs='<DEADLINEARGS>' -arg3=4 -arg3=5",
            "-arg1 -arg2 -deadlineargs='<DEADLINEARGS>'",
        ],
    )
    def test_extract_deadline_args(self, deadline_args: str, argstring: str):
        input_str = argstring.replace("<DEADLINEARGS>", deadline_args)

        assert common.extract_deadline_args(input_str) == deadline_args

    @pytest.mark.parametrize(
        "inherited_args,additional_args,expected_result",
        [
            # Basic case with no special args
            (
                "-arg1 -arg2=value",
                "-add1 -add2=val",
                ["-arg1", "-arg2=value", "-add1", "-add2=val"],
            ),
        ],
    )
    def test_get_in_process_executor_cmd_args(
        self, inherited_args, additional_args, expected_result
    ):
        with mock.patch.object(common, "unreal") as mock_unreal:
            mock_settings = mock.MagicMock()
            mock_settings.inherited_command_line_arguments = inherited_args
            mock_settings.additional_command_line_arguments = additional_args
            mock_unreal.get_default_object.return_value = mock_settings

            result = common.get_in_process_executor_cmd_args()
            assert result == expected_result

    @pytest.mark.parametrize(
        "inherited_args,deadline_args,additional_args,expected_result",
        [
            # Explicit deadline args test cases
            (
                '-arg1 -arg2 -deadlineargs="-specific1 -specific2" -arg3',
                "-specific1 -specific2",
                "-add1 -add2",
                ["-specific1", "-specific2", "-add1", "-add2"],
            ),
            # Mixed case and spacing variations
            (
                '-arg1 -DeAdLiNeArGs="-option1=value -option2" -arg2',
                "-option1=value -option2",
                "-add1",
                ["-option1=value", "-option2", "-add1"],
            ),
            # Single quotes
            (
                "-arg1 -deadlineargs='-flag1 -flag2=test' -arg2",
                "-flag1 -flag2=test",
                "-add1 -add2=val",
                ["-flag1", "-flag2=test", "-add1", "-add2=val"],
            ),
            # Multiple flags and nested quotes
            (
                """-arg1 -deadlineargs="-a=1 -b=\"quoted value\" -c" -arg2""",
                """-a=1 -b="quoted value" -c""",
                "-add1",
                ["-a=1", '-b="quoted', 'value"', "-c", "-add1"],
            ),
            # Empty deadline args
            ('-arg1 -deadlineargs="" -arg2', "", "-add1", ["", "-add1"]),
        ],
    )
    def test_deadline_args_override(
        self, inherited_args, deadline_args, additional_args, expected_result
    ):
        with mock.patch.object(common, "unreal") as mock_unreal:
            mock_settings = mock.MagicMock()
            mock_settings.inherited_command_line_arguments = inherited_args
            mock_settings.additional_command_line_arguments = additional_args
            mock_unreal.get_default_object.return_value = mock_settings

            with mock.patch(
                "deadline.unreal_submitter.common.extract_deadline_args", return_value=deadline_args
            ):
                with mock.patch("deadline.unreal_submitter.common.logger.info") as mock_logger:
                    result = common.get_in_process_executor_cmd_args()
                    assert result == expected_result

                    mock_logger.assert_called_once_with(f"Found deadline args {deadline_args}")
