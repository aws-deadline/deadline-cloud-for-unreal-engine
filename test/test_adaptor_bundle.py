# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for adaptorBundle.py"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from adaptorBundle import (
    ADAPTOR_MODULES,
    BUNDLE_DEPENDENCIES,
    OPENJD_WRAPPER_CONTENT,
    P4_UTILS_WRAPPER_CONTENT,
    SUPPORTED_PYTHON_VERSIONS,
    _copy_adaptor_modules,
    _generate_wrapper_scripts,
    _cleanup_bundle,
    _get_dependency_specs,
    _install_dependencies,
    _split_native_and_pure_specs,
    build_adaptor_bundle,
)


@pytest.fixture
def bundle_dir(tmp_path):
    """Create a temporary bundle directory."""
    bd = tmp_path / "adaptor_bundle"
    bd.mkdir()
    return bd


@pytest.fixture
def fake_src(tmp_path):
    """Create a fake src/deadline/ directory with adaptor modules."""
    src_deadline = tmp_path / "src" / "deadline"
    src_deadline.mkdir(parents=True)

    # Create namespace __init__.py
    (src_deadline / "__init__.py").write_text("")

    # Create each adaptor module as a directory with __init__.py
    for module_name in ADAPTOR_MODULES:
        module_dir = src_deadline / module_name
        module_dir.mkdir()
        (module_dir / "__init__.py").write_text(f"# {module_name}")
        (module_dir / "main.py").write_text(f"# {module_name} main")

    # Also create a submitter module (should be excluded)
    submitter_dir = src_deadline / "unreal_submitter"
    submitter_dir.mkdir()
    (submitter_dir / "__init__.py").write_text("# submitter")

    return tmp_path


class TestGetDependencySpecs:
    """Tests for _get_dependency_specs()"""

    def test_extracts_pinned_deps_from_pyproject(self):
        """Verify that bundled deps are extracted with version pins from pyproject.toml."""
        pyproject_dict = {
            "project": {
                "dependencies": [
                    "deadline >= 0.51,< 0.54",
                    "openjd-adaptor-runtime >= 0.8.1,< 0.10",
                    "openjd-model >= 0.8.1, < 0.10",
                    "p4python == 2025.1.2767466",
                    "psutil >= 5.9.0",
                ]
            }
        }
        specs = _get_dependency_specs(pyproject_dict)

        # Should include openjd-adaptor-runtime and p4python (in BUNDLE_DEPENDENCIES)
        # Should NOT include deadline, openjd-model, psutil (in worker agent)
        spec_names = [
            s.split(">")[0].split("=")[0].split("<")[0].split("!")[0].lower() for s in specs
        ]
        assert "openjd-adaptor-runtime" in spec_names
        assert "p4python" in spec_names
        # jsonschema and pyyaml are not in pyproject.toml but are in BUNDLE_DEPENDENCIES
        assert "jsonschema" in spec_names
        assert "pyyaml" in spec_names

    def test_excludes_worker_agent_deps(self):
        """Verify that worker agent deps (deadline, psutil) are NOT included."""
        pyproject_dict = {
            "project": {
                "dependencies": [
                    "deadline >= 0.51,< 0.54",
                    "psutil >= 5.9.0",
                ]
            }
        }
        specs = _get_dependency_specs(pyproject_dict)
        spec_names = [s.split(">")[0].split("=")[0].split("<")[0].lower() for s in specs]
        assert "deadline" not in spec_names
        assert "psutil" not in spec_names

    def test_adds_missing_bundle_deps(self):
        """Verify deps in BUNDLE_DEPENDENCIES but not in pyproject.toml are still added."""
        pyproject_dict: dict[str, dict[str, list[str]]] = {"project": {"dependencies": []}}
        specs = _get_dependency_specs(pyproject_dict)
        spec_names = [s.lower() for s in specs]
        for dep in BUNDLE_DEPENDENCIES:
            assert dep.lower() in spec_names


