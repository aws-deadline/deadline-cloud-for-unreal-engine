# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for adaptor bundle integration with the submitter."""

import sys
import yaml
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock unreal and problematic native dependencies before importing submitter code
unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock
# Mock P4 module which requires native SSL
if "P4" not in sys.modules:
    sys.modules["P4"] = MagicMock()

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (  # noqa: E402
    RenderUnrealOpenJob,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (  # noqa: E402
    OpenJobParameterNames,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (  # noqa: E402
    AdaptorSetupUnrealOpenJobEnvironment,
)
from deadline.unreal_submitter import settings  # noqa: E402
from deadline.client.job_bundle.submission import AssetReferences  # noqa: E402


class TestAdaptorSetupEnvironment:
    """Tests for the AdaptorSetup environment class and template."""

    def test_default_template_path(self):
        """Verify the default template path points to adaptor_setup_environment.yml."""
        assert (
            AdaptorSetupUnrealOpenJobEnvironment.default_template_path
            == "adaptor_setup_environment.yml"
        )

    def test_adaptor_setup_template_exists(self):
        """Verify the adaptor_setup_environment.yml template file exists."""
        templates_dir = settings.OPENJD_TEMPLATES_DIRECTORY
        if templates_dir:
            template_path = Path(templates_dir) / "adaptor_setup_environment.yml"
        else:
            # Fall back to the source tree location
            template_path = (
                Path(__file__).parents[4]
                / "src"
                / "unreal_plugin"
                / "Content"
                / "Python"
                / "openjd_templates"
                / "adaptor_setup_environment.yml"
            )
        assert template_path.exists(), f"Template not found at {template_path}"

    def test_adaptor_setup_template_content(self):
        """Verify the template has the expected structure."""
        template_path = (
            Path(__file__).parents[4]
            / "src"
            / "unreal_plugin"
            / "Content"
            / "Python"
            / "openjd_templates"
            / "adaptor_setup_environment.yml"
        )
        with open(template_path) as f:
            template = yaml.safe_load(f)

        assert template["name"] == "AdaptorSetup"
        assert "script" in template
        assert "embeddedFiles" in template["script"]
        assert "actions" in template["script"]
        assert "onEnter" in template["script"]["actions"]

        # Verify the embedded script checks for conda, bundle, and fails gracefully
        setup_script = template["script"]["embeddedFiles"][0]["data"]
        assert "where unreal-engine-openjd" in setup_script
        assert "BUNDLE_PATH" in setup_script
        assert "PYTHONPATH" in setup_script
        assert "ERROR" in setup_script

    def test_adaptor_setup_template_bundle_checked_before_conda(self):
        """Verify the template checks for bundle BEFORE checking conda on PATH."""
        template_path = (
            Path(__file__).parents[4]
            / "src"
            / "unreal_plugin"
            / "Content"
            / "Python"
            / "openjd_templates"
            / "adaptor_setup_environment.yml"
        )
        with open(template_path) as f:
            template = yaml.safe_load(f)

        setup_script = template["script"]["embeddedFiles"][0]["data"]
        # Use the actual condition check (goto :check_conda on empty), not the variable assignment
        bundle_check_pos = setup_script.index('if not exist "%BUNDLE_PATH%\\bin"')
        conda_check_pos = setup_script.index("where unreal-engine-openjd")
        assert (
            bundle_check_pos < conda_check_pos
        ), "Bundle existence check must come before conda check in AdaptorSetup script"

    def test_adaptor_setup_template_no_variables(self):
        """Verify the template has no variables key (not needed)."""
        template_path = (
            Path(__file__).parents[4]
            / "src"
            / "unreal_plugin"
            / "Content"
            / "Python"
            / "openjd_templates"
            / "adaptor_setup_environment.yml"
        )
        with open(template_path) as f:
            template = yaml.safe_load(f)

        assert "variables" not in template


class TestOpenJobParameterNames:
    """Tests for the AdaptorBundlePath parameter name constant."""

    def test_adaptor_bundle_path_constant_exists(self):
        """Verify ADAPTOR_BUNDLE_PATH is defined in OpenJobParameterNames."""
        assert hasattr(OpenJobParameterNames, "ADAPTOR_BUNDLE_PATH")
        assert OpenJobParameterNames.ADAPTOR_BUNDLE_PATH == "AdaptorBundlePath"


class TestRenderUnrealOpenJobAdaptorSetup:
    """Tests for RenderUnrealOpenJob adaptor bundle integration."""

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_init_inserts_adaptor_setup_environment(self, get_template_object_mock):
        """Verify AdaptorSetup environment is automatically inserted at position 0."""
        get_template_object_mock.return_value = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            "parameterDefinitions": [
                {"name": "CondaPackages", "type": "STRING", "default": "unrealengine=5.7"},
                {
                    "name": "AdaptorBundlePath",
                    "type": "PATH",
                    "objectType": "DIRECTORY",
                    "dataFlow": "IN",
                },
            ],
        }

        job = RenderUnrealOpenJob(name="TestJob")

        # Verify AdaptorSetup is the first environment
        assert len(job._environments) >= 1
        assert isinstance(job._environments[0], AdaptorSetupUnrealOpenJobEnvironment)

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_init_does_not_duplicate_adaptor_setup(self, get_template_object_mock):
        """Verify AdaptorSetup is not duplicated if already provided."""
        get_template_object_mock.return_value = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            "parameterDefinitions": [
                {"name": "CondaPackages", "type": "STRING", "default": "unrealengine=5.7"},
            ],
        }

        existing_adaptor_env = AdaptorSetupUnrealOpenJobEnvironment()
        job = RenderUnrealOpenJob(
            name="TestJob",
            environments=[existing_adaptor_env],
        )

        adaptor_envs = [
            e for e in job._environments if isinstance(e, AdaptorSetupUnrealOpenJobEnvironment)
        ]
        assert len(adaptor_envs) == 1

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
        "UnrealOpenJob.get_plugins_references"
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
        "RenderUnrealOpenJob._get_mrq_job_dependency_paths"
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
        "RenderUnrealOpenJob._get_adaptor_bundle_dir"
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_get_asset_references_includes_bundle_dir(
        self, get_template_object_mock, mock_bundle_dir, mock_dep_paths, mock_plugins
    ):
        """Verify adaptor bundle directory is added to input_directories."""
        get_template_object_mock.return_value = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            "parameterDefinitions": [
                {"name": "CondaPackages", "type": "STRING", "default": "unrealengine=5.7"},
                {
                    "name": "AdaptorBundlePath",
                    "type": "PATH",
                    "objectType": "DIRECTORY",
                    "dataFlow": "IN",
                    "default": "",
                },
            ],
        }
        mock_bundle_dir.return_value = "/path/to/adaptor_bundle"
        mock_dep_paths.return_value = []
        mock_plugins.return_value = AssetReferences()

        job = RenderUnrealOpenJob(name="TestJob")
        asset_refs = job.get_asset_references()

        assert "/path/to/adaptor_bundle" in asset_refs.input_directories

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
        "UnrealOpenJob.get_plugins_references"
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
        "RenderUnrealOpenJob._get_mrq_job_dependency_paths"
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
        "RenderUnrealOpenJob._get_adaptor_bundle_dir"
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_get_asset_references_skips_when_no_bundle(
        self, get_template_object_mock, mock_bundle_dir, mock_dep_paths, mock_plugins
    ):
        """Verify get_asset_references succeeds (no crash) when bundle directory doesn't exist."""
        get_template_object_mock.return_value = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            "parameterDefinitions": [
                {"name": "CondaPackages", "type": "STRING", "default": "unrealengine=5.7"},
                {
                    "name": "AdaptorBundlePath",
                    "type": "PATH",
                    "objectType": "DIRECTORY",
                    "dataFlow": "IN",
                    "default": "",
                },
            ],
        }
        mock_bundle_dir.return_value = None
        mock_dep_paths.return_value = []
        mock_plugins.return_value = AssetReferences()

        job = RenderUnrealOpenJob(name="TestJob")

        # Should not raise — bundle missing is tolerated outside submission
        asset_refs = job.get_asset_references()
        assert "adaptor_bundle" not in str(asset_refs.input_directories)


