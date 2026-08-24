#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Setup runner for Unreal Engine tests in CodeBuild.

Installs supported Unreal Engine versions on Windows from immutable zip
artifacts in S3, along with the build dependencies required by the plugin.

Follows the same pattern as deadline-cloud-for-cinema-4d and
deadline-cloud-for-maya setup runners.

Environment variables required:
    INSTALLER_BUCKET - S3 bucket containing the UE installer zip
    INSTALLER_BUCKET_EXPECTED_OWNER - 12-digit AWS account ID (for verification)
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import boto3
from botocore.config import Config

UE_INSTALLERS = {
    "5.6": {
        "windows": {
            "s3_key": "unrealengine/ci-source-artifacts/v1/5.6/UnrealEngine_5.6_Win.zip",
            "sha256": "9e5c184d4d929498d97d5d5703747c0e295e573cca884928d04e4d45cfceb5c2",
            "size": 11230461116,
            "archive_root": "UE_5.6",
            "type": "zip",
        },
    },
    "5.7": {
        "windows": {
            "s3_key": "unrealengine/ci-source-artifacts/v1/5.7/UnrealEngine_5.7_Win.zip",
            "sha256": "0a87923ed5bc9915c0225333c7644de379e8a118fef9f240b5e31f7fe814f640",
            "size": 12209071317,
            "archive_root": "UE_5.7",
            "type": "zip",
        },
    },
    "5.8": {
        "windows": {
            "s3_key": "unrealengine/ci-source-artifacts/v1/5.8/UnrealEngine_5.8_Win.zip",
            "sha256": "4402b37df38fdb0d5df7c10a6de8bf212aa56ca82f9a4dded61132d49852f5c8",
            "size": 13425863018,
            "archive_root": "UE_5.8",
            "type": "zip",
        },
    },
}

UE_INSTALL_PATHS = {
    "5.6": {
        "windows": Path("C:/Program Files/Epic Games/UE_5.6"),
    },
    "5.7": {
        "windows": Path("C:/Program Files/Epic Games/UE_5.7"),
    },
    "5.8": {
        "windows": Path("C:/Program Files/Epic Games/UE_5.8"),
    },
}

INSTALL_MARKER_FILENAME = ".deadline-cloud-ci-install.json"
LEGACY_INSTALL_MARKER_FILENAME = ".installed"


def run(cmd, check=True):
    """Run a shell command, exiting on failure if check is True."""
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(cmd, shell=isinstance(cmd, str))
    if check and result.returncode != 0:
        sys.exit(result.returncode)
    return result


def download_from_s3(s3_path, local_path):
    """Download a file from S3 with optional expected bucket owner verification."""
    bucket = os.environ.get("INSTALLER_BUCKET")
    if not bucket:
        print("ERROR: INSTALLER_BUCKET not set")
        sys.exit(1)

    expected_bucket_owner = os.environ.get("INSTALLER_BUCKET_EXPECTED_OWNER")
    if expected_bucket_owner and not (
        expected_bucket_owner.isdigit() and len(expected_bucket_owner) == 12
    ):
        raise ValueError("INSTALLER_BUCKET_EXPECTED_OWNER must be a 12-digit AWS Account ID")

    config = Config(read_timeout=300, connect_timeout=60, retries={"max_attempts": 2})
    s3 = boto3.client("s3", config=config)

    extra_args = {}
    if expected_bucket_owner:
        extra_args["ExpectedBucketOwner"] = expected_bucket_owner

    print(f"Downloading s3://{bucket}/{s3_path} to {local_path}")
    s3.download_file(bucket, s3_path, str(local_path), ExtraArgs=extra_args)


def verify_artifact(file_path, expected_checksum, expected_size):
    """Verify the downloaded artifact's size and SHA256 checksum."""
    actual_size = file_path.stat().st_size
    if actual_size != expected_size:
        raise RuntimeError(
            f"Artifact size mismatch for {file_path}: "
            f"expected {expected_size}, got {actual_size}"
        )

    print(f"Verifying checksum for {file_path}...")
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()
    if actual != expected_checksum:
        raise RuntimeError(
            f"SHA256 mismatch for {file_path}: expected {expected_checksum}, got {actual}"
        )
    print("OK Checksum verified")


