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
    _copy_adaptor_modules,
    _generate_wrapper_scripts,
    _cleanup_bundle,
    _get_dependency_specs,
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

    def test_raises_on_missing_module(self, bundle_dir, tmp_path):
        """Verify FileNotFoundError when a module is missing."""
        src_deadline = tmp_path / "src" / "deadline"
        src_deadline.mkdir(parents=True)
        # Only create one module, not all four
        (src_deadline / "unreal_adaptor").mkdir()
        (src_deadline / "unreal_adaptor" / "__init__.py").write_text("")

        with patch("adaptorBundle.Path") as mock_path:
            mock_path.return_value = tmp_path / "src" / "deadline"
            # The function should raise when it can't find a module
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
    def test_calls_pip_install(self, mock_project_dict, mock_run, tmp_path):
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
