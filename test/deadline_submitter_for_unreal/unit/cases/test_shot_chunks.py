import sys
import unittest
from unittest.mock import patch, MagicMock

from deadline.unreal_submitter.unreal_open_job.job_step import RenderJobStep


class TestShotChunks(unittest.TestCase):

    @staticmethod
    def helper_test_chunk_size(chunk_size: int, shots_count: int, expected_chunk_id: list[int]):
        render_step = RenderJobStep(
            step_template={
                'parameterSpace': {
                    'taskParameterDefinitions': [
                        {'name': 'ChunkSize', 'type': 'INT'},
                        {'name': 'ChunkId', 'type': 'INT'}
                    ]
                }
            },
            step_settings=MagicMock(),
            host_requirements=MagicMock(),
            queue_manifest_path=MagicMock(),
            shots_count=shots_count,
            task_chunk_size=chunk_size
        )
        parameters = render_step._job_step['parameterSpace']['taskParameterDefinitions']

        chunk_size_param = next((p for p in parameters if p['name'] == 'ChunkSize'), None)
        assert chunk_size_param is not None
        assert chunk_size_param['range'][0] == chunk_size

        chunk_id_param = next((p for p in parameters if p['name'] == 'ChunkId'), None)
        assert chunk_id_param is not None
        assert chunk_id_param['range'] == expected_chunk_id

    def test_chunk_size(self):
        # TODO find better approach on parametrizing unittest.TestCase cases
        #  (pytest.mark.parametrize doesn't work as expected here)
        params_list = [
            (1, 15, [i for i in range(15)]),
            (2, 15, [i for i in range(8)]),
            (5, 29, [0, 1, 2, 3, 4, 5]),
            (6, 36, [0, 1, 2, 3, 4, 5]),
            (100000, 100, [0])
        ]
        for params in params_list:
            TestShotChunks.helper_test_chunk_size(*params)


suite = unittest.TestLoader().loadTestsFromTestCase(TestShotChunks)
result = unittest.TextTestRunner(stream=sys.stdout, buffer=True).run(suite)
