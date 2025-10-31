# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import sys

from unittest.mock import patch

# Allow init_unreal import
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "../../../src/unreal_plugin/Content/Python")
)


class TestPython397Patch:
    """Test the Python 3.9.7 pydantic StringConstraints compatibility patch."""

    @patch("init_unreal.sys.version_info", (3, 10, 0))
    def test_patch_skipped_on_other_python_versions(self, capsys):
        """Test that the patch is skipped on Python versions other than 3.9.7."""
        from init_unreal import _check_patch_pydantic_py397

        _check_patch_pydantic_py397()

        captured = capsys.readouterr()
        assert "Skipping Python 3.9.7 patch: Python version is (3, 10, 0)" in captured.out

    @patch("init_unreal.sys.version_info", (3, 9, 7))
    def test_patch_applied_when_all_checks_pass(self, capsys):
        """Test that the patch is applied when all checks pass."""

        from init_unreal import _check_patch_pydantic_py397

        _check_patch_pydantic_py397()

        captured = capsys.readouterr()
        assert "Applied Python 3.9.7 compatibility fix" in captured.out
