# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Build script that assembles the adaptor bundle directory for job attachment deployment.

The bundle contains the UE adaptor source modules and runtime dependencies NOT provided
by the Deadline Cloud worker agent. This replaces the conda-based deployment of the
unrealengine-openjd package.

Native dependencies (those containing platform-specific .pyd/.so files) are downloaded
for ALL supported Python versions so the bundle works regardless of the worker's Python
version. Pure-Python dependencies are version-agnostic and only downloaded once.

Usage:
    python adaptorBundle.py [--output <dir>] [--python-version <ver>] [--platform <plat>]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

# Adaptor source modules to include in the bundle (relative to src/deadline/)
ADAPTOR_MODULES = [
    "unreal_adaptor",
    "unreal_perforce_utils",
    "unreal_logger",
    "unreal_cmd_utils",
]

# Dependencies to bundle that are NOT in the worker agent environment.
# Worker agent provides: deadline, boto3, psutil, pywin32, openjd-model, openjd-sessions, pydantic
# Each is installed with --no-deps, so transitive deps must be listed explicitly.
BUNDLE_DEPENDENCIES = [
    "openjd-adaptor-runtime",
    "p4python",
    "jsonschema",
    "jsonschema-specifications",
    "referencing",
    "rpds-py",
    "attrs",
    "pyyaml",
]

# Dependencies that contain native extensions (.pyd/.so) and must be downloaded
# for each supported Python version to ensure compatibility on the worker.
NATIVE_DEPENDENCIES = [
    "rpds-py",
    "p4python",
    "pyyaml",
]

# All Python versions supported on the worker. Native deps are downloaded for each.
SUPPORTED_PYTHON_VERSIONS = ["3.9", "3.10", "3.11", "3.12"]

DEFAULT_PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"
DEFAULT_PLATFORM = "win_amd64"
DEFAULT_OUTPUT_DIR = "adaptor_bundle"

# Wrapper script content for Windows .cmd files
OPENJD_WRAPPER_CONTENT = "@echo off\npython -m deadline.unreal_adaptor.UnrealAdaptor %*\n"
P4_UTILS_WRAPPER_CONTENT = "@echo off\npython -m deadline.unreal_perforce_utils.cli %*\n"


def _get_project_dict() -> dict[str, Any]:
    """Parse pyproject.toml and return the project dictionary."""
    if sys.version_info < (3, 11):
        with TemporaryDirectory() as toml_env:
            subprocess.run(
                ["pip", "install", "--target", toml_env, "toml"], check=True, capture_output=True
            )
            sys.path.insert(0, toml_env)
            import toml  # type: ignore[import-untyped]

        mode = "r"
    else:
        import tomllib as toml

        mode = "rb"

    with open("pyproject.toml", mode) as f:
        return toml.load(f)


def _get_dependency_specs(pyproject_dict: dict[str, Any]) -> list[str]:
    """
    Extract version-pinned dependency specs from pyproject.toml for bundled deps.

    Returns specs like ['openjd-adaptor-runtime>=0.8.1,<0.10', 'p4python==2025.1.2767466', ...]
    Only includes dependencies listed in BUNDLE_DEPENDENCIES.
    """
    project_deps = pyproject_dict.get("project", {}).get("dependencies", [])

    # Normalize names for comparison (PEP 503: lowercase, replace [-_.] with -)
    def normalize(name: str) -> str:
        return (
            name.split()[0]
            .split(">")[0]
            .split("<")[0]
            .split("=")[0]
            .split("!")[0]
            .lower()
            .replace("_", "-")
            .replace(".", "-")
        )

    bundle_names = {d.lower().replace("_", "-").replace(".", "-") for d in BUNDLE_DEPENDENCIES}
    pinned = []
    for dep in project_deps:
        dep_name = normalize(dep)
        if dep_name in bundle_names:
            pinned.append(dep.replace(" ", ""))

    # Add any BUNDLE_DEPENDENCIES not found in pyproject.toml (e.g. jsonschema, pyyaml)
    found_names = {normalize(d) for d in pinned}
    for dep in BUNDLE_DEPENDENCIES:
        if dep.lower().replace("_", "-").replace(".", "-") not in found_names:
            pinned.append(dep)

    return pinned


