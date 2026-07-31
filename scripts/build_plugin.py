# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Helper script for compiling the plugin binaries and Python code and optionally installing it to your Unreal Engine installation
# Currently only works for Windows
# Assumes your environment is capable of building the plugin, specifically that you have installed Unreal and the toolchain
# dependencies as described in https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/docs/user_guide/setup-submitter.md#install-build-tools
# Assumes you're running from the root of your plugin source directory

import argparse
import csv
import logging
import shutil
import os
import subprocess
import sys
import tempfile
from typing import Tuple, Optional

DEFAULT_UE_INSTALL_ROOT = "C:\\Program Files\\Epic Games"
PLUGIN_FOLDER_NAME = "UnrealDeadlineCloudService"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(levelname)s - %(message)s")

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)

logger.addHandler(stream_handler)


def find_unreal_engine(folder: str, version: Optional[str] = None) -> str:
    """
    Finds a version in the given folder by searching for all subfolders which begin with "UE_" and comparing the
    version strings which come after the underscore, or checking against a specified version

    :param folder: Root UE install folder to list for UE_<version> Unreal Engine version installations
    :param version: Specific version string to check for, e.g. 5.5

    :return: Path to root of latest Unreal Engine installation in folder
    """

    logger.info(f"Searching for UE with version {version}")
    if not os.path.exists(folder):
        raise Exception(f"Could not find Unreal Engine install folder at {folder}")

    if version:
        check_version = version
    else:
        # Default to 5.8 if no other versions are found
        check_version = "5.8"
        for subfolder in os.listdir(folder):
            if subfolder.startswith("UE_"):
                version = subfolder.split("_")[1]
                if version > check_version:
                    check_version = version

    engine_root = os.path.join(folder, "UE_" + check_version)
    if not os.path.exists(os.path.join(engine_root, "Engine")):
        raise Exception(
            f"Could not find Unreal Engine folder at {engine_root}, please supply an --engine-root to a valid Unreal installation (Should contain an Engine subfolder) or set UE_INSTALL_ROOT to "
            + "the folder where Unreal is installed (Should contain UE_VERSION.NUM subfolders)"
        )
    return engine_root


def get_plugin_folder(engine_root: str) -> str:
    """
    :return: Path to the plugin folder for UnrealDeadlineCloudService in the given Unreal Engine installation
    """

    return os.path.join(engine_root, "Engine", "Plugins", PLUGIN_FOLDER_NAME)


def build_whl() -> str:
    """
    Builds the python .whl file by running "hatch build", capturing the stderr lines for the .whl file path

    :return: Path to .whl file
    """

    # Attempt to build with hatch, if hatch isn't found, install it with pip
    try:
        subprocess.run(["hatch", "--version"], check=True, stderr=subprocess.PIPE)
    except FileNotFoundError:
        subprocess.run(
            ["python", "-m", "pip", "install", "hatch"], check=True, stderr=subprocess.PIPE
        )
        subprocess.run(["hatch", "--version"], check=True, stderr=subprocess.PIPE)

    # When invoked from inside a hatch-managed env (e.g. the integ-ci env in CI),
    # hatch refuses to build because the active env isn't a builder env. Strip the
    # marker so `hatch build` runs in the default builder context.
    build_env = os.environ.copy()
    build_env.pop("HATCH_ENV_ACTIVE", None)
    result = subprocess.run(["hatch", "build"], stderr=subprocess.PIPE, text=True, env=build_env)
    if result.returncode != 0:
        logger.error(f"hatch build failed with stderr:\n{result.stderr}")
        raise Exception(f"hatch build failed: {result.stderr}")
    lines = result.stderr.splitlines()
    whl_path = None
    # Go through lines, finding the first which ends in .whl
    for line in lines:
        if line.endswith(".whl"):
            whl_path = line
            break

    if not whl_path:
        raise Exception("Failed to retrieve .whl file from hatch build")

    whl_path = os.path.join(get_source_root(), whl_path)

    logger.info(f"Build result: {result.returncode}, whl_path is {whl_path}")
    return whl_path


