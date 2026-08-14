# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from unittest.mock import patch, MagicMock

import pytest

from scripts.build_plugin import (
    build_and_install,
    get_pywin32_requirement,
    install_whl_to_plugin,
    install_whl_global,
    install_worker_dependencies,
)

import os

FAKE_ENGINE_ROOT = "/fake/engine"
FAKE_PYTHON_PATH = os.path.join(
    FAKE_ENGINE_ROOT, "Engine", "Binaries", "ThirdParty", "Python3", "Win64", "python.exe"
)
FAKE_WHL_PATH = "/fake/path/package.whl"
FAKE_PLUGIN_LIBRARIES = os.path.join(
    FAKE_ENGINE_ROOT,
    "Engine",
    "Plugins",
    "UnrealDeadlineCloudService",
    "Content",
    "Python",
    "libraries",
)


class TestInstallWhlToPlugin:
    @patch("scripts.build_plugin.subprocess.run")
    @patch("scripts.build_plugin.os.path.exists", return_value=True)
    def test_pip_install_uses_force_reinstall(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        install_whl_to_plugin(FAKE_WHL_PATH, FAKE_ENGINE_ROOT)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == FAKE_PYTHON_PATH
        assert "--force-reinstall" in cmd
        assert "-t" in cmd
        assert cmd[cmd.index("-t") + 1] == FAKE_PLUGIN_LIBRARIES


class TestInstallWhlGlobal:
    @patch("scripts.build_plugin.subprocess.run")
    @patch("scripts.build_plugin.os.path.exists", return_value=True)
    def test_pip_install_two_pass_deps_then_force_reinstall(self, mock_exists, mock_run):
        """
        install_whl_global runs two `pip install` passes: (1) plain install so
        dependencies get resolved, (2) --force-reinstall --no-deps so
        iterative dev builds overwrite files even when the version string is
        unchanged.
        """
        mock_run.return_value = MagicMock(returncode=0)

        install_whl_global(FAKE_WHL_PATH)

        assert mock_run.call_count == 2
        first_cmd = mock_run.call_args_list[0][0][0]
        second_cmd = mock_run.call_args_list[1][0][0]

        # Pass 1: plain install — resolves deps.
        assert FAKE_WHL_PATH in first_cmd
        assert "install" in first_cmd
        assert "--force-reinstall" not in first_cmd
        assert "--no-deps" not in first_cmd

        # Pass 2: --force-reinstall --no-deps overwrites the package itself.
        assert FAKE_WHL_PATH in second_cmd
        assert "--force-reinstall" in second_cmd
        assert "--no-deps" in second_cmd


class TestInstallWorkerDependencies:
    @patch("scripts.build_plugin.Path.read_text", side_effect=OSError("not found"))
    def test_missing_pywin32_version_has_clear_error(self, mock_read_text):
        with pytest.raises(RuntimeError, match="Unable to read pywin32 version"):
            get_pywin32_requirement()

    @patch("scripts.build_plugin.Path.read_text", return_value="")
    def test_empty_pywin32_version_has_clear_error(self, mock_read_text):
        with pytest.raises(RuntimeError, match="Invalid pywin32 version"):
            get_pywin32_requirement()

    @patch("scripts.build_plugin.subprocess.run")
    @patch("scripts.build_plugin.os.path.exists", return_value=True)
    def test_worker_agent_install_uses_eager_upgrade_strategy(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        install_worker_dependencies(FAKE_ENGINE_ROOT)

        # Last call should be the deadline-cloud-worker-agent install
        worker_agent_call = mock_run.call_args_list[-1]
        cmd = worker_agent_call[0][0]
        assert "deadline-cloud-worker-agent" in cmd
        assert "--upgrade" in cmd
        assert "--upgrade-strategy" in cmd
        assert cmd[cmd.index("--upgrade-strategy") + 1] == "eager"

    @patch("scripts.build_plugin.subprocess.run")
    @patch("scripts.build_plugin.os.path.exists", return_value=True)
    def test_pywin32_install_is_pinned_to_a_binary_wheel(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        install_worker_dependencies(FAKE_ENGINE_ROOT)

        cmd = mock_run.call_args_list[0][0][0]
        assert "pywin32==310" in cmd
        assert "--only-binary=:all:" in cmd


class TestBuildAndInstall:
    @patch("scripts.build_plugin.install_worker_dependencies")
    @patch("scripts.build_plugin.install_whl_global")
    @patch("scripts.build_plugin.install_plugin")
    @patch("scripts.build_plugin.build_whl", return_value=FAKE_WHL_PATH)
    @patch("scripts.build_plugin.build_plugin")
    @patch("scripts.build_plugin.find_runuat", return_value="/fake/runuat")
    @patch("scripts.build_plugin.check_configuration_warnings")
    @patch("scripts.build_plugin.find_engine_root", return_value=FAKE_ENGINE_ROOT)
    def test_install_flag_does_not_touch_global_python(
        self,
        mock_find_engine,
        mock_check_warnings,
        mock_find_runuat,
        mock_build_plugin,
        mock_build_whl,
        mock_install_plugin,
        mock_install_whl_global,
        mock_install_worker_dependencies,
    ):
        build_and_install(install=True)

        mock_install_plugin.assert_called_once()
        mock_install_whl_global.assert_not_called()
        mock_install_worker_dependencies.assert_not_called()

    @patch("scripts.build_plugin.install_worker_dependencies")
    @patch("scripts.build_plugin.install_whl_global")
    @patch("scripts.build_plugin.install_plugin")
    @patch("scripts.build_plugin.build_whl", return_value=FAKE_WHL_PATH)
    @patch("scripts.build_plugin.build_plugin")
    @patch("scripts.build_plugin.find_runuat", return_value="/fake/runuat")
    @patch("scripts.build_plugin.check_configuration_warnings")
    @patch("scripts.build_plugin.find_engine_root", return_value=FAKE_ENGINE_ROOT)
    def test_worker_flag_updates_global_python(
        self,
        mock_find_engine,
        mock_check_warnings,
        mock_find_runuat,
        mock_build_plugin,
        mock_build_whl,
        mock_install_plugin,
        mock_install_whl_global,
        mock_install_worker_dependencies,
    ):
        build_and_install(install=True, worker=True)

        mock_install_plugin.assert_called_once()
        mock_install_whl_global.assert_called_once_with(FAKE_WHL_PATH)
        mock_install_worker_dependencies.assert_called_once_with(FAKE_ENGINE_ROOT)
