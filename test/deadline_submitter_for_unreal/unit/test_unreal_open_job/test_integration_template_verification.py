# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Integration verification tests for dynamic chunking and legacy templates.

These tests verify that:
1. Dynamic chunking templates (TASK_CHUNKING extension) work end-to-end
2. Legacy templates remain unchanged and continue to work correctly
"""

import sys
import os
import pytest
import yaml
from unittest.mock import MagicMock
from pathlib import Path

# Mock unreal module before importing deadline modules
unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_dynamic_chunking import (  # noqa: E402
    DynamicChunkingHelper,
)


def get_templates_base_path() -> str:
    """Get the base path for OpenJD templates."""
    # Navigate from test directory to src/unreal_plugin/Content/Python/openjd_templates
    # The test file is at: test/deadline_submitter_for_unreal/unit/test_unreal_open_job/
    # We need to go up 4 levels to reach the workspace root
    current_dir = Path(__file__).resolve().parent
    workspace_root = current_dir.parent.parent.parent.parent
    templates_path = (
        workspace_root / "src" / "unreal_plugin" / "Content" / "Python" / "openjd_templates"
    )
    return str(templates_path)


class TestDynamicChunkingTemplateIntegration:
    """
    Integration tests for dynamic chunking templates.
    """

    @pytest.fixture
    def templates_base_path(self):
        """Fixture providing the base path for templates."""
        return get_templates_base_path()

    def test_dynamic_chunking_job_template_has_task_chunking_extension(self, templates_base_path):
        """
        Verify dynamic chunking job template includes TASK_CHUNKING extension.
        """
        # GIVEN - the dynamic chunking job template
        job_template_path = os.path.join(
            templates_base_path, "dynamic_chunking", "dynamic_chunking_render_job.yml"
        )

        # WHEN - we load the template
        with open(job_template_path, "r") as f:
            job_template = yaml.safe_load(f)

        # THEN - it should have TASK_CHUNKING extension
        assert "extensions" in job_template, "Job template should have extensions field"
        assert (
            "TASK_CHUNKING" in job_template["extensions"]
        ), "Job template should include TASK_CHUNKING extension"
        assert (
            "REDACTED_ENV_VARS" in job_template["extensions"]
        ), "Job template should also include REDACTED_ENV_VARS extension"

    def test_dynamic_chunking_job_template_has_frames_parameter(self, templates_base_path):
        """
        Verify dynamic chunking job template includes Frames parameter.
        """
        # GIVEN - the dynamic chunking job template
        job_template_path = os.path.join(
            templates_base_path, "dynamic_chunking", "dynamic_chunking_render_job.yml"
        )

        # WHEN - we load the template
        with open(job_template_path, "r") as f:
            job_template = yaml.safe_load(f)

        # THEN - it should have Frames parameter
        param_names = [p["name"] for p in job_template["parameterDefinitions"]]
        assert "Frames" in param_names, "Job template should have Frames parameter"

        # Verify Frames parameter is STRING type for expression passthrough
        frames_param = next(
            p for p in job_template["parameterDefinitions"] if p["name"] == "Frames"
        )
        assert frames_param["type"] == "STRING", "Frames parameter should be STRING type"

    def test_dynamic_chunking_job_template_has_chunking_parameters(self, templates_base_path):
        """
        Verify dynamic chunking job template includes chunking configuration parameters
        (ChunkSize, TargetRuntimeSeconds).
        """
        # GIVEN - the dynamic chunking job template
        job_template_path = os.path.join(
            templates_base_path, "dynamic_chunking", "dynamic_chunking_render_job.yml"
        )

        # WHEN - we load the template
        with open(job_template_path, "r") as f:
            job_template = yaml.safe_load(f)

        # THEN - it should have all chunking parameters
        param_names = [p["name"] for p in job_template["parameterDefinitions"]]

        assert "ChunkSize" in param_names, "Job template should have ChunkSize parameter"
        assert (
            "TargetRuntimeSeconds" in param_names
        ), "Job template should have TargetRuntimeSeconds parameter"

        # Verify ChunkSize has correct constraints
        chunk_size_param = next(
            p for p in job_template["parameterDefinitions"] if p["name"] == "ChunkSize"
        )
        assert chunk_size_param["type"] == "INT", "ChunkSize should be INT type"
        assert chunk_size_param.get("minValue", 0) >= 1 or chunk_size_param.get("default", 0) >= 1

        # Verify TargetRuntimeSeconds
        target_runtime_param = next(
            p for p in job_template["parameterDefinitions"] if p["name"] == "TargetRuntimeSeconds"
        )
        assert target_runtime_param["type"] == "INT", "TargetRuntimeSeconds should be INT type"
        assert target_runtime_param.get("default") == 0, "TargetRuntimeSeconds should default to 0"
        assert (
            target_runtime_param.get("minValue", 0) >= 0
        ), "TargetRuntimeSeconds minValue should be >= 0"

    def test_dynamic_chunking_job_template_uses_current_conda_defaults(self, templates_base_path):
        """
        Verify dynamic chunking job template uses the current CondaPackages pin and
        CondaChannels defaults. Dynamic chunking requires an adaptor that understands
        the dynamic_chunked_frames run_data key, so the pin must be at least 0.7.*.
        """
        # GIVEN - the dynamic chunking job template
        job_template_path = os.path.join(
            templates_base_path, "dynamic_chunking", "dynamic_chunking_render_job.yml"
        )

        # WHEN - we load the template
        with open(job_template_path, "r") as f:
            job_template = yaml.safe_load(f)

        # THEN - CondaPackages pin should reference the 0.7.* adaptor line
        conda_packages_param = next(
            p for p in job_template["parameterDefinitions"] if p["name"] == "CondaPackages"
        )
        assert "unrealengine-openjd=0.7.*" in conda_packages_param["default"]
        assert "unrealengine-openjd=0.6.*" not in conda_packages_param["default"]

        # AND - CondaChannels should include the current deadline-cloud-v2 channel
        conda_channels_param = next(
            p for p in job_template["parameterDefinitions"] if p["name"] == "CondaChannels"
        )
        assert "deadline-cloud-v2" in conda_channels_param["default"]

    def test_dynamic_chunking_step_template_has_chunk_int_parameter(self, templates_base_path):
        """
        Verify dynamic chunking step template contains CHUNK[INT] task parameter
        with the chunks configuration structure preserved.
        """
        # GIVEN - the dynamic chunking step template
        step_template_path = os.path.join(
            templates_base_path, "dynamic_chunking", "dynamic_chunking_render_step.yml"
        )

        # WHEN - we load the template
        with open(step_template_path, "r") as f:
            step_template = yaml.safe_load(f)

        # THEN - it should have CHUNK[INT] task parameter
        task_params = step_template["parameterSpace"]["taskParameterDefinitions"]
        chunk_params = [p for p in task_params if p.get("type") == "CHUNK[INT]"]

        assert len(chunk_params) == 1, "Step template should have exactly one CHUNK[INT] parameter"

        chunk_param = chunk_params[0]
        assert (
            chunk_param["name"] == "DynamicChunking"
        ), "CHUNK[INT] parameter should be named DynamicChunking"

        # Verify chunks configuration exists with all required fields
        assert "chunks" in chunk_param, "CHUNK[INT] parameter should have chunks configuration"
        chunks_config = chunk_param["chunks"]

        assert "defaultTaskCount" in chunks_config, "chunks config should have defaultTaskCount"
        assert (
            "targetRuntimeSeconds" in chunks_config
        ), "chunks config should have targetRuntimeSeconds"
        assert "rangeConstraint" in chunks_config, "chunks config should have rangeConstraint"

    def test_dynamic_chunking_detection_works_on_step_template(self, templates_base_path):
        """
        Verify DynamicChunkingHelper correctly detects CHUNK[INT] in step template.
        """
        # GIVEN - the dynamic chunking step template
        step_template_path = os.path.join(
            templates_base_path, "dynamic_chunking", "dynamic_chunking_render_step.yml"
        )

        with open(step_template_path, "r") as f:
            step_template = yaml.safe_load(f)

        # WHEN - we check if it uses dynamic chunking
        uses_dynamic_chunking = DynamicChunkingHelper.is_using_dynamic_chunking(step_template)

        # THEN - it should be detected as using dynamic chunking
        assert (
            uses_dynamic_chunking is True
        ), "Dynamic chunking step template should be detected as using dynamic chunking"

    def test_dynamic_chunking_step_template_uses_template_references(self, templates_base_path):
        """
        Verify dynamic chunking step template uses template references for parameter values.

        This ensures frame range expressions and chunking parameters are passed through
        from job parameters to the step template.
        """
        # GIVEN - the dynamic chunking step template
        step_template_path = os.path.join(
            templates_base_path, "dynamic_chunking", "dynamic_chunking_render_step.yml"
        )

        with open(step_template_path, "r") as f:
            step_template = yaml.safe_load(f)

        # WHEN - we examine the CHUNK[INT] parameter
        task_params = step_template["parameterSpace"]["taskParameterDefinitions"]
        chunk_param = next(p for p in task_params if p.get("type") == "CHUNK[INT]")

        # THEN - it should use template references
        assert (
            chunk_param["range"] == "{{Param.Frames}}"
        ), "CHUNK[INT] range should reference Frames parameter"

        chunks_config = chunk_param["chunks"]
        assert (
            chunks_config["defaultTaskCount"] == "{{Param.ChunkSize}}"
        ), "defaultTaskCount should reference ChunkSize parameter"
        assert (
            chunks_config["targetRuntimeSeconds"] == "{{Param.TargetRuntimeSeconds}}"
        ), "targetRuntimeSeconds should reference TargetRuntimeSeconds parameter"
        # rangeConstraint is hardcoded to CONTIGUOUS (not a template reference)
        assert (
            chunks_config["rangeConstraint"] == "CONTIGUOUS"
        ), "rangeConstraint should be hardcoded to CONTIGUOUS"

    def test_dynamic_chunking_step_template_uses_current_run_data_wiring(self, templates_base_path):
        """
        Verify dynamic chunking step template wires Handler/QueueManifestPath and
        dynamic_chunked_frames into run data using the current conventions.
        """
        # GIVEN - the dynamic chunking step template
        step_template_path = os.path.join(
            templates_base_path, "dynamic_chunking", "dynamic_chunking_render_step.yml"
        )

        with open(step_template_path, "r") as f:
            step_template = yaml.safe_load(f)

        # WHEN - we examine the script's embedded files
        embedded_files = step_template["script"]["embeddedFiles"]
        run_data_file = next(f for f in embedded_files if f["name"] == "runData")

        # THEN - run data should reference the current keys
        assert "handler: {{Task.Param.Handler}}" in run_data_file["data"]
        assert "queue_manifest_path: {{Task.Param.QueueManifestPath}}" in run_data_file["data"]
        assert "dynamic_chunked_frames: {{Task.Param.DynamicChunking}}" in run_data_file["data"]
        # AND - it should NOT carry the legacy/static chunking keys
        assert "task_index:" not in run_data_file["data"]
        assert "shots_per_task:" not in run_data_file["data"]
        assert "frames_per_task:" not in run_data_file["data"]


class TestLegacyTemplateIntegration:
    """
    Integration tests for legacy (non-dynamic-chunking) templates.
    """

    @pytest.fixture
    def templates_base_path(self):
        """Fixture providing the base path for templates."""
        return get_templates_base_path()

    def test_legacy_job_template_does_not_have_task_chunking_extension(self, templates_base_path):
        """
        Verify legacy job template does NOT include TASK_CHUNKING extension.
        """
        # GIVEN - the legacy render job template
        job_template_path = os.path.join(templates_base_path, "render_job.yml")

        # WHEN - we load the template
        with open(job_template_path, "r") as f:
            job_template = yaml.safe_load(f)

        # THEN - it should NOT have TASK_CHUNKING extension
        extensions = job_template.get("extensions", [])
        assert (
            "TASK_CHUNKING" not in extensions
        ), "Legacy job template should NOT include TASK_CHUNKING extension"

    def test_legacy_step_template_has_task_index_parameter(self, templates_base_path):
        """
        Verify legacy step template uses TaskIndex INT parameter (not CHUNK[INT]).
        """
        # GIVEN - the legacy render step template
        step_template_path = os.path.join(templates_base_path, "render_step.yml")

        # WHEN - we load the template
        with open(step_template_path, "r") as f:
            step_template = yaml.safe_load(f)

        # THEN - it should have TaskIndex INT parameter (not CHUNK[INT])
        task_params = step_template["parameterSpace"]["taskParameterDefinitions"]

        # Should have TaskIndex parameter
        task_index_params = [p for p in task_params if p["name"] == "TaskIndex"]
        assert len(task_index_params) == 1, "Legacy template should have TaskIndex parameter"

        task_index_param = task_index_params[0]
        assert task_index_param["type"] == "INT", "TaskIndex should be INT type (not CHUNK[INT])"

        # Should NOT have any CHUNK[INT] parameters
        chunk_int_params = [p for p in task_params if p.get("type") == "CHUNK[INT]"]
        assert (
            len(chunk_int_params) == 0
        ), "Legacy template should NOT have any CHUNK[INT] parameters"

    def test_legacy_step_template_not_detected_as_dynamic_chunking(self, templates_base_path):
        """
        Verify DynamicChunkingHelper correctly identifies legacy template as NOT using
        dynamic chunking.
        """
        # GIVEN - the legacy render step template
        step_template_path = os.path.join(templates_base_path, "render_step.yml")

        with open(step_template_path, "r") as f:
            step_template = yaml.safe_load(f)

        # WHEN - we check if it uses dynamic chunking
        uses_dynamic_chunking = DynamicChunkingHelper.is_using_dynamic_chunking(step_template)

        # THEN - it should NOT be detected as using dynamic chunking
        assert (
            uses_dynamic_chunking is False
        ), "Legacy step template should NOT be detected as using dynamic chunking"

    def test_legacy_job_template_has_shots_per_task_parameter(self, templates_base_path):
        """
        Verify legacy job template has ShotsPerTask parameter for shot-based chunking.
        """
        # GIVEN - the legacy render job template
        job_template_path = os.path.join(templates_base_path, "render_job.yml")

        # WHEN - we load the template
        with open(job_template_path, "r") as f:
            job_template = yaml.safe_load(f)

        # THEN - it should have ShotsPerTask parameter
        param_names = [p["name"] for p in job_template["parameterDefinitions"]]
        assert (
            "ShotsPerTask" in param_names
        ), "Legacy job template should have ShotsPerTask parameter for shot-based chunking"

    def test_legacy_step_template_uses_task_index_in_run_data(self, templates_base_path):
        """
        Verify legacy step template references task_index in run data.

        This confirms the legacy template structure is preserved for backward compatibility.
        """
        # GIVEN - the legacy render step template
        step_template_path = os.path.join(templates_base_path, "render_step.yml")

        with open(step_template_path, "r") as f:
            step_template = yaml.safe_load(f)

        # WHEN - we examine the script's embedded files
        embedded_files = step_template["script"]["embeddedFiles"]
        run_data_file = next(f for f in embedded_files if f["name"] == "runData")

        # THEN - run data should reference task_index
        assert (
            "task_index: {{Task.Param.TaskIndex}}" in run_data_file["data"]
        ), "Legacy template run data should reference TaskIndex task parameter"
        assert (
            "shots_per_task: {{Param.ShotsPerTask}}" in run_data_file["data"]
        ), "Legacy template run data should reference ShotsPerTask job parameter"


class TestTemplateStructureComparison:
    """
    Tests comparing dynamic chunking and legacy template structures.

    Ensures both template types maintain their distinct characteristics.
    """

    @pytest.fixture
    def templates_base_path(self):
        """Fixture providing the base path for templates."""
        return get_templates_base_path()

    def test_both_templates_have_same_base_structure(self, templates_base_path):
        """
        Verify both template types share common base structure elements.
        """
        # Load both step templates
        dynamic_step_path = os.path.join(
            templates_base_path, "dynamic_chunking", "dynamic_chunking_render_step.yml"
        )
        legacy_step_path = os.path.join(templates_base_path, "render_step.yml")

        with open(dynamic_step_path, "r") as f:
            dynamic_template = yaml.safe_load(f)
        with open(legacy_step_path, "r") as f:
            legacy_template = yaml.safe_load(f)

        # Both should have same base structure
        assert "name" in dynamic_template and "name" in legacy_template
        assert "parameterSpace" in dynamic_template and "parameterSpace" in legacy_template
        assert "script" in dynamic_template and "script" in legacy_template

        # Both should have Handler and QueueManifestPath parameters
        dynamic_param_names = [
            p["name"] for p in dynamic_template["parameterSpace"]["taskParameterDefinitions"]
        ]
        legacy_param_names = [
            p["name"] for p in legacy_template["parameterSpace"]["taskParameterDefinitions"]
        ]

        assert "Handler" in dynamic_param_names and "Handler" in legacy_param_names
        assert (
            "QueueManifestPath" in dynamic_param_names and "QueueManifestPath" in legacy_param_names
        )

    def test_templates_differ_in_chunking_approach(self, templates_base_path):
        """
        Verify templates use different chunking approaches.
        """
        # Load both step templates
        dynamic_step_path = os.path.join(
            templates_base_path, "dynamic_chunking", "dynamic_chunking_render_step.yml"
        )
        legacy_step_path = os.path.join(templates_base_path, "render_step.yml")

        with open(dynamic_step_path, "r") as f:
            dynamic_template = yaml.safe_load(f)
        with open(legacy_step_path, "r") as f:
            legacy_template = yaml.safe_load(f)

        dynamic_params = dynamic_template["parameterSpace"]["taskParameterDefinitions"]
        legacy_params = legacy_template["parameterSpace"]["taskParameterDefinitions"]

        # Dynamic template should have CHUNK[INT], legacy should have INT TaskIndex
        dynamic_types = {p["name"]: p["type"] for p in dynamic_params}
        legacy_types = {p["name"]: p["type"] for p in legacy_params}

        assert "DynamicChunking" in dynamic_types
        assert dynamic_types["DynamicChunking"] == "CHUNK[INT]"

        assert "TaskIndex" in legacy_types
        assert legacy_types["TaskIndex"] == "INT"

        # Dynamic should NOT have TaskIndex, legacy should NOT have DynamicChunking
        assert "TaskIndex" not in dynamic_types
        assert "DynamicChunking" not in legacy_types