def expected_install_marker(version, installer_info):
    """Return the marker content that identifies an exact engine artifact."""
    return {
        "version": version,
        "s3_key": installer_info["s3_key"],
        "sha256": installer_info["sha256"],
        "size": installer_info["size"],
    }


def install_is_current(install_dir, version, installer_info):
    """Return whether install_dir contains the exact configured engine artifact."""
    editor_exe = install_dir / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe"
    marker_path = install_dir / INSTALL_MARKER_FILENAME
    if not editor_exe.exists() or not marker_path.exists():
        return False

    try:
        actual_marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    return actual_marker == expected_install_marker(version, installer_info)


def write_install_marker(install_dir, version, installer_info):
    """Record the immutable artifact used to populate install_dir."""
    marker_path = install_dir / INSTALL_MARKER_FILENAME
    marker_path.write_text(
        json.dumps(expected_install_marker(version, installer_info), indent=2) + "\n",
        encoding="utf-8",
    )


def install_is_ci_managed(install_dir):
    """Return whether an install was created by this setup runner."""
    return any(
        (install_dir / marker).exists()
        for marker in (INSTALL_MARKER_FILENAME, LEGACY_INSTALL_MARKER_FILENAME)
    )


def remove_readonly(func, path, exc_info):
    """Clear a Windows read-only attribute and retry a failed removal."""
    if not isinstance(exc_info[1], PermissionError) or func not in (os.unlink, os.rmdir):
        raise exc_info[1]
    os.chmod(path, stat.S_IWRITE)
    func(path)


def cleanup_stale_version_artifacts(version, local_installer, staging_dir):
    """Remove temporary files left by previous artifacts for one engine version."""
    stale_paths = [
        *local_installer.parent.glob(f"UE_{version}_*.zip"),
        *staging_dir.parent.glob(f"UE_{version}_*"),
    ]
    for stale_path in stale_paths:
        if stale_path in (local_installer, staging_dir):
            continue
        print(f"Removing stale UE {version} setup artifact: {stale_path}")
        if stale_path.is_dir():
            shutil.rmtree(stale_path, onerror=remove_readonly)
        else:
            stale_path.unlink(missing_ok=True)


def replace_ci_managed_install(staged_install_dir, install_dir):
    """Move a staged engine into place without deleting an unmanaged installation."""
    install_dir.parent.mkdir(parents=True, exist_ok=True)
    if install_dir.exists():
        is_configured_codebuild_install = bool(os.environ.get("CODEBUILD_BUILD_ID")) and (
            install_dir in {paths["windows"] for paths in UE_INSTALL_PATHS.values()}
        )
        if not install_is_ci_managed(install_dir) and not is_configured_codebuild_install:
            raise RuntimeError(
                f"Refusing to replace unmanaged Unreal Engine install at {install_dir}. "
                "Move or remove it before running CI setup."
            )
        print(f"Replacing incomplete or outdated UE install at {install_dir}")
        shutil.rmtree(install_dir, onerror=remove_readonly)
    shutil.move(str(staged_install_dir), str(install_dir))


def install_engine_artifact(version, install_dir, installer_info):
    """Download, verify, stage, and install one Unreal Engine artifact."""
    local_installer = Path(f"C:/Temp/UnrealCI/UE_{version}_{installer_info['sha256'][:12]}.zip")
    staging_dir = Path(f"C:/UnrealCI/engine-staging/UE_{version}_{installer_info['sha256'][:12]}")
    local_installer.parent.mkdir(parents=True, exist_ok=True)
    staging_dir.parent.mkdir(parents=True, exist_ok=True)
    cleanup_stale_version_artifacts(version, local_installer, staging_dir)

    if staging_dir.exists():
        shutil.rmtree(staging_dir, onerror=remove_readonly)

    try:
        download_from_s3(installer_info["s3_key"], local_installer)
        verify_artifact(local_installer, installer_info["sha256"], installer_info["size"])

        staging_dir.mkdir()
        print(f"Extracting to {staging_dir} (this may take 10-15 minutes)...")
        extract_zip(local_installer, staging_dir)
        local_installer.unlink(missing_ok=True)

        staged_install_dir = staging_dir / installer_info["archive_root"]
        staged_editor = (
            staged_install_dir / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe"
        )
        if not staged_editor.exists():
            contents = [item.name for item in sorted(staging_dir.iterdir())[:10]]
            raise RuntimeError(
                f"UnrealEditor-Cmd.exe not found at {staged_editor}. "
                f"Staging contents: {contents}"
            )

        write_install_marker(staged_install_dir, version, installer_info)
        replace_ci_managed_install(staged_install_dir, install_dir)
    finally:
        local_installer.unlink(missing_ok=True)
        shutil.rmtree(staging_dir, ignore_errors=True)


