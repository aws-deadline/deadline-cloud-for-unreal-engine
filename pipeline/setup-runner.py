#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Setup runner for Unreal Engine integration tests in CodeBuild.

Installs UE 5.7 full SDK on Windows from a zip in S3, along with all
build dependencies (VS Build Tools, .NET Framework SDK, .NET SDK 8.0).

Follows the same pattern as deadline-cloud-for-cinema-4d and
deadline-cloud-for-maya setup runners.

Environment variables required:
    INSTALLER_BUCKET - S3 bucket containing the UE installer zip
    INSTALLER_BUCKET_EXPECTED_OWNER - 12-digit AWS account ID (for verification)
"""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import boto3
from botocore.config import Config


UE_INSTALLERS = {
    "5.7": {
        "windows": {
            "s3_key": "unrealengine/5/UnrealEngine_5.7_FullSDK_Win.zip",
            "sha256": "",
            "type": "zip",
        },
    },
}

UE_INSTALL_PATHS = {
    "5.7": {
        "windows": Path("C:/Program Files/Epic Games/UE_5.7"),
    },
}


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


def verify_checksum(file_path, expected_checksum):
    """Verify SHA256 checksum of downloaded file."""
    if not expected_checksum:
        print(f"WARNING: No checksum configured for {file_path}, skipping verification")
        return
    print(f"Verifying checksum for {file_path}...")
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()
    if actual != expected_checksum:
        print("ERROR: Checksum mismatch!")
        print(f"  Expected: {expected_checksum}")
        print(f"  Actual:   {actual}")
        sys.exit(1)
    print("OK Checksum verified")


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
    msvc_path = Path("C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC")
    if msvc_path.exists() and any(msvc_path.iterdir()):
        # Check if .NET Framework SDK is also present
        netfx_path = Path(
            "C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools"
            "/MSBuild/Microsoft/Microsoft.NET.Build.Extensions"
        )
        if netfx_path.exists():
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

    if not msvc_path.exists():
        print("ERROR: VS Build Tools installation failed")
        sys.exit(1)

    print("VS Build Tools installed successfully")


def extract_zip(zip_path, dest_dir):
    """Extract a zip archive using 7-Zip (faster and lower memory than Python zipfile)."""
    seven_zip = ensure_7zip()
    print(f"Extracting {zip_path} to {dest_dir}...")
    run([seven_zip, "x", str(zip_path), f"-o{dest_dir}", "-y"])


def setup_windows(versions):
    """Install Unreal Engine and build dependencies on Windows."""
    # Install build tools first (needed for plugin compilation)
    ensure_vs_buildtools()

    for version in versions:
        install_dir = UE_INSTALL_PATHS[version]["windows"]
        marker = install_dir / ".installed"
        editor_exe = install_dir / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe"

        if marker.exists() and editor_exe.exists():
            print(f"UE {version} already installed at {install_dir}")
            continue

        print(f"Installing UE {version}...")
        installer_info = UE_INSTALLERS[version]["windows"]
        local_installer = Path(f"C:/Temp/UE_{version}_installer.zip")
        local_installer.parent.mkdir(parents=True, exist_ok=True)

        download_from_s3(installer_info["s3_key"], local_installer)
        verify_checksum(local_installer, installer_info["sha256"])

        install_dir.mkdir(parents=True, exist_ok=True)
        print(f"Extracting to {install_dir} (this may take 10-15 minutes)...")
        extract_zip(local_installer, install_dir)

        # Clean up installer zip
        local_installer.unlink(missing_ok=True)

        # Verify
        if not editor_exe.exists():
            print(f"ERROR: UnrealEditor-Cmd.exe not found at {editor_exe}")
            print("Contents of install dir:")
            for item in sorted(install_dir.iterdir())[:10]:
                print(f"  {item.name}")
            sys.exit(1)

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

        marker.touch()
        print(f"UE {version} installed successfully at {install_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Unreal Engine test environment")
    parser.add_argument(
        "--versions",
        nargs="+",
        required=True,
        help="UE versions to install (e.g., 5.7)",
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
