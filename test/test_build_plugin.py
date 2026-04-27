# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from unittest.mock import patch, MagicMock

from scripts.build_plugin import (
    build_and_install,
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
    def test_pip_install_uses_eager_upgrade_strategy(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        install_whl_global(FAKE_WHL_PATH)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert FAKE_WHL_PATH in cmd
        assert "--upgrade" in cmd
        assert "--upgrade-strategy" in cmd
        assert cmd[cmd.index("--upgrade-strategy") + 1] == "eager"


class TestInstallWorkerDependencies:
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


class TestBuildAndInstall:
    @patch("scripts.build_plugin.install_whl_global")
    @patch("scripts.build_plugin.install_plugin")
    @patch("scripts.build_plugin.build_whl", return_value=FAKE_WHL_PATH)
    @patch("scripts.build_plugin.build_plugin")
    @patch("scripts.build_plugin.find_runuat", return_value="/fake/runuat")
    @patch("scripts.build_plugin.check_configuration_warnings")
    @patch("scripts.build_plugin.find_engine_root", return_value=FAKE_ENGINE_ROOT)
    def test_install_flag_also_updates_global_python(
        self,
        mock_find_engine,
        mock_check_warnings,
        mock_find_runuat,
        mock_build_plugin,
        mock_build_whl,
        mock_install_plugin,
        mock_install_whl_global,
    ):
        build_and_install(install=True)

        mock_install_plugin.assert_called_once()
        mock_install_whl_global.assert_called_once_with(FAKE_WHL_PATH)