def install_plugin_build_output(output_folder: str, plugin_folder: str):
    """
    Copies the compiled binaries and resources from the given output folder to the given plugin folder
    """

    logger.info(f"Copying binaries and resources to {plugin_folder}")
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


def install_test_content(plugin_folder: str):
    """
    Copies test data to the destination plugin folder
    """

    logger.info(f"Copying test content to {plugin_folder}")

    source_root = get_source_root()

    template_extension = os.path.join(
        "Source", "UnrealDeadlineCloudService", "Private", "Tests", "openjd_templates"
    )
    template_dir = os.path.join(source_root, "src", "unreal_plugin", template_extension)
    if not os.path.exists(template_dir):
        raise Exception(f"Could not find openjd_templates directory at {template_dir}")

    template_dest_dir = os.path.join(plugin_folder, template_extension)
    shutil.copytree(
        template_dir,
        template_dest_dir,
        dirs_exist_ok=True,
    )


def install_whl_to_plugin(whl_path: str, engine_root: str):
    """
    Installs the given .whl file to the plugin folder in the given Unreal Engine installation

    :param whl_path: Path to .whl file
    :param engine_root: Path to root of Unreal Engine installation
    """

    plugin_folder = get_plugin_folder(engine_root)

    python_path = os.path.join(
        engine_root, "Engine", "Binaries", "ThirdParty", "Python3", "Win64", "python.exe"
    )
    if not os.path.exists(python_path):
        raise Exception(
            f"Could not find Python executable at {python_path}, please supply an --engine-root to a valid Unreal installation or set UE_INSTALL_ROOT to "
            + "the folder where Unreal is installed (Should contain UE_VERSION.NUM subfolders)"
        )

    plugin_libraries_path = os.path.join(plugin_folder, "Content", "Python", "libraries")

    # Pip install the .whl file to the plugin libraries path.
    # --force-reinstall is required because pip install -t still checks the
    # interpreter's own site-packages for already-satisfied dependencies.
    # Without it, an older 'deadline' in UE Python's Lib/site-packages causes
    # pip to skip installing the required version into the target directory.
    logger.info(f"Installing {whl_path} to {plugin_libraries_path}")
    result = subprocess.run(
        [
            python_path,
            "-m",
            "pip",
            "install",
            whl_path,
            "-t",
            plugin_libraries_path,
            "--force-reinstall",
        ],
        check=True,
    )
    logger.info(f"Install result: {result.returncode}")


def install_plugin(engine_root: str, output_folder: str, whl_path: str, binaries: bool):
    """
    Installs the plugin to the given Unreal Engine installation, copying the compiled binaries and resources from the given output folder and
    installing the whl file

    :param engine_root: Path to root of Unreal Engine installation
    :param output_folder: Path to folder where runuat has output the plugin binaries and resources to
    :param whl_path: Path to compiled .whl file to install
    """

    plugin_folder = get_plugin_folder(engine_root)

    if binaries and os.path.exists(plugin_folder):
        logger.info(f"Removing existing plugin folder at {plugin_folder}")
        shutil.rmtree(plugin_folder)

    if binaries:
        install_plugin_build_output(output_folder, plugin_folder)
    install_whl_to_plugin(whl_path, engine_root)
    logger.info(f"Plugin installed to {plugin_folder}")


def install_whl_global(whl_path: str):
    """
    Installs the given .whl file to the global python interpreter.

    Done in two passes so iterative dev builds reliably overwrite installed
    files without paying the dependency-resolve cost on every build:

    1. ``pip install <whl>`` — resolves and installs deps the first time;
       on subsequent builds where deps are already satisfied this is a fast
       metadata check.
    2. ``pip install <whl> --force-reinstall --no-deps`` — overwrites the
       package's own files even when the version string is unchanged, which
       the previous --upgrade strategy would silently skip.

    :param whl_path: Path to whl file
    """

    if not os.path.exists(whl_path):
        raise Exception(f"Could not find .whl file at {whl_path}")

    # Pass 1: ensure dependencies are present.
    logger.info(f"Installing {whl_path} dependencies to global interpreter")
    subprocess.run(
        ["python", "-m", "pip", "install", whl_path],
        check=True,
    )

    # Pass 2: force-overwrite the package itself so iterative builds with the
    # same version string actually replace files on disk.
    logger.info(f"Force-reinstalling {whl_path} to global interpreter")
    result = subprocess.run(
        ["python", "-m", "pip", "install", whl_path, "--force-reinstall", "--no-deps"],
        check=True,
    )
    logger.info(f"Install result: {result.returncode}")


