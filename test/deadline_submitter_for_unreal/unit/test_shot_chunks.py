import sys
import pytest
from unittest.mock import MagicMock

sys.modules["unreal"] = MagicMock()


class ShotInfoMock:

    def __init__(self, enabled: bool, outer_name: str):
        self.enabled = enabled
        self.outer_name = outer_name


class RenderJobMock:

    def __init__(self, job_name: str, shot_info: list[ShotInfoMock]):
        self.job_name = job_name
        self.shot_info = shot_info


class TestShotChunks:

    @pytest.mark.parametrize(
        "shots_count, enabled_shots_count", [(1, 1), (100, 100), (10, 0), (5, 4), (6, 3)]
    )
    def test_get_enabled_shot_names(self, shots_count: int, enabled_shots_count: int):
        # GIVEN
        enabled_shots = [
            ShotInfoMock(enabled=True, outer_name=f"Enabled{i}") for i in range(enabled_shots_count)
        ]
        disabled_shots = [
            ShotInfoMock(enabled=False, outer_name=f"Disabled{i}")
            for i in range(shots_count - enabled_shots_count)
        ]
        render_job_mock = RenderJobMock(
            job_name="MockedMrqJob", shot_info=enabled_shots + disabled_shots
        )

        # WHEN
        from deadline.unreal_submitter.unreal_open_job.open_job_description import (
            OpenJobDescription,
        )

        enabled_shot_names = OpenJobDescription.get_enabled_shot_names(render_job_mock)

        # THEN
        assert len(enabled_shot_names) == enabled_shots_count
        for enabled_shot in enabled_shots:
            assert enabled_shot.outer_name.startswith("Enabled")

    @pytest.mark.parametrize(
        "chunk_size, shots_count, expected_chunk_id",
        [
            (1, 15, [i for i in range(15)]),
            (2, 15, [i for i in range(8)]),
            (5, 29, [0, 1, 2, 3, 4, 5]),
            (6, 36, [0, 1, 2, 3, 4, 5]),
            (100000, 100, [0]),
        ],
    )
    def test_chunk_size(self, chunk_size: int, shots_count: int, expected_chunk_id: list[int]):

        from deadline.unreal_submitter.unreal_open_job.job_step import RenderJobStep

        render_step = RenderJobStep(
            step_template={
                "parameterSpace": {
                    "taskParameterDefinitions": [
                        {"name": "ChunkSize", "type": "INT"},
                        {"name": "ChunkId", "type": "INT"},
                    ]
                }
            },
            step_settings=MagicMock(),
            host_requirements=MagicMock(),
            queue_manifest_path=MagicMock(),
            shots_count=shots_count,
            task_chunk_size=chunk_size,
        )
        parameters = render_step._job_step["parameterSpace"]["taskParameterDefinitions"]

        chunk_size_param = next((p for p in parameters if p["name"] == "ChunkSize"), None)
        assert chunk_size_param is not None
        assert chunk_size_param["range"][0] == chunk_size

        chunk_id_param = next((p for p in parameters if p["name"] == "ChunkId"), None)
        assert chunk_id_param is not None
        assert chunk_id_param["range"] == expected_chunk_id
