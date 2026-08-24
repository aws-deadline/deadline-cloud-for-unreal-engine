# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import hashlib
import importlib.util
from pathlib import Path

import pytest

SETUP_RUNNER_PATH = Path(__file__).parents[1] / "pipeline" / "setup-runner.py"
SPEC = importlib.util.spec_from_file_location("unreal_setup_runner", SETUP_RUNNER_PATH)
assert SPEC and SPEC.loader
setup_runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup_runner)


def test_supported_installers_are_immutable_ci_artifacts():
    assert set(setup_runner.UE_INSTALLERS) == {"5.6", "5.7", "5.8"}

    for version, platforms in setup_runner.UE_INSTALLERS.items():
        installer = platforms["windows"]
        assert installer["s3_key"].startswith(f"unrealengine/ci-source-artifacts/v1/{version}/")
        assert len(installer["sha256"]) == 64
        assert installer["size"] > 0
        assert installer["archive_root"] == f"UE_{version}"


def test_install_marker_requires_exact_artifact(tmp_path):
    version = "5.7"
    installer = setup_runner.UE_INSTALLERS[version]["windows"]
    editor = tmp_path / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe"
    editor.parent.mkdir(parents=True)
    editor.touch()

    assert not setup_runner.install_is_current(tmp_path, version, installer)

    setup_runner.write_install_marker(tmp_path, version, installer)
    assert setup_runner.install_is_current(tmp_path, version, installer)
    assert setup_runner.install_is_ci_managed(tmp_path)

    changed_installer = {**installer, "sha256": "0" * 64}
    assert not setup_runner.install_is_current(tmp_path, version, changed_installer)


def test_cleanup_stale_version_artifacts_preserves_current_and_other_versions(tmp_path):
    download_dir = tmp_path / "downloads"
    staging_root = tmp_path / "staging"
    download_dir.mkdir()
    staging_root.mkdir()

    current_installer = download_dir / "UE_5.7_current.zip"
    stale_installer = download_dir / "UE_5.7_old.zip"
    other_installer = download_dir / "UE_5.8_old.zip"
    current_staging = staging_root / "UE_5.7_current"
    stale_staging = staging_root / "UE_5.7_old"
    other_staging = staging_root / "UE_5.8_old"
    for path in (current_installer, stale_installer, other_installer):
        path.touch()
    for path in (current_staging, stale_staging, other_staging):
        path.mkdir()

    setup_runner.cleanup_stale_version_artifacts("5.7", current_installer, current_staging)

    assert current_installer.exists()
    assert current_staging.exists()
    assert not stale_installer.exists()
    assert not stale_staging.exists()
    assert other_installer.exists()
    assert other_staging.exists()


def test_replace_ci_managed_install_refuses_unmanaged_directory(tmp_path):
    install_dir = tmp_path / "UE_5.7"
    staged_install = tmp_path / "staging" / "UE_5.7"
    install_dir.mkdir()
    staged_install.mkdir(parents=True)
    unmanaged_file = install_dir / "custom-plugin.txt"
    staged_file = staged_install / "engine.txt"
    unmanaged_file.touch()
    staged_file.touch()

    with pytest.raises(RuntimeError, match="unmanaged Unreal Engine install"):
        setup_runner.replace_ci_managed_install(staged_install, install_dir)

    assert unmanaged_file.exists()
    assert staged_file.exists()

    (install_dir / setup_runner.LEGACY_INSTALL_MARKER_FILENAME).touch()
    setup_runner.replace_ci_managed_install(staged_install, install_dir)

    assert not unmanaged_file.exists()
    assert (install_dir / "engine.txt").exists()


def test_verify_artifact_checks_size_and_sha256(tmp_path):
    artifact = tmp_path / "engine.zip"
    content = b"test artifact"
    artifact.write_bytes(content)
    checksum = hashlib.sha256(content).hexdigest()

    setup_runner.verify_artifact(artifact, checksum, len(content))

    with pytest.raises(RuntimeError, match="size mismatch"):
        setup_runner.verify_artifact(artifact, checksum, len(content) + 1)

    with pytest.raises(RuntimeError, match="SHA256 mismatch"):
        setup_runner.verify_artifact(artifact, "0" * 64, len(content))


def test_configure_unreal_build_tool_disables_uba(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    setup_runner.configure_unreal_build_tool()

    config = (tmp_path / "Unreal Engine" / "UnrealBuildTool" / "BuildConfiguration.xml").read_text(
        encoding="utf-8"
    )
    assert "<bAllowUBAExecutor>false</bAllowUBAExecutor>" in config