def find_engine_root(version: Optional[str] = None) -> str:
    """
    Find the latest version of Unreal Engine

    :return: Path to root of engine
    """

    ue_install_root = os.environ.get("UE_INSTALL_ROOT", DEFAULT_UE_INSTALL_ROOT)
    ue_install_root = os.path.expanduser(ue_install_root)
    return find_unreal_engine(ue_install_root, version)


def find_runuat(engine_root: str) -> str:
    """
    Check if the "RunUAT.bat" file exists in the expected location for this Engine root, raise an exception if not

    :param engine_root: Path to root of Unreal Engine installation

    :return: Path to RunUAT in the given Unreal Engine installation
    """
    if not engine_root:
        engine_root = find_engine_root()
    runuat_path = os.path.join(engine_root, "Engine", "Build", "BatchFiles", "RunUAT.bat")
    if not os.path.exists(runuat_path):
        raise Exception(
            f"Could not find RunUAT.bat at {runuat_path}, please supply an --engine-root to a valid Unreal installation or set UE_INSTALL_ROOT to "
            + "the folder where Unreal is installed (Should contain UE_VERSION.NUM subfolders)"
        )
    logger.info(f"Found RunUAT.bat at {runuat_path}")
    return runuat_path


def get_source_root() -> str:
    """
    Return the path of the root of the deadline-cloud-for-unreal-engine source.  Assumes it's 1 folder up from the directory this
    file lives in, which is in a "/scripts/" subfolder off the root
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Get the parent directory
    parent_dir = os.path.dirname(current_dir)
    return parent_dir


def get_input_uplugin_path() -> str:
    """
    Return the path of the .uplugin file to build.  Assumes cwd is the root of deadline-cloud-for-unreal-engine

    :return: Path to .uplugin file within repo
    """

    uplugin_path = os.path.join(
        get_source_root(), "src", "unreal_plugin", "UnrealDeadlineCloudService.uplugin"
    )
    if not os.path.exists(uplugin_path):
        raise Exception(
            f"Could not find UnrealDeadlineCloudService.uplugin at expected path {uplugin_path}, please run this script from the root of the repo"
        )
    return uplugin_path


def build_plugin(runuat_path: str, plugin_input_folder: str, output_folder: str):
    """
    Run the RunUAT.bat file to build the plugin

    :param runuat_path: Path to RunUAT.bat file
    :param plugin_input_folder: Path to .uplugin file to build
    :param output_folder: Path to folder to build the plugin in
    """

    logger.info("Building plugin...")
    # Build the plugin
    result = subprocess.run(
        [
            runuat_path,
            "BuildPlugin",
            f"-Plugin={plugin_input_folder}",
            f"-package={output_folder}",
        ],
        check=True,
    )
    if result.returncode != 0:
        raise Exception(f"Build failed {result.returncode}")


def _warn_if_deadline_worker_service_running():
    """Warn the user if the DeadlineWorker service is running and needs a restart."""
    if sys.platform != "win32":
        return
    try:
        result = subprocess.run(
            ["sc", "query", "DeadlineWorker"],
            capture_output=True,
            text=True,
        )
        if "RUNNING" in result.stdout:
            logger.warning(
                "The DeadlineWorker service is currently running. "
                "Restart it to pick up the new code: Restart-Service DeadlineWorker"
            )
    except Exception:
        pass


def install_worker_dependencies(engine_root: str):
    """
    Installs the dependencies required for the worker plugin to function

    :param engine_root: Path to root of Unreal Engine installation
    """

    logger.info("Installing worker dependencies...")
    python_path = os.path.join(
        engine_root, "Engine", "Binaries", "ThirdParty", "Python3", "Win64", "python.exe"
    )
    if not os.path.exists(python_path):
        raise Exception(
            f"Could not find Python executable at {python_path}, please supply an --engine-root to a valid Unreal installation or set UE_INSTALL_ROOT to "
            + "the folder where Unreal is installed (Should contain UE_VERSION.NUM subfolders)"
        )

    worker_dependencies = ["pywin32"]
    for dep in worker_dependencies:
        subprocess.run(
            [python_path, "-m", "pip", "install", dep],
            check=True,
        )

    subprocess.run(
        [
            "python",
            "-m",
            "pip",
            "install",
            "deadline-cloud-worker-agent",
            "--upgrade",
            "--upgrade-strategy",
            "eager",
        ],
        check=True,
        stderr=subprocess.PIPE,
    )


def unreal_python_has_deadline_installed(engine_root: str) -> Tuple[bool, Optional[str]]:
    """
    Test if deadline appears to already be installed to the "Unreal" version of Python's
    libraries folder where it could potentially take precedence over what we're installing
    """
    if sys.platform != "win32":
        return False, None
    python_libs_folder = os.path.join(
        engine_root, "Engine\\Binaries\\ThirdParty\\Python3\\Win64\\Lib"
    )
    deadline_folder = os.path.join(python_libs_folder, "deadline")

    if os.path.exists(deadline_folder):
        return True, deadline_folder

    return False, deadline_folder


def long_paths_enabled() -> bool:
    """
    Test if Windows long paths are enabled by attempting to create a long path.
    We need to support both Admin and non Admin usage, so rather than attempt to check
    the registry we'll simply try to create a file in a folder which exceeds the path limit
    and catch possible exceptions.
    """

    # We're only interested in checking on Windows currently
    if sys.platform != "win32":
        return True

    # Create a temporary directory as our base
    with tempfile.TemporaryDirectory() as temp_base:
        try:
            # Create a path that exceeds the traditional 260 character limit
            long_name = "a" * 250  # Do not exceeed 255 character directory name/file name limit
            long_path = os.path.join(temp_base, long_name)

            # Validate that a folder can be created which exceeds 260 characters
            os.makedirs(long_path, exist_ok=True)

            # Validate that a file can be created in that folder
            test_file = os.path.join(long_path, "some_long_path_test.txt")
            with open(test_file, "w") as f:
                f.write("Test successful")

            # Long paths appear to be enabled
            return True

        except (OSError, FileNotFoundError, PermissionError) as e:
            # If we get an error about the path being too long, then long paths are not enabled
            if "path too long" in str(e).lower() or "cannot find the path" in str(e).lower():
                return False

            # For other errors, print but still return False as we couldn't create the long path
            print(f"Error during long path test: {e}")
            return False


def check_running_unreal_processes():
    """
    Check for running Unreal Engine processes that might interfere with the build.

    Returns:
        bool: True if any Unreal processes are running, False otherwise
    """
    if sys.platform != "win32":
        return False

    target_names = {"unrealeditor.exe", "unrealeditor-cmd.exe"}
    unreal_processes = []
    try:
        # tasklist /FO CSV /NH outputs: "Image Name","PID","Session Name","Session#","Mem Usage"
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        logger.warning(f"Could not check for running Unreal processes: {e}")
        return False

    for row in csv.reader(result.stdout.splitlines()):
        if len(row) < 2:
            continue
        name, pid = row[0], row[1]
        if name.lower() in target_names:
            unreal_processes.append({"name": name, "pid": pid})

    if unreal_processes:
        logger.warning(
            "WARNING: Found running Unreal Engine processes that may interfere with the build:"
        )
        for proc in unreal_processes:
            logger.warning(f"  - {proc['name']} (PID: {proc['pid']})")
        logger.warning(
            "Consider closing these processes before building to avoid file locking issues."
        )
        return True

    return False


def check_configuration_warnings(engine_root: str):
    """
    Check for common configuration issues which may prevent successful jobs
    """
    # Check for running Unreal processes
    check_running_unreal_processes()

    if long_paths_enabled():
        logger.info("Long paths are enabled")
    else:
        logger.warning(
            "Windows long paths are not enabled.  Please see "
            "https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/docs/user_guide/setup-submitter.md#windows-long-paths"
            "for instructions on enabling."
        )

    deadline_installed, deadline_path = unreal_python_has_deadline_installed(engine_root)
    if deadline_installed:
        logger.warning(
            f"deadline appears to be installed at {deadline_path}.  Please uninstall the deadline tools from this location"
            "to prevent conflicts."
        )


def build_and_install(
    engine_root: str = "",
    uplugin_path: str = "",
    output_folder: str = "",
    install: bool = False,
    worker: bool = False,
    binaries: bool = True,
    test: bool = False,
    version: str = "",
):
    """
    Build the plugin and optionally install it to the given Unreal Engine installation

    :param engine_root: Path to root of Unreal Engine installation
    :param uplugin_path: Path to .uplugin file to build
    :param output_folder: Path to folder to build the plugin in
    :param install: Whether to install the plugin to the Unreal Engine installation
    :param worker: Whether to install the plugin as a worker plugin to the global python interpreter
    :param binaries: Should binaries be included in the installation
    :param test: Should test content be included in the plugin installation
    :param version: Specific version to use if found
    """

    logger.info("Beginning build...")

    # Find the latest version of Unreal Engine
    if not engine_root:
        engine_root = find_engine_root(version)

    check_configuration_warnings(engine_root)

    runuat_path = find_runuat(engine_root)

    # Create a TemporaryDirectory to build into if no output_folder given
    output_folder = output_folder or tempfile.TemporaryDirectory().name

    # Either input_folder path to .uplugin is given, or we assume you're in the root of the repo
    plugin_input_folder = uplugin_path or get_input_uplugin_path()

    if binaries:
        build_plugin(runuat_path, plugin_input_folder, output_folder)

    whl_path = build_whl()

    if install:
        install_plugin(engine_root, output_folder, whl_path, binaries)

    if worker:
        install_whl_global(whl_path)
        install_worker_dependencies(engine_root)
        _warn_if_deadline_worker_service_running()

    if test:
        install_test_content(get_plugin_folder(engine_root))


def main():

    parser = argparse.ArgumentParser(
        description="Build the Deadline Cloud plugin for Unreal Engine"
    )
    parser.add_argument(
        "--engine-root",
        type=str,
        help="Path to the root of the Unreal Engine installation.  Attempts to find latest version if not provided.",
    )
    parser.add_argument(
        "--ueversion",
        type=str,
        help="Assuming default engine root, attempts to find the given version within",
    )
    parser.add_argument(
        "--uplugin-path",
        type=str,
        help="Path to the .uplugin file for the plugin to build.  Assumes the .uplugin at the default path within this repository if not provided.",
    )
    parser.add_argument(
        "--output-folder",
        type=str,
        help="Path to the output folder for the plugin build.  Creates and uses a temporary folder if not provided.",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install the plugin to the Unreal Engine installation",
    )
    parser.add_argument(
        "--worker",
        action="store_true",
        help="Install the plugin as a worker plugin to the global python interpreter, including the built .whl and worker dependencies.  Generally should be paired with --install.  Requires admin/elevated privileges on Windows; the submitter-only --install path does not.",
    )
    parser.add_argument(
        "--no-binaries",
        default=False,
        action="store_true",
        help="Skip building new binaries",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Include test content in the destination plugin install",
    )
    args = parser.parse_args()

    build_and_install(
        engine_root=args.engine_root,
        uplugin_path=args.uplugin_path,
        output_folder=args.output_folder,
        install=args.install,
        worker=args.worker,
        binaries=not args.no_binaries,
        test=args.test,
        version=args.ueversion,
    )


if __name__ == "__main__":
    main()
