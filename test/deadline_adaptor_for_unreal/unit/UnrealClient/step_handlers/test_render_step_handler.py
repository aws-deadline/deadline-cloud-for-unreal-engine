#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

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
        "shots_count, enabled_shots_count, task_chunk_size, task_chunk_id",
        [
            (29, 15, 5, 0),
            (29, 29, 5, 1),
            (1, 1, 10, 0),
            (1500, 1, 1501, 0),
            (10, 9, 3, 2),
        ],
    )
    def test_enable_shots_by_chunk(
        self,
        unreal_render_step_handler,
        shots_count,
        enabled_shots_count,
        task_chunk_size,
        task_chunk_id,
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
        chunked = enabled_job_shots[
            task_chunk_id * task_chunk_size : (task_chunk_id + 1) * task_chunk_size
        ]
        chunked_names = [shot.outer_name for shot in chunked]

        # WHEN
        with patch(
            "deadline.unreal_adaptor.UnrealClient.step_handlers."
            "unreal_render_step_handler.logger.info"
        ) as log_mock:
            unreal_render_step_handler.enable_shots_by_chunk(
                render_job_mock, task_chunk_size, task_chunk_id
            )

            # THEN
            enabled_shots = [shot for shot in render_job_mock.shot_info if shot.enabled]
            assert all([shot.enabled for shot in enabled_shots])
            assert all([shot.outer_name.startswith("Enabled") for shot in chunked])
            assert len(enabled_shots) <= task_chunk_size and len(enabled_shots) <= shots_count

            disabled_shots = [
                shot for shot in render_job_mock.shot_info if shot.outer_name not in chunked_names
            ]
            for shot in disabled_shots:
                assert not shot.enabled

            log_mock.assert_called_with(
                f"Shots in task: {[shot.outer_name for shot in enabled_shots]}"
            )