def _copy_adaptor_modules(bundle_dir: Path) -> None:
    """Copy adaptor source modules from src/deadline/ into the bundle."""
    src_deadline = Path("src") / "deadline"
    dest_deadline = bundle_dir / "deadline"
    dest_deadline.mkdir(parents=True, exist_ok=True)

    for module_name in ADAPTOR_MODULES:
        src_module = src_deadline / module_name
        dest_module = dest_deadline / module_name
        if src_module.is_dir():
            shutil.copytree(str(src_module), str(dest_module))
        else:
            raise FileNotFoundError(f"Adaptor module not found: {src_module}")

    # Generate _version.py in each module (normally created by hatch-vcs at build time)
    for module_name in ADAPTOR_MODULES:
        version_file = dest_deadline / module_name / "_version.py"
        if not version_file.exists():
            version_file.write_text('version = "0.0.0.dev"\n')

    # Remove submitter code if accidentally included
    submitter_dir = dest_deadline / "unreal_submitter"
    if submitter_dir.exists():
        shutil.rmtree(str(submitter_dir))


def _split_native_and_pure_specs(
    dependency_specs: list[str],
) -> tuple[list[str], list[str]]:
    """Split dependency specs into native and pure-Python lists.

    Returns (native_specs, pure_specs) where native_specs are packages
    that contain platform-specific extensions and need multi-version install.
    """

    def _normalize(name: str) -> str:
        return (
            name.split()[0]
            .split(">")[0]
            .split("<")[0]
            .split("=")[0]
            .split("!")[0]
            .lower()
            .replace("_", "-")
            .replace(".", "-")
        )

    native_names = {d.lower().replace("_", "-").replace(".", "-") for d in NATIVE_DEPENDENCIES}
    native_specs = []
    pure_specs = []
    for spec in dependency_specs:
        if _normalize(spec) in native_names:
            native_specs.append(spec)
        else:
            pure_specs.append(spec)
    return native_specs, pure_specs


def _install_dependencies(
    bundle_dir: Path, dependency_specs: list[str], python_version: str, platform: str
) -> None:
    """Download platform-specific wheels for bundle dependencies using pip.

    Pure-Python dependencies are installed once (they are version-agnostic).
    Native dependencies (those with .pyd/.so extensions) are installed for ALL
    supported Python versions so the bundle works regardless of the worker's
    Python interpreter version.

    All dependencies are installed with --no-deps to prevent transitive
    dependencies (e.g. pywin32, typing-extensions) that are already provided
    by the worker agent from being pulled in.
    """
    native_specs, pure_specs = _split_native_and_pure_specs(dependency_specs)

    # Install pure-Python deps once (version-agnostic)
    if pure_specs:
        subprocess.run(
            [
                "pip",
                "install",
                "--target",
                str(bundle_dir),
                "--platform",
                platform,
                "--python-version",
                python_version,
                "--only-binary=:all:",
                "--no-deps",
                *pure_specs,
            ],
            check=True,
        )

    # Install native deps for each supported Python version so the correct
    # .pyd/.so files are available regardless of the worker's Python version.
    if native_specs:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            for ver in SUPPORTED_PYTHON_VERSIONS:
                ver_dir = tmp_path / ver.replace(".", "_")
                ver_dir.mkdir()
                subprocess.run(
                    [
                        "pip",
                        "install",
                        "--target",
                        str(ver_dir),
                        "--platform",
                        platform,
                        "--python-version",
                        ver,
                        "--only-binary=:all:",
                        "--no-deps",
                        *native_specs,
                    ],
                    check=True,
                )
                # Copy files into bundle_dir, skipping duplicates (pure .py files
                # are identical across versions; only .pyd/.so names differ)
                for file in ver_dir.rglob("*"):
                    if file.is_file():
                        relative = file.relative_to(ver_dir)
                        dest = bundle_dir / relative
                        if not dest.exists():
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(file), str(dest))