class TestSplitNativeAndPureSpecs:
    """Tests for _split_native_and_pure_specs()"""

    def test_splits_native_from_pure(self):
        """Verify native deps are separated from pure-Python deps."""
        specs = [
            "openjd-adaptor-runtime>=0.8.1,<0.10",
            "p4python==2025.1.2767466",
            "jsonschema",
            "rpds-py",
            "pyyaml",
            "attrs",
        ]
        native_specs, pure_specs = _split_native_and_pure_specs(specs)

        # Native: rpds-py, p4python, pyyaml
        native_names = [s.split(">")[0].split("=")[0].split("<")[0].lower() for s in native_specs]
        assert "rpds-py" in native_names
        assert "p4python" in native_names
        assert "pyyaml" in native_names

        # Pure: openjd-adaptor-runtime, jsonschema, attrs
        pure_names = [s.split(">")[0].split("=")[0].split("<")[0].lower() for s in pure_specs]
        assert "openjd-adaptor-runtime" in pure_names
        assert "jsonschema" in pure_names
        assert "attrs" in pure_names

    def test_empty_specs(self):
        """Verify empty input returns empty lists."""
        native_specs, pure_specs = _split_native_and_pure_specs([])
        assert native_specs == []
        assert pure_specs == []

    def test_all_native(self):
        """Verify all-native input returns empty pure list."""
        specs = ["rpds-py", "p4python==1.0", "pyyaml>=6.0"]
        native_specs, pure_specs = _split_native_and_pure_specs(specs)
        assert len(native_specs) == 3
        assert len(pure_specs) == 0

    def test_all_pure(self):
        """Verify all-pure input returns empty native list."""
        specs = ["jsonschema", "attrs>=22.0", "referencing"]
        native_specs, pure_specs = _split_native_and_pure_specs(specs)
        assert len(native_specs) == 0
        assert len(pure_specs) == 3


class TestCopyAdaptorModules:
    """Tests for _copy_adaptor_modules()"""

    def test_copies_all_modules(self, fake_src, bundle_dir):
        """Verify all 4 adaptor modules are copied to the bundle."""
        import os

        # Run the actual function from the fake source tree
        original_cwd = os.getcwd()
        try:
            os.chdir(fake_src)
            _copy_adaptor_modules(bundle_dir)
        finally:
            os.chdir(original_cwd)

        dest_deadline = bundle_dir / "deadline"
        for module_name in ADAPTOR_MODULES:
            assert (dest_deadline / module_name).is_dir()
            assert (dest_deadline / module_name / "__init__.py").is_file()

    def test_excludes_submitter(self, fake_src, bundle_dir):
        """Verify submitter code is removed from the bundle."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(fake_src)
            _copy_adaptor_modules(bundle_dir)
        finally:
            os.chdir(original_cwd)

        assert not (bundle_dir / "deadline" / "unreal_submitter").exists()

    def test_does_not_create_namespace_init(self, fake_src, bundle_dir):
        """Verify deadline/__init__.py is NOT created (implicit namespace package)."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(fake_src)
            _copy_adaptor_modules(bundle_dir)
        finally:
            os.chdir(original_cwd)

        assert not (bundle_dir / "deadline" / "__init__.py").exists()

    def test_raises_on_missing_module(self, bundle_dir, tmp_path, monkeypatch):
        """Verify FileNotFoundError when a required adaptor module is missing."""
        src_deadline = tmp_path / "src" / "deadline"
        src_deadline.mkdir(parents=True)
        # Only create one module — the others are missing
        (src_deadline / "unreal_adaptor").mkdir()
        (src_deadline / "unreal_adaptor" / "__init__.py").write_text("")

        monkeypatch.chdir(tmp_path)
        with pytest.raises(FileNotFoundError):
            _copy_adaptor_modules(bundle_dir)


