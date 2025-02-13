#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
from unittest.mock import MagicMock


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