def _generate_wrapper_scripts(bundle_dir: Path) -> None:
    """Generate .cmd wrapper scripts in the bundle's bin/ directory."""
    bin_dir = bundle_dir / "bin"
    bin_dir.mkdir(exist_ok=True)

    openjd_wrapper = bin_dir / "unreal-engine-openjd.cmd"
    openjd_wrapper.write_text(OPENJD_WRAPPER_CONTENT)

    p4_utils_wrapper = bin_dir / "unreal-engine-p4-utils.cmd"
    p4_utils_wrapper.write_text(P4_UTILS_WRAPPER_CONTENT)


def _cleanup_bundle(bundle_dir: Path) -> None:
    """Remove unnecessary files from the bundle (dist-info, __pycache__, etc.)."""
    for pattern in ["*.dist-info", "__pycache__"]:
        for path in bundle_dir.rglob(pattern):
            if path.is_dir():
                shutil.rmtree(str(path))

    # Remove any bin/ directory created by pip (we generate our own wrappers)
    pip_bin = bundle_dir / "bin"
    # Don't remove our bin dir — only remove pip-generated scripts inside it
    # that aren't our wrappers
    if pip_bin.exists():
        for item in pip_bin.iterdir():
            if item.name not in ("unreal-engine-openjd.cmd", "unreal-engine-p4-utils.cmd"):
                if item.is_file():
                    item.unlink()


def build_adaptor_bundle(
    output_dir: str = DEFAULT_OUTPUT_DIR,
    python_version: str = DEFAULT_PYTHON_VERSION,
    platform: str = DEFAULT_PLATFORM,
) -> Path:
    """
    Build the adaptor bundle directory.

    :param output_dir: Output directory path for the bundle
    :param python_version: Target Python version (e.g. "3.11")
    :param platform: Target platform (e.g. "win_amd64")
    :return: Path to the created bundle directory
    """
    bundle_dir = Path(output_dir)

    # Clean existing bundle
    if bundle_dir.exists():
        shutil.rmtree(str(bundle_dir))
    bundle_dir.mkdir(parents=True)

    # Get dependency specs from pyproject.toml
    project_dict = _get_project_dict()
    dependency_specs = _get_dependency_specs(project_dict)

    print(f"Building adaptor bundle in {bundle_dir}")
    print(f"  Target: Python {python_version}, {platform}")
    print(f"  Dependencies: {dependency_specs}")

    # Copy adaptor source modules
    _copy_adaptor_modules(bundle_dir)
    print("  Copied adaptor modules")

    # Install dependencies
    _install_dependencies(bundle_dir, dependency_specs, python_version, platform)
    print("  Installed dependencies")

    # Generate wrapper scripts
    _generate_wrapper_scripts(bundle_dir)
    print("  Generated wrapper scripts")

    # Cleanup
    _cleanup_bundle(bundle_dir)
    print("  Cleaned up bundle")

    print(f"Bundle created at: {bundle_dir.resolve()}")
    return bundle_dir


def main():
    parser = argparse.ArgumentParser(description="Build the UE adaptor bundle for job attachments")
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--python-version",
        default=DEFAULT_PYTHON_VERSION,
        help=f"Target Python version (default: {DEFAULT_PYTHON_VERSION})",
    )
    parser.add_argument(
        "--platform",
        default=DEFAULT_PLATFORM,
        help=f"Target platform (default: {DEFAULT_PLATFORM})",
    )
    args = parser.parse_args()
    build_adaptor_bundle(args.output, args.python_version, args.platform)


if __name__ == "__main__":
    main()