class TestJobTemplateCondaPackagesDefault:
    """Tests for the updated CondaPackages default in job templates."""

    def test_render_job_conda_packages_default(self):
        """Verify render_job.yml CondaPackages default is 'unrealengine=5.7' only."""
        template_path = (
            Path(__file__).parents[4]
            / "src"
            / "unreal_plugin"
            / "Content"
            / "Python"
            / "openjd_templates"
            / "render_job.yml"
        )
        with open(template_path) as f:
            template = yaml.safe_load(f)

        conda_param = next(
            p for p in template["parameterDefinitions"] if p["name"] == "CondaPackages"
        )
        assert conda_param["default"] == "unrealengine=5.7"
        assert "unrealengine-openjd" not in conda_param["default"]

    def test_p4_render_job_conda_packages_default(self):
        """Verify p4_render_job.yml CondaPackages default is 'unrealengine=5.7' only."""
        template_path = (
            Path(__file__).parents[4]
            / "src"
            / "unreal_plugin"
            / "Content"
            / "Python"
            / "openjd_templates"
            / "p4"
            / "p4_render_job.yml"
        )
        with open(template_path) as f:
            template = yaml.safe_load(f)

        conda_param = next(
            p for p in template["parameterDefinitions"] if p["name"] == "CondaPackages"
        )
        assert conda_param["default"] == "unrealengine=5.7"
        assert "unrealengine-openjd" not in conda_param["default"]

    def test_render_job_has_adaptor_bundle_path_param(self):
        """Verify render_job.yml has AdaptorBundlePath parameter definition."""
        template_path = (
            Path(__file__).parents[4]
            / "src"
            / "unreal_plugin"
            / "Content"
            / "Python"
            / "openjd_templates"
            / "render_job.yml"
        )
        with open(template_path) as f:
            template = yaml.safe_load(f)

        param_names = [p["name"] for p in template["parameterDefinitions"]]
        assert "AdaptorBundlePath" in param_names

        bundle_param = next(
            p for p in template["parameterDefinitions"] if p["name"] == "AdaptorBundlePath"
        )
        assert bundle_param["type"] == "PATH"
        assert bundle_param["objectType"] == "DIRECTORY"
        assert bundle_param["dataFlow"] == "IN"
        assert bundle_param["default"] == ""
        assert bundle_param["userInterface"]["control"] == "HIDDEN"

    def test_p4_render_job_has_adaptor_bundle_path_param(self):
        """Verify p4_render_job.yml has AdaptorBundlePath parameter definition."""
        template_path = (
            Path(__file__).parents[4]
            / "src"
            / "unreal_plugin"
            / "Content"
            / "Python"
            / "openjd_templates"
            / "p4"
            / "p4_render_job.yml"
        )
        with open(template_path) as f:
            template = yaml.safe_load(f)

        param_names = [p["name"] for p in template["parameterDefinitions"]]
        assert "AdaptorBundlePath" in param_names

        bundle_param = next(
            p for p in template["parameterDefinitions"] if p["name"] == "AdaptorBundlePath"
        )
        assert bundle_param["type"] == "PATH"
        assert bundle_param["objectType"] == "DIRECTORY"
        assert bundle_param["dataFlow"] == "IN"
        assert bundle_param["default"] == ""
        assert bundle_param["userInterface"]["control"] == "HIDDEN"


