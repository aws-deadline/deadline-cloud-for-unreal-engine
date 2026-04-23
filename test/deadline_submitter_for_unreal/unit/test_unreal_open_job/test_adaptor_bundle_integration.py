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
        bundle_check_pos = setup_script.index("BUNDLE_PATH")
        conda_check_pos = setup_script.index("where unreal-engine-openjd")
        assert (
            bundle_check_pos < conda_check_pos
        ), "Bundle check must come before conda check in AdaptorSetup script"

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
    def test_get_asset_references_raises_when_no_bundle(
        self, get_template_object_mock, mock_bundle_dir, mock_dep_paths, mock_plugins
    ):
        """Verify FileNotFoundError propagates when bundle directory doesn't exist."""
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
        mock_bundle_dir.side_effect = FileNotFoundError("Adaptor bundle directory not found.")
        mock_dep_paths.return_value = []
        mock_plugins.return_value = AssetReferences()

        job = RenderUnrealOpenJob(name="TestJob")

        with pytest.raises(FileNotFoundError):
            job.get_asset_references()


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

    @patch("deadline.unreal_submitter.unreal_open_job.unreal_open_job.Path")
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_raises_when_no_bundle(self, get_template_object_mock, mock_path_cls):
        """Verify FileNotFoundError raised when bundle directory doesn't exist."""
        get_template_object_mock.return_value = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            "parameterDefinitions": [
                {"name": "CondaPackages", "type": "STRING", "default": "unrealengine=5.7"},
            ],
        }

        # Make all candidate paths return is_dir() = False
        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__ = MagicMock(return_value=mock_path_instance)
        mock_path_instance.parent = mock_path_instance
        mock_path_instance.is_dir.return_value = False
        mock_path_cls.return_value = mock_path_instance
        mock_path_cls.cwd.return_value = mock_path_instance

        with pytest.raises(FileNotFoundError):
            RenderUnrealOpenJob._get_adaptor_bundle_dir()

    @patch("deadline.unreal_submitter.unreal_open_job.unreal_open_job.Path")
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_finds_bundle_in_plugin_dir(self, get_template_object_mock, mock_path_cls):
        """Verify bundle found at Content/Python/adaptor_bundle (plugin install path)."""
        get_template_object_mock.return_value = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            "parameterDefinitions": [
                {"name": "CondaPackages", "type": "STRING", "default": "unrealengine=5.7"},
            ],
        }

        # First candidate (plugin path) exists, others don't
        plugin_bundle = MagicMock()
        plugin_bundle.is_dir.return_value = True
        plugin_bundle.resolve.return_value = Path("/plugin/Content/Python/adaptor_bundle")

        other_path = MagicMock()
        other_path.is_dir.return_value = False
        other_path.__truediv__ = MagicMock(return_value=other_path)
        other_path.parent = other_path

        templates_dir = MagicMock()
        templates_dir.parent = MagicMock()
        templates_dir.parent.__truediv__ = MagicMock(return_value=plugin_bundle)
        # For repo root candidate: go up 5 parents
        repo_parent = MagicMock()
        repo_parent.__truediv__ = MagicMock(return_value=other_path)
        templates_dir.parent.parent = MagicMock()
        templates_dir.parent.parent.parent = MagicMock()
        templates_dir.parent.parent.parent.parent = MagicMock()
        templates_dir.parent.parent.parent.parent.parent = repo_parent

        mock_path_cls.return_value = templates_dir
        mock_path_cls.cwd.return_value = other_path

        result = RenderUnrealOpenJob._get_adaptor_bundle_dir()
        assert result == str(Path("/plugin/Content/Python/adaptor_bundle"))

    @patch("deadline.unreal_submitter.unreal_open_job.unreal_open_job.Path")
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_plugin_path_takes_priority_over_repo_root(
        self, get_template_object_mock, mock_path_cls
    ):
        """Verify plugin Content/Python/adaptor_bundle is checked before repo root."""
        get_template_object_mock.return_value = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            "parameterDefinitions": [
                {"name": "CondaPackages", "type": "STRING", "default": "unrealengine=5.7"},
            ],
        }

        # Both plugin and repo root paths exist
        plugin_bundle = MagicMock()
        plugin_bundle.is_dir.return_value = True
        plugin_bundle.resolve.return_value = Path("/plugin/adaptor_bundle")

        repo_bundle = MagicMock()
        repo_bundle.is_dir.return_value = True
        repo_bundle.resolve.return_value = Path("/repo/adaptor_bundle")

        templates_dir = MagicMock()
        templates_dir.parent = MagicMock()
        templates_dir.parent.__truediv__ = MagicMock(return_value=plugin_bundle)
        repo_parent = MagicMock()
        repo_parent.__truediv__ = MagicMock(return_value=repo_bundle)
        templates_dir.parent.parent = MagicMock()
        templates_dir.parent.parent.parent = MagicMock()
        templates_dir.parent.parent.parent.parent = MagicMock()
        templates_dir.parent.parent.parent.parent.parent = repo_parent

        mock_path_cls.return_value = templates_dir
        cwd_path = MagicMock()
        cwd_path.__truediv__ = MagicMock(
            return_value=MagicMock(is_dir=MagicMock(return_value=False))
        )
        mock_path_cls.cwd.return_value = cwd_path

        result = RenderUnrealOpenJob._get_adaptor_bundle_dir()
        # Plugin path should win
        assert result == str(Path("/plugin/adaptor_bundle"))

    @patch("deadline.unreal_submitter.unreal_open_job.unreal_open_job.Path")
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object"
    )
    def test_error_message_is_actionable(self, get_template_object_mock, mock_path_cls):
        """Verify the error message tells the user how to fix it."""
        get_template_object_mock.return_value = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "TestJob",
            "parameterDefinitions": [
                {"name": "CondaPackages", "type": "STRING", "default": "unrealengine=5.7"},
            ],
        }

        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__ = MagicMock(return_value=mock_path_instance)
        mock_path_instance.parent = mock_path_instance
        mock_path_instance.is_dir.return_value = False
        mock_path_cls.return_value = mock_path_instance
        mock_path_cls.cwd.return_value = mock_path_instance

        with pytest.raises(FileNotFoundError, match="build_plugin.py --install"):
            RenderUnrealOpenJob._get_adaptor_bundle_dir()