def ensure_7zip():
    """Ensure 7-Zip is installed from the installer bucket, install if missing."""
    seven_zip = Path("C:/Program Files/7-Zip/7z.exe")
    if seven_zip.exists():
        return str(seven_zip)

    print("Installing 7-Zip from installer bucket...")
    installer_path = Path("C:/Temp/7z-install.exe")
    installer_path.parent.mkdir(parents=True, exist_ok=True)
    download_from_s3("tools/7z2408-x64.exe", installer_path)
    run(
        [
            "powershell",
            "-Command",
            f"Start-Process '{installer_path}' -ArgumentList '/S' -Wait",
        ]
    )

    if not seven_zip.exists():
        print("ERROR: 7-Zip installation failed")
        sys.exit(1)

    return str(seven_zip)


def ensure_vs_buildtools():
    """Ensure Visual Studio Build Tools 2022 with required components are installed.

    Components installed:
    - VCTools workload (C++ build tools)
    - MSVC x64/x86 build tools (latest, includes v14.44+)
    - Windows 11 SDK
    - .NET Framework 4.6.1 Targeting Pack
    - .NET Framework 4.8.1 SDK
    - .NET development prerequisites
    """
    build_tools_root = Path("C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools")
    msvc_path = build_tools_root / "VC" / "Tools" / "MSVC"
    msbuild_path = build_tools_root / "MSBuild" / "Current" / "Bin" / "MSBuild.exe"
    kits_bin = Path("C:/Program Files (x86)/Windows Kits/10/bin")
    netfx_path = Path("C:/Program Files (x86)/Windows Kits/NETFXSDK")

    def required_components_exist():
        sdk_tool_dirs = kits_bin.glob("*/x64") if kits_bin.exists() else []
        has_windows_sdk = any(
            (tool_dir / "rc.exe").exists() and (tool_dir / "signtool.exe").exists()
            for tool_dir in sdk_tool_dirs
        )
        return (
            msvc_path.exists()
            and any(msvc_path.iterdir())
            and msbuild_path.exists()
            and has_windows_sdk
            and netfx_path.exists()
            and any(netfx_path.iterdir())
        )

    if required_components_exist():
        print("VS Build Tools already installed with all required components")
        return

    print("Installing Visual Studio Build Tools 2022...")
    installer_path = Path("C:/Temp/vs_buildtools.exe")
    installer_path.parent.mkdir(parents=True, exist_ok=True)

    run(
        [
            "powershell",
            "-Command",
            "Invoke-WebRequest -Uri 'https://aka.ms/vs/17/release/vs_buildtools.exe'"
            f" -OutFile '{installer_path}' -UseBasicParsing",
        ]
    )

    run(
        [
            "powershell",
            "-Command",
            f"Start-Process '{installer_path}' -ArgumentList "
            "'--quiet','--wait','--norestart',"
            "'--add','Microsoft.VisualStudio.Workload.VCTools',"
            "'--add','Microsoft.VisualStudio.Component.VC.Tools.x86.x64',"
            "'--add','Microsoft.VisualStudio.Component.Windows11SDK.22621',"
            "'--add','Microsoft.Net.Component.4.6.1.TargetingPack',"
            "'--add','Microsoft.Net.Component.4.8.1.SDK',"
            "'--add','Microsoft.Net.ComponentGroup.DevelopmentPrerequisites'"
            " -Wait",
        ]
    )

    if not required_components_exist():
        raise RuntimeError("VS Build Tools installation did not provide all required components")

    print("VS Build Tools installed successfully")


def configure_unreal_build_tool():
    """Disable Unreal Build Accelerator for deterministic headless CI builds."""
    app_data = os.environ.get("APPDATA")
    if not app_data:
        raise RuntimeError("APPDATA is required to configure UnrealBuildTool")

    config_path = Path(app_data) / "Unreal Engine" / "UnrealBuildTool" / "BuildConfiguration.xml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<Configuration xmlns="https://www.unrealengine.com/BuildConfiguration">
  <BuildConfiguration>
    <bAllowUBAExecutor>false</bAllowUBAExecutor>
  </BuildConfiguration>