class TestGetAdaptorBundleDir:
    """Tests for RenderUnrealOpenJob._get_adaptor_bundle_dir()."""

    @patch("deadline.unreal_submitter.unreal_open_job.unreal_open_job.settings")
    def test_returns_none_when_setting_empty(self, mock_settings):
        """Verify None returned when ADAPTOR_BUNDLE_DIRECTORY is empty."""
        mock_settings.ADAPTOR_BUNDLE_DIRECTORY = ""

        result = RenderUnrealOpenJob._get_adaptor_bundle_dir()
        assert result is None

    @patch("deadline.unreal_submitter.unreal_open_job.unreal_open_job.settings")
    def test_returns_none_when_dir_does_not_exist(self, mock_settings, tmp_path):
        """Verify None returned when ADAPTOR_BUNDLE_DIRECTORY points to nonexistent path."""
        mock_settings.ADAPTOR_BUNDLE_DIRECTORY = str(tmp_path / "nonexistent_bundle")

        result = RenderUnrealOpenJob._get_adaptor_bundle_dir()
        assert result is None

    @patch("deadline.unreal_submitter.unreal_open_job.unreal_open_job.settings")
    def test_returns_resolved_path_when_dir_exists(self, mock_settings, tmp_path):
        """Verify resolved path returned when ADAPTOR_BUNDLE_DIRECTORY exists."""
        bundle_dir = tmp_path / "adaptor_bundle"
        bundle_dir.mkdir()
        mock_settings.ADAPTOR_BUNDLE_DIRECTORY = str(bundle_dir)

        result = RenderUnrealOpenJob._get_adaptor_bundle_dir()
        assert result == str(bundle_dir.resolve())

    @patch("deadline.unreal_submitter.unreal_open_job.unreal_open_job.settings")
    def test_does_not_use_cwd_fallback(self, mock_settings, tmp_path, monkeypatch):
        """Verify CWD is never used as a fallback — only the explicit setting matters."""
        # Create adaptor_bundle in CWD — should NOT be found
        cwd_bundle = tmp_path / "cwd_workspace"
        cwd_bundle.mkdir()
        (cwd_bundle / "adaptor_bundle").mkdir()
        monkeypatch.chdir(cwd_bundle)

        # Setting points nowhere
        mock_settings.ADAPTOR_BUNDLE_DIRECTORY = str(tmp_path / "nonexistent")

        result = RenderUnrealOpenJob._get_adaptor_bundle_dir()
        assert result is None, "CWD must never be used as a fallback for security reasons"