class TestGenerateWrapperScripts:
    """Tests for _generate_wrapper_scripts()"""

    def test_creates_bin_directory(self, bundle_dir):
        """Verify bin/ directory is created."""
        _generate_wrapper_scripts(bundle_dir)
        assert (bundle_dir / "bin").is_dir()

    def test_creates_openjd_wrapper(self, bundle_dir):
        """Verify unreal-engine-openjd.cmd wrapper is created with correct content."""
        _generate_wrapper_scripts(bundle_dir)
        wrapper = bundle_dir / "bin" / "unreal-engine-openjd.cmd"
        assert wrapper.is_file()
        assert wrapper.read_text() == OPENJD_WRAPPER_CONTENT

    def test_creates_p4_utils_wrapper(self, bundle_dir):
        """Verify unreal-engine-p4-utils.cmd wrapper is created with correct content."""
        _generate_wrapper_scripts(bundle_dir)
        wrapper = bundle_dir / "bin" / "unreal-engine-p4-utils.cmd"
        assert wrapper.is_file()
        assert wrapper.read_text() == P4_UTILS_WRAPPER_CONTENT

    def test_wrapper_invokes_python_m(self, bundle_dir):
        """Verify wrappers use 'python -m' to invoke the adaptor modules."""
        _generate_wrapper_scripts(bundle_dir)
        openjd = (bundle_dir / "bin" / "unreal-engine-openjd.cmd").read_text()
        p4 = (bundle_dir / "bin" / "unreal-engine-p4-utils.cmd").read_text()
        assert "python -m deadline.unreal_adaptor.UnrealAdaptor" in openjd
        assert "python -m deadline.unreal_perforce_utils.cli" in p4


class TestCleanupBundle:
    """Tests for _cleanup_bundle()"""

    def test_removes_dist_info(self, bundle_dir):
        """Verify .dist-info directories are removed."""
        dist_info = bundle_dir / "some_package-1.0.dist-info"
        dist_info.mkdir()
        (dist_info / "METADATA").write_text("test")

        _cleanup_bundle(bundle_dir)
        assert not dist_info.exists()

    def test_removes_pycache(self, bundle_dir):
        """Verify __pycache__ directories are removed."""
        pycache = bundle_dir / "some_module" / "__pycache__"
        pycache.mkdir(parents=True)
        (pycache / "module.cpython-311.pyc").write_text("test")

        _cleanup_bundle(bundle_dir)
        assert not pycache.exists()

    def test_preserves_wrapper_scripts(self, bundle_dir):
        """Verify our wrapper scripts in bin/ are preserved during cleanup."""
        _generate_wrapper_scripts(bundle_dir)
        # Add a pip-generated script that should be removed
        (bundle_dir / "bin" / "pip.exe").write_text("pip")

        _cleanup_bundle(bundle_dir)
        assert (bundle_dir / "bin" / "unreal-engine-openjd.cmd").is_file()
        assert (bundle_dir / "bin" / "unreal-engine-p4-utils.cmd").is_file()
        assert not (bundle_dir / "bin" / "pip.exe").exists()