</Configuration>
""",
        encoding="utf-8",
    )
    print(f"Disabled Unreal Build Accelerator in {config_path}")


def extract_zip(zip_path, dest_dir):
    """Extract a zip archive using 7-Zip (faster and lower memory than Python zipfile)."""
    seven_zip = ensure_7zip()
    print(f"Extracting {zip_path} to {dest_dir}...")
    run([seven_zip, "x", str(zip_path), f"-o{dest_dir}", "-y"])


def get_pywin32_requirement():
    """Read the shared pywin32 pin when the Windows dependency is needed."""
    version_file = Path(__file__).resolve().parents[1] / "scripts" / "ci" / "pywin32-version.txt"
    try:
        version = version_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Unable to read pywin32 version from {version_file}: {exc}") from exc
    if not version.isdigit():
        raise RuntimeError(f"Invalid pywin32 version in {version_file}: {version!r}")
    return version, f"pywin32=={version}"


def ensure_ue_python_dependencies(install_dir):
    """Install Windows modules required by the adaptor inside UE's Python."""
    pywin32_version, pywin32_requirement = get_pywin32_requirement()
    python_exe = (
        install_dir / "Engine" / "Binaries" / "ThirdParty" / "Python3" / "Win64" / "python.exe"
    )
    if not python_exe.exists():
        print(f"ERROR: Unreal Python not found at {python_exe}")
        sys.exit(1)

    result = subprocess.run(
        [
            str(python_exe),
            "-c",
            (
                "import importlib.metadata; import win32file; "
                f"assert importlib.metadata.version('pywin32') == '{pywin32_version}'"
            ),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"UE Python dependency {pywin32_requirement} is already installed")
        return

    print(f"Installing {pywin32_requirement} into UE Python...")
    run(
        [
            str(python_exe),
            "-m",
            "pip",
            "install",
            "--only-binary=:all:",
            pywin32_requirement,
        ]
    )
    run(
        [
            str(python_exe),
            "-c",
            (
                "import importlib.metadata; import win32file; "
                f"assert importlib.metadata.version('pywin32') == '{pywin32_version}'"
            ),
        ]
    )


def setup_windows(versions):
    """Install Unreal Engine and build dependencies on Windows."""
    # Install build tools first (needed for plugin compilation)
    ensure_vs_buildtools()
    configure_unreal_build_tool()

    for version in versions:
        install_dir = UE_INSTALL_PATHS[version]["windows"]
        installer_info = UE_INSTALLERS[version]["windows"]

        if install_is_current(install_dir, version, installer_info):
            print(f"UE {version} already installed at {install_dir}")
            ensure_ue_python_dependencies(install_dir)
            continue

        print(f"Installing UE {version}...")
        install_engine_artifact(version, install_dir, installer_info)

        # Clear AutomationTool runtime cache (logs from previous runs)
        for cache_dir in [
            install_dir / "Engine" / "Programs" / "AutomationTool" / "Saved",
        ]:
            if cache_dir.exists():
                print(f"  Clearing cache: {cache_dir}")
                shutil.rmtree(cache_dir, ignore_errors=True)

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            uat_cache = Path(local_app_data) / "UnrealEngine" / "Programs" / "AutomationTool"
            if uat_cache.exists():
                shutil.rmtree(uat_cache, ignore_errors=True)

        ensure_ue_python_dependencies(install_dir)
        print(f"UE {version} installed successfully at {install_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Unreal Engine test environment")
    parser.add_argument(
        "--versions",
        nargs="+",
        required=True,
        help="UE versions to install (e.g., 5.6 5.7 5.8)",
    )
    args = parser.parse_args()

    system = platform.system()
    print(f"Setting up {system} with UE {', '.join(args.versions)}")

    if system != "Windows":
        print(f"ERROR: Only Windows is supported (got {system})")
        sys.exit(1)

    for v in args.versions:
        if v not in UE_INSTALLERS:
            print(f"ERROR: Unsupported version {v}. Supported: {list(UE_INSTALLERS.keys())}")
            sys.exit(1)

    setup_windows(args.versions)
    print("Setup complete!")
