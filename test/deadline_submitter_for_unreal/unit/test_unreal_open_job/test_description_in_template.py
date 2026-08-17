# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for the optional Job ``description`` reaching the built OpenJD template.

``UnrealOpenJob`` carries an optional ``description`` populated from the ``UDeadlineCloudJob``
Details panel (which a pre-GUI hook may have pre-populated) via :meth:`from_data_asset`. These
tests cover the DCC-owned piece: a set description flows into the template dict handed to openjd,
an unset one is omitted, and ``serialize_template`` preserves the key ordering.
"""

import sys
from unittest.mock import MagicMock, patch

from test.deadline_submitter_for_unreal import fixtures

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (  # noqa: E402
    RenderUnrealOpenJob,
    UnrealOpenJob,
    UnrealOpenJobParameterDefinition,
)

_JOB_SHARED_SETTINGS_PATCH = (
    "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
    "JobSharedSettings.from_u_deadline_cloud_job_shared_settings"
)

_TEMPLATE_PATCH = (
    "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
    "UnrealOpenJobEntity.get_template_object"
)


def _make_job() -> UnrealOpenJob:
    with patch(_TEMPLATE_PATCH, return_value=fixtures.f_job_template_default()):
        return UnrealOpenJob(
            file_path="",
            name="OriginalName",
            extra_parameters=[
                UnrealOpenJobParameterDefinition.from_dict(p)
                for p in fixtures.f_job_template_default()["parameterDefinitions"]
            ],
        )


class TestDescriptionInTemplate:
    """The description set on the Job (from the Details panel) must reach the built template."""

    def test_description_passed_into_built_template(self):
        """A set description is placed into the dict handed to openjd's parse_model."""
        job = _make_job()
        job.description = "rendered by pipeline"

        with (
            patch(_TEMPLATE_PATCH, return_value=fixtures.f_job_template_default()),
            patch(
                "deadline.unreal_submitter.unreal_open_job.unreal_open_job.parse_model"
            ) as parse_model_mock,
        ):
            job._build_template()

        template_dict = parse_model_mock.call_args.kwargs["obj"]
        assert template_dict["description"] == "rendered by pipeline"

    def test_no_description_omits_key_from_built_template(self):
        """With no description, no description key is emitted into the template dict."""
        job = _make_job()

        with (
            patch(_TEMPLATE_PATCH, return_value=fixtures.f_job_template_default()),
            patch(
                "deadline.unreal_submitter.unreal_open_job.unreal_open_job.parse_model"
            ) as parse_model_mock,
        ):
            job._build_template()

        template_dict = parse_model_mock.call_args.kwargs["obj"]
        assert "description" not in template_dict

    def test_description_survives_serialize_template(self):
        """serialize_template keeps the description key (it is in the ordered key list)."""
        import json

        template_json = {
            "specificationVersion": "jobtemplate-2023-09",
            "name": "JobA",
            "description": "kept",
            "parameterDefinitions": [],
            "steps": [{"name": "S"}],
        }
        template = MagicMock()
        template.json.return_value = json.dumps(template_json)

        ordered = UnrealOpenJob.serialize_template(template)

        assert ordered["description"] == "kept"
        # description is ordered right after name
        keys = list(ordered.keys())
        assert keys.index("description") == keys.index("name") + 1


def _data_asset_with_description(description: str) -> MagicMock:
    """A minimal DeadlineCloud(Render)Job data-asset mock whose shared settings carry a description."""
    data_asset = MagicMock()
    data_asset.steps = []
    data_asset.environments = []
    data_asset.get_job_parameters.return_value = []
    data_asset.path_to_template.file_path = ""
    shared_settings = data_asset.job_preset_struct.job_shared_settings
    shared_settings.name = "Untitled"
    shared_settings.description = description
    return data_asset


class TestDescriptionFromDataAsset:
    """The shared ``_description_from_data_asset`` maps the panel value, and BOTH from_data_asset
    paths (base + the RenderUnrealOpenJob override) carry it — the override previously dropped it.
    """

    def test_helper_maps_default_sentinel_to_empty(self):
        ss = MagicMock()
        ss.description = "No description"  # C++ unset sentinel
        assert UnrealOpenJob._description_from_data_asset(ss) == ""

    def test_helper_maps_empty_to_empty(self):
        ss = MagicMock()
        ss.description = ""
        assert UnrealOpenJob._description_from_data_asset(ss) == ""

    def test_helper_passes_real_description_through(self):
        ss = MagicMock()
        ss.description = "populated by pre-GUI hook"
        assert UnrealOpenJob._description_from_data_asset(ss) == "populated by pre-GUI hook"

    def test_render_from_data_asset_carries_description(self):
        """RenderUnrealOpenJob.from_data_asset (the MRQ render path) must emit the panel/hook
        description — its override does not call super(), so it must apply the shared helper."""
        data_asset = _data_asset_with_description("populated by pre-GUI hook")
        with (
            patch(_TEMPLATE_PATCH, return_value=fixtures.f_job_template_default()),
            patch.object(RenderUnrealOpenJob, "render_steps_count", return_value=1),
            patch(_JOB_SHARED_SETTINGS_PATCH, return_value=MagicMock()),
        ):
            job = RenderUnrealOpenJob.from_data_asset(data_asset)

        assert job.description == "populated by pre-GUI hook"

    def test_render_from_data_asset_drops_default_description(self):
        data_asset = _data_asset_with_description("No description")
        with (
            patch(_TEMPLATE_PATCH, return_value=fixtures.f_job_template_default()),
            patch.object(RenderUnrealOpenJob, "render_steps_count", return_value=1),
            patch(_JOB_SHARED_SETTINGS_PATCH, return_value=MagicMock()),
        ):
            job = RenderUnrealOpenJob.from_data_asset(data_asset)

        assert job.description == ""


def _render_job_with_mrq_override(asset_description: str, override_description: str):
    """A RenderUnrealOpenJob seeded with ``asset_description`` (as if from the data asset), then
    handed an MRQ job whose ``preset_overrides`` carry ``override_description``."""
    with (
        patch(_TEMPLATE_PATCH, return_value=fixtures.f_job_template_default()),
        patch(_JOB_SHARED_SETTINGS_PATCH, return_value=MagicMock()),
    ):
        job = RenderUnrealOpenJob(file_path="", name="OriginalName")
        job.description = asset_description

        mrq_job = MagicMock()
        # Skip the extra-parameter override block; keep the preset name at the unset sentinel so
        # only the description path is exercised.
        mrq_job.job_template_overrides.parameters = []
        mrq_job.preset_overrides.job_shared_settings.name = "Untitled"
        mrq_job.preset_overrides.job_shared_settings.description = override_description

        job.mrq_job = mrq_job
    return job


class TestDescriptionFromMrqPresetOverride:
    """On the MRQ render path the description is re-resolved from ``preset_overrides`` alongside
    priority/name/etc. — but, like the name, only when the override actually carries one. The
    default "No description" sentinel is treated as "unset" so the underlying data-asset /
    pre-GUI-hook description is kept rather than cleared (PresetOverrides is a stale snapshot, so a
    description set after the preset was assigned must not be silently erased)."""

    def test_override_description_replaces_asset_description(self):
        job = _render_job_with_mrq_override("asset desc", "override desc")
        assert job.description == "override desc"

    def test_override_default_sentinel_keeps_asset_description(self):
        # Mirror the name handling: the "No description" sentinel is "unset", so the underlying
        # data-asset / pre-GUI-hook description survives rather than being cleared.
        job = _render_job_with_mrq_override("asset desc", "No description")
        assert job.description == "asset desc"
