# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
from unittest.mock import MagicMock, patch

unreal_mock = MagicMock()
unreal_mock.log = MagicMock()
sys.modules["unreal"] = unreal_mock


@pytest.fixture()
def unreal_render_step_handler():
    from deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler import (
        UnrealRenderStepHandler,
    )

    return UnrealRenderStepHandler()


class ShotInfoMock:

    def __init__(self, enabled: bool, outer_name: str, inner_name: str):
        self.enabled = enabled
        self.outer_name = outer_name
        self.inner_name = inner_name


class RenderJobMock:

    def __init__(self, shot_info: list[ShotInfoMock]):
        self.shot_info = shot_info


class TestUnrealRenderStepHandler:

    @pytest.mark.parametrize(
        "shots_count, enabled_shots_count, shots_per_task, task_index",
        [
            (29, 15, 5, 0),
            (29, 29, 5, 1),
            (1, 1, 10, 0),
            (1500, 1, 1501, 0),
            (10, 9, 3, 2),
        ],
    )
    def test_enable_shots_for_task(
        self,
        unreal_render_step_handler,
        shots_count,
        enabled_shots_count,
        shots_per_task,
        task_index,
    ):
        # GIVEN
        enabled_shots = [
            ShotInfoMock(enabled=True, outer_name=f"Enabled{i}", inner_name=f"Enabled{i}")
            for i in range(enabled_shots_count)
        ]
        disabled_shots = [
            ShotInfoMock(enabled=False, outer_name=f"Disabled{i}", inner_name=f"Disabled{i}")
            for i in range(shots_count - enabled_shots_count)
        ]
        render_job_mock = RenderJobMock(shot_info=enabled_shots + disabled_shots)

        enabled_job_shots = [shot for shot in render_job_mock.shot_info if shot.enabled]
        task_shots = enabled_job_shots[
            task_index * shots_per_task : (task_index + 1) * shots_per_task
        ]
        task_shot_names = [shot.outer_name for shot in task_shots]

        # WHEN
        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers."
            "unreal_render_step_handler.logger.info"
        ) as log_mock:
            unreal_render_step_handler.enable_shots_for_task(
                render_job_mock, shots_per_task, task_index
            )

            # THEN
            enabled_shots = [shot for shot in render_job_mock.shot_info if shot.enabled]
            assert all([shot.enabled for shot in enabled_shots])
            assert all([shot.outer_name.startswith("Enabled") for shot in task_shots])
            assert len(enabled_shots) <= shots_per_task and len(enabled_shots) <= shots_count

            disabled_shots = [
                shot for shot in render_job_mock.shot_info if shot.outer_name not in task_shot_names
            ]
            for shot in disabled_shots:
                assert not shot.enabled

            log_mock.assert_called_with(
                f"Shots in task: {[shot.outer_name for shot in enabled_shots]}"
            )


class TestApplyParamAliases:
    """Backwards-compatible run_data key aliasing.

    The adaptor's downstream logic uses the new keys (shots_per_task/task_index).
    For backwards compatibility during the parameter rename it also accepts the
    legacy keys (chunk_size/chunk_id), normalizing them onto the new keys. The
    new keys take precedence when both are present.
    """

    def test_legacy_keys_aliased_to_new(self, unreal_render_step_handler):
        args = {"handler": "render", "chunk_size": 5, "chunk_id": 2}
        unreal_render_step_handler._apply_param_aliases(args)
        assert args["shots_per_task"] == 5
        assert args["task_index"] == 2

    def test_new_keys_untouched_when_no_legacy_keys(self, unreal_render_step_handler):
        args = {"handler": "render", "shots_per_task": 7, "task_index": 3}
        unreal_render_step_handler._apply_param_aliases(args)
        assert args["shots_per_task"] == 7
        assert args["task_index"] == 3
        assert "chunk_size" not in args
        assert "chunk_id" not in args

    def test_new_keys_take_precedence_over_legacy(self, unreal_render_step_handler):
        # If both are present (e.g. a hand-edited template), the new keys win.
        args = {
            "handler": "render",
            "shots_per_task": 5,
            "task_index": 2,
            "chunk_size": 99,
            "chunk_id": 88,
        }
        unreal_render_step_handler._apply_param_aliases(args)
        assert args["shots_per_task"] == 5
        assert args["task_index"] == 2

    def test_partial_legacy_keys_each_aliased_independently(self, unreal_render_step_handler):
        # Only one legacy key present — it should be aliased, the new key that
        # is already present left as-is.
        args = {"handler": "render", "chunk_size": 4, "task_index": 1}
        unreal_render_step_handler._apply_param_aliases(args)
        assert args["shots_per_task"] == 4
        assert args["task_index"] == 1

    def test_no_partitioning_keys_is_noop(self, unreal_render_step_handler):
        args = {"handler": "render"}
        unreal_render_step_handler._apply_param_aliases(args)
        assert args == {"handler": "render"}

    def test_returns_same_dict(self, unreal_render_step_handler):
        args = {"handler": "render", "chunk_size": 1}
        assert unreal_render_step_handler._apply_param_aliases(args) is args
