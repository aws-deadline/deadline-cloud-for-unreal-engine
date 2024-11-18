# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Helper script for compiling the plugin and optionally uploading an archive of the binaries and unreal dependencies to S3
# Currently only works for Windows
# Assumes your environment is capable of building the plugin, specifically that you have installed Unreal and the toolchain
# dependencies as described in https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/SETUP_SUBMITTER_CMF.md#install-build-tools
# Assumes you're running from the root of your plugin source directory

import shutil
import boto3
import os
import subprocess
import tempfile

DEFAULT_UE_INSTALL_ROOT = "C:\\Program Files\\Epic Games"
BUILD_OUTPUT_FOLDER = "Build"
PLUGIN_FOLDER_NAME = "UnrealDeadlineCloudService"
BUCKET_PREBUILDS_FOLDER = "component_prebuilds"
PREBUILD_PLATFORM = "windows-x64"  # Currently only supporting windows
COMPONENT_ZIP_FILE = "deadline-cloud-for-unreal-engine"


def find_latest_runuat_version(folder: str) -> str:
    # Finds the latest version in the the given folder by searching for all subfolders which begin with "UE_" and comparing the
    # version strings which come after the underscore
    latest_version = "5.2"
    # Default to 5.2 if no other versions are found
    for subfolder in os.listdir(folder):
        if subfolder.startswith("UE_"):
            version = subfolder.split("_")[1]
            if version > latest_version:
                latest_version = version
    # Check if the "runuat.bat" file exists in the latest folder version, raise an exception if not
    runuat_path = os.path.join(
        folder, "UE_" + latest_version, "Engine", "Build", "BatchFiles", "RunUAT.bat"
    )
    if not os.path.exists(runuat_path):
        raise Exception(
            f"Could not find RunUAT.bat at {runuat_path}, please supply a --runuat-path or set UE_INSTALL_ROOT to "
            + "the folder where Unreal is installed (Should contain UE_VERSION.NUM subfolders)"
        )
    print(f"Found RunUAT.bat at {runuat_path}")
    return runuat_path


def build_plugin(
    runuat_path: str = None,
    input_folder: str = None,
    output_folder: str = None,
    upload_bucket: str = None,
):
    print("Building plugin...")
    # Create a TemporaryDirectory to build into if no output_folder given
    output_folder = output_folder or tempfile.TemporaryDirectory().name

    # Find the latest version of Unreal Engine
    if not runuat_path:
        ue_install_root = os.environ.get("UE_INSTALL_ROOT", DEFAULT_UE_INSTALL_ROOT)
        ue_install_root = os.path.expanduser(ue_install_root)
        runuat_path = find_latest_runuat_version(ue_install_root)

    output_folder = os.path.join(output_folder, BUILD_OUTPUT_FOLDER)

    # Either input_folder path to .uplugin is given, or we assume you're in the root of the repo
    plugin_input_folder = input_folder or os.path.join(
        os.getcwd(), "src", "unreal_plugin", "UnrealDeadlineCloudService.uplugin"
    )

    # Build the plugin
    result = subprocess.run(
        [
            runuat_path,
            "BuildPlugin",
            f"-Plugin={plugin_input_folder}",
            f"-package={output_folder}",
            "-TargetPlatform=Win64",
        ],
        check=True,
    )
    print(f"Build result: {result.returncode}")

    # Prepare to create an archive.  First create the archive/plugin folder if it doesn't exist
    archive_folder = os.path.join(output_folder, "archive")
    plugin_folder = os.path.join(archive_folder, PLUGIN_FOLDER_NAME)
    print(f"Creating folder {plugin_folder}")
    os.makedirs(plugin_folder, exist_ok=True)
    print(f"Copying binaries and resources to {plugin_folder}")
    # Copy the Binaries, Content and Resources subfolders to the plugin folder, ignoring .pdb files
    shutil.copytree(
        os.path.join(output_folder, "Binaries"),
        os.path.join(plugin_folder, "Binaries"),
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("*.pdb"),
    )
    shutil.copytree(
        os.path.join(output_folder, "Resources"),
        os.path.join(plugin_folder, "Resources"),
        dirs_exist_ok=True,
    )
    shutil.copytree(
        os.path.join(output_folder, "Content"),
        os.path.join(plugin_folder, "Content"),
        dirs_exist_ok=True,
    )
    shutil.copy2(os.path.join(output_folder, f"{PLUGIN_FOLDER_NAME}.uplugin"), plugin_folder)

    # Create a zip of the output_folder which contains only the Binaries and Resources subfolders, outputting the archive into output_folder
    output_archive = os.path.join(archive_folder, f"{COMPONENT_ZIP_FILE}.zip")
    print(f"Creating archive at {output_archive}")
    # Create a zip archive of the contents of the archive folder which will be named "deadline-cloud-for-unreal-engine.zip"
    shutil.make_archive(
        base_name=os.path.splitext(output_archive)[0],
        format="zip",
        root_dir=archive_folder,
        base_dir=PLUGIN_FOLDER_NAME,
    )
    print(f"Archive created: {output_archive}")

    # Optionally upload the archive to S3
    if upload_bucket:
        print(f"Uploading archive to S3 bucket {upload_bucket}")
        s3 = boto3.client("s3")
        upload_key = f"{BUCKET_PREBUILDS_FOLDER}/{PREBUILD_PLATFORM}/{COMPONENT_ZIP_FILE}.zip"
        s3.upload_file(output_archive, upload_bucket, upload_key)
        print(f"Archive uploaded to s3://{upload_bucket}/{upload_key}")


if __name__ == "__main__":
    # Parse optional command line arguments for runuat_path, input_folder, output_folder, upload_bucket
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--runuat-path", help="Path to RunUAT.bat")
    parser.add_argument("--input-folder", help="Path to plugin input folder")
    parser.add_argument("--output-folder", help="Path to output folder")
    parser.add_argument("--upload-bucket", help="S3 bucket to upload archive to")
    args = parser.parse_args()
    build_plugin(args.runuat_path, args.input_folder, args.output_folder, args.upload_bucket)
