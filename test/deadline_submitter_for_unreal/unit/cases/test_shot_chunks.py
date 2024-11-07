import sys
import unittest
from unittest.mock import MagicMock

from deadline.unreal_submitter.unreal_open_job.job_step import RenderJobStep
from deadline.unreal_submitter.unreal_open_job.open_job_description import OpenJobDescription


class ShotInfoMock:

    def __init__(self, enabled: bool, outer_name: str):
        self.enabled = enabled
        self.outer_name = outer_name


class RenderJobMock:

    def __init__(self, job_name: str, shot_info: list[ShotInfoMock]):
        self.job_name = job_name
        self.shot_info = shot_info


class TestShotChunks(unittest.TestCase):

    def test_get_enabled_shot_names(self):
        for shots_count, enabled_shots_count in [
            (1, 1),
            (100, 100),
            (10, 0),
            (5, 4),
            (6, 3)
        ]:
            # GIVEN
            enabled_shots = [
                ShotInfoMock(enabled=True, outer_name=f"Enabled{i}")
                for i in range(enabled_shots_count)
            ]
            disabled_shots = [
                ShotInfoMock(enabled=False, outer_name=f"Disabled{i}")
                for i in range(shots_count - enabled_shots_count)
            ]
            render_job_mock = RenderJobMock(
                job_name="MockedMrqJob", shot_info=enabled_shots + disabled_shots
            )

            # WHEN
            enabled_shot_names = OpenJobDescription.get_enabled_shot_names(render_job_mock)

            # THEN
            assert len(enabled_shot_names) == enabled_shots_count
            for enabled_shot in enabled_shots:
                assert enabled_shot.outer_name.startswith("Enabled")

    def test_chunk_size(self):
        params_list = [
            (1, 15, [i for i in range(15)]),
            (2, 15, [i for i in range(8)]),
            (5, 29, [0, 1, 2, 3, 4, 5]),
            (6, 36, [0, 1, 2, 3, 4, 5]),
            (100000, 100, [0])
        ]

        for chunk_size, shots_count, expected_chunk_id in params_list:
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


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestShotChunks)
    unittest.TextTestRunner(stream=sys.stdout, buffer=True).run(suite)