class TestBuildAdaptorBundle:
    """Tests for build_adaptor_bundle() end-to-end with mocked subprocess."""

    @patch("adaptorBundle.subprocess.run")
    @patch("adaptorBundle._get_project_dict")
    def test_creates_bundle_directory(self, mock_project_dict, mock_run, tmp_path, monkeypatch):
        """Verify the bundle directory is created."""
        mock_project_dict.return_value = {
            "project": {
                "dependencies": [
                    "openjd-adaptor-runtime >= 0.8.1,< 0.10",
                    "p4python == 2025.1.2767466",
                ]
            }
        }
        mock_run.return_value = MagicMock(returncode=0)

        # Create fake source modules in tmp_path and chdir so relative Path("src") resolves there
        monkeypatch.chdir(tmp_path)
        src_deadline = tmp_path / "src" / "deadline"
        for module_name in ADAPTOR_MODULES:
            module_dir = src_deadline / module_name
            module_dir.mkdir(parents=True, exist_ok=True)
            (module_dir / "__init__.py").write_text(f"# {module_name}")

        output = str(tmp_path / "test_bundle")
        build_adaptor_bundle(output_dir=output)
        assert Path(output).is_dir()
        # Verify wrapper scripts exist
        assert (Path(output) / "bin" / "unreal-engine-openjd.cmd").is_file()
        assert (Path(output) / "bin" / "unreal-engine-p4-utils.cmd").is_file()
        # Verify adaptor modules copied
        for module_name in ADAPTOR_MODULES:
            assert (Path(output) / "deadline" / module_name).is_dir()

    @patch("adaptorBundle.subprocess.run")
    @patch("adaptorBundle._get_project_dict")
    def test_calls_pip_install(self, mock_project_dict, mock_run, tmp_path, monkeypatch):
        """Verify pip install is called with correct platform args."""
        mock_project_dict.return_value = {
            "project": {
                "dependencies": [
                    "openjd-adaptor-runtime >= 0.8.1,< 0.10",
                    "p4python == 2025.1.2767466",
                ]
            }
        }
        mock_run.return_value = MagicMock(returncode=0)

        monkeypatch.chdir(tmp_path)
        src_deadline = tmp_path / "src" / "deadline"
        for module_name in ADAPTOR_MODULES:
            module_dir = src_deadline / module_name
            module_dir.mkdir(parents=True, exist_ok=True)
            (module_dir / "__init__.py").write_text(f"# {module_name}")

        output = str(tmp_path / "test_bundle")
        build_adaptor_bundle(output_dir=output, python_version="3.11", platform="win_amd64")

        # Verify pip was called with platform-specific args
        pip_calls = [c for c in mock_run.call_args_list if "pip" in str(c)]
        assert len(pip_calls) > 0
        pip_call_str = str(pip_calls[0])
        assert "--platform" in pip_call_str
        assert "win_amd64" in pip_call_str
        assert "--python-version" in pip_call_str
        assert "3.11" in pip_call_str

    @patch("adaptorBundle.subprocess.run")
    @patch("adaptorBundle._get_project_dict")
    def test_native_deps_installed_for_all_python_versions(
        self, mock_project_dict, mock_run, tmp_path, monkeypatch
    ):
        """Verify native deps are downloaded for each supported Python version."""
        mock_project_dict.return_value = {
            "project": {
                "dependencies": [
                    "openjd-adaptor-runtime >= 0.8.1,< 0.10",
                    "p4python == 2025.1.2767466",
                    "rpds-py",
                ]
            }
        }
        mock_run.return_value = MagicMock(returncode=0)

        monkeypatch.chdir(tmp_path)
        src_deadline = tmp_path / "src" / "deadline"
        for module_name in ADAPTOR_MODULES:
            module_dir = src_deadline / module_name
            module_dir.mkdir(parents=True, exist_ok=True)
            (module_dir / "__init__.py").write_text(f"# {module_name}")

        output = str(tmp_path / "test_bundle")
        build_adaptor_bundle(output_dir=output, python_version="3.11", platform="win_amd64")

        # Collect all pip install calls
        pip_calls = [c for c in mock_run.call_args_list if "pip" in str(c)]

        # There should be at least 1 call for pure deps + len(SUPPORTED_PYTHON_VERSIONS) for native
        # Pure deps call uses --python-version 3.11
        # Native deps calls use each version in SUPPORTED_PYTHON_VERSIONS
        pip_call_strs = [str(c) for c in pip_calls]

        # Verify native deps are installed for each supported version
        for ver in SUPPORTED_PYTHON_VERSIONS:
            version_calls = [s for s in pip_call_strs if f"'{ver}'" in s or f'"{ver}"' in s]
            assert (
                len(version_calls) >= 1
            ), f"Expected pip call for Python {ver}, got none. Calls: {pip_call_strs}"