class TestAdaptorSetupScriptEmptyPathGuard:
    """Tests that the adaptor-setup.cmd script guards against empty/invalid BUNDLE_PATH.

    B2 review concern: if OpenJD path-maps an empty string default into '.' or
    the working directory, 'if exist' alone would pass. The script must also
    check that BUNDLE_PATH is non-empty AND that the expected 'bin' subdirectory
    exists inside it, to avoid silently setting PYTHONPATH to a wrong directory.
    """

    @staticmethod
    def _get_setup_script() -> str:
        template_path = (
            Path(__file__).parents[4]
            / "src"
            / "unreal_plugin"
            / "Content"
            / "Python"
            / "openjd_templates"
            / "adaptor_setup_environment.yml"
        )
        with open(template_path) as f:
            template = yaml.safe_load(f)
        return template["script"]["embeddedFiles"][0]["data"]

    def test_script_guards_against_empty_string(self):
        """Verify the script checks BUNDLE_PATH is non-empty before 'if exist'."""
        script = self._get_setup_script()
        # The script should skip to conda fallback when BUNDLE_PATH is empty
        assert '"%BUNDLE_PATH%"==""' in script, (
            "Setup script must guard against empty BUNDLE_PATH. "
            "An empty PATH parameter could be path-mapped to '.' or CWD."
        )

    def test_script_validates_bundle_structure(self):
        """Verify the script checks for 'bin' subdir, not just directory existence."""
        script = self._get_setup_script()
        # Checking for bin/ inside the bundle is a structural validation
        # that prevents false positives from random directories
        assert "\\bin" in script, (
            "Setup script should validate bundle structure (e.g. bin/ subdir) "
            "not just directory existence."
        )

    def test_script_does_not_use_delayed_expansion(self):
        """Verify the script avoids EnableDelayedExpansion.

        EnableDelayedExpansion corrupts paths containing '!' characters.
        Instead, the script uses goto/label to keep %PATH% expansion
        outside of if ( ... ) blocks, avoiding the complementary problem
        where ')' in PATH (e.g. 'Program Files (x86)') breaks if blocks.
        """
        script = self._get_setup_script()
        assert "EnableDelayedExpansion" not in script
        assert "!PATH!" not in script
        # Should use %PATH% directly, outside of if () blocks
        assert "%PATH%" in script


class TestCreateJobBundleAdaptorValidation:
    """Tests for RenderUnrealOpenJob.create_job_bundle() adaptor bundle validation."""

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
        "RenderUnrealOpenJob._get_adaptor_bundle_dir"
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_raises_when_bundle_missing(self, get_template_object_mock, mock_bundle_dir):
        """Verify create_job_bundle raises FileNotFoundError when bundle is missing."""
        get_template_object_mock.return_value = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            "parameterDefinitions": [
                {"name": "CondaPackages", "type": "STRING", "default": "unrealengine=5.7"},
            ],
        }
        mock_bundle_dir.return_value = None

        job = RenderUnrealOpenJob(name="TestJob")
        with pytest.raises(FileNotFoundError, match="Adaptor bundle directory not found"):
            job.create_job_bundle()

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
        "UnrealOpenJob.create_job_bundle"
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
        "RenderUnrealOpenJob._get_adaptor_bundle_dir"
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_calls_super_when_bundle_exists(
        self, get_template_object_mock, mock_bundle_dir, mock_super_create
    ):
        """Verify create_job_bundle delegates to super() when bundle exists."""
        get_template_object_mock.return_value = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            "parameterDefinitions": [
                {"name": "CondaPackages", "type": "STRING", "default": "unrealengine=5.7"},
            ],
        }
        mock_bundle_dir.return_value = "/path/to/adaptor_bundle"
        mock_super_create.return_value = "/path/to/job_bundle"

        job = RenderUnrealOpenJob(name="TestJob")
        result = job.create_job_bundle()

        mock_super_create.assert_called_once()
        assert result == "/path/to/job_bundle"
