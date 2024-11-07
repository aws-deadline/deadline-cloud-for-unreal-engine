#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import unittest

from deadline.unreal_adaptor.UnrealClient.step_handlers.unreal_render_step_handler import (
    UnrealRenderStepHandler
)


class ShotInfoMock:

    def __init__(self, enabled: bool, outer_name: str):
        self.enabled = enabled
        self.outer_name = outer_name


class RenderJobMock:

    def __init__(self, shot_info: list[ShotInfoMock]):
        self.shot_info = shot_info


class TestUnrealRenderStepHandler(unittest.TestCase):
    def test_enable_shots_by_chunk(self):
        for shots_count, enabled_shots_count, task_chunk_size, task_chunk_id in [
            (29, 15, 5, 0),
            (29, 29, 5, 1),
            (1, 1, 10, 0),
            (1500, 1, 1501, 0),
            (10, 9, 3, 2),

        ]:
            # GIVEN
            enabled_shots = [ShotInfoMock(enabled=True, outer_name=f'Enabled{i}') for i in range(enabled_shots_count)]
            disabled_shots = [ShotInfoMock(enabled=False, outer_name=f'Disabled{i}') for i in range(shots_count - enabled_shots_count)]
            render_job_mock = RenderJobMock(shot_info=enabled_shots + disabled_shots)

            enabled_job_shots = [shot for shot in render_job_mock.shot_info if shot.enabled]
            chunked = enabled_job_shots[task_chunk_id * task_chunk_size: (task_chunk_id + 1) * task_chunk_size]
            chunked_names = [shot.outer_name for shot in chunked]

            # WHEN
            UnrealRenderStepHandler.enable_shots_by_chunk(render_job_mock, task_chunk_size, task_chunk_id)

            # THEN
            enabled_shots = [shot for shot in render_job_mock.shot_info if shot.enabled]
            assert all([shot.enabled for shot in enabled_shots])
            assert all([shot.outer_name.startswith('Enabled') for shot in chunked])
            assert len(enabled_shots) <= task_chunk_size and len(enabled_shots) <= shots_count

            disabled_shots = [shot for shot in render_job_mock.shot_info if shot.outer_name not in chunked_names]
            for shot in disabled_shots:
                assert not shot.enabled


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUnrealRenderStepHandler)
    unittest.TextTestRunner(stream=sys.stdout, buffer=True).run(suite)