class TestInstallDependenciesMultiVersion:
    """Tests that verify native extensions for multiple Python versions end up in the bundle.

    These tests simulate pip's output by creating fake .pyd files in temp directories,
    verifying the file-merging logic that prevents 'No module named rpds.rpds' on workers
    running a different Python version than the build machine.
    """

    def _fake_pip_side_effect(self, tmp_path):
        """
        Returns a side_effect function for subprocess.run that simulates pip creating
        version-specific .pyd files in the --target directory.
        """

        def side_effect(cmd, **kwargs):
            # Find --target argument
            if "pip" not in cmd[0] and "pip" not in str(cmd):
                return MagicMock(returncode=0)
            try:
                target_idx = cmd.index("--target") + 1
                target_dir = Path(cmd[target_idx])
            except (ValueError, IndexError):
                return MagicMock(returncode=0)

            # Find --python-version argument
            try:
                ver_idx = cmd.index("--python-version") + 1
                python_ver = cmd[ver_idx]
            except (ValueError, IndexError):
                python_ver = "3.11"

            # Simulate pip output for rpds-py: creates rpds/__init__.py + rpds.cpXY-win_amd64.pyd
            ver_tag = python_ver.replace(".", "")
            rpds_dir = target_dir / "rpds"
            rpds_dir.mkdir(parents=True, exist_ok=True)
            # __init__.py is the same across versions
            init_file = rpds_dir / "__init__.py"
            if not init_file.exists():
                init_file.write_text("from .rpds import *\n")
            # .pyd is version-specific
            pyd_file = rpds_dir / f"rpds.cp{ver_tag}-win_amd64.pyd"
            pyd_file.write_text(f"fake native extension for cp{ver_tag}")

            return MagicMock(returncode=0)

        return side_effect

    @patch("adaptorBundle.subprocess.run")
    def test_bundle_contains_pyd_for_all_python_versions(self, mock_run, tmp_path):
        """
        Verify that after _install_dependencies, the bundle contains .pyd files
        for each supported Python version — not just the build machine's version.

        This is the regression test for the 'No module named rpds.rpds' bug.
        """
        mock_run.side_effect = self._fake_pip_side_effect(tmp_path)

        bundle_dir = tmp_path / "bundle"
        bundle_dir.mkdir()

        _install_dependencies(
            bundle_dir=bundle_dir,
            dependency_specs=["rpds-py"],
            python_version="3.11",
            platform="win_amd64",
        )

        rpds_dir = bundle_dir / "rpds"
        assert rpds_dir.is_dir(), "rpds/ directory should exist in bundle"

        # Verify .pyd files exist for ALL supported versions
        for ver in SUPPORTED_PYTHON_VERSIONS:
            ver_tag = ver.replace(".", "")
            pyd_file = rpds_dir / f"rpds.cp{ver_tag}-win_amd64.pyd"
            assert pyd_file.is_file(), (
                f"Missing rpds.cp{ver_tag}-win_amd64.pyd — worker running Python {ver} "
                f"would get 'No module named rpds.rpds'"
            )

    @patch("adaptorBundle.subprocess.run")
    def test_pure_deps_not_duplicated_across_versions(self, mock_run, tmp_path):
        """
        Verify that pure-Python deps are installed only once (not per-version).
        """
        call_count = {"pure": 0, "native": 0}

        def side_effect(cmd, **kwargs):
            if "pip" in cmd[0] or (isinstance(cmd, list) and cmd[0] == "pip"):
                specs = [c for c in cmd if "jsonschema" in c or "attrs" in c]
                if specs:
                    call_count["pure"] += 1
            return MagicMock(returncode=0)

        mock_run.side_effect = side_effect

        bundle_dir = tmp_path / "bundle"
        bundle_dir.mkdir()

        _install_dependencies(
            bundle_dir=bundle_dir,
            dependency_specs=["jsonschema", "attrs", "rpds-py"],
            python_version="3.11",
            platform="win_amd64",
        )

        # Pure deps should be installed exactly once
        assert (
            call_count["pure"] == 1
        ), f"Pure deps should be installed once, but pip was called {call_count['pure']} times"
