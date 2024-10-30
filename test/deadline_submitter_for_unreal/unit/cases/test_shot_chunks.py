import sys
import unittest
from unittest.mock import patch, MagicMock

from deadline.unreal_submitter.unreal_open_job.job_step import RenderJobStep


class TestShotChunks(unittest.TestCase):

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


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestShotChunks)
    result = unittest.TextTestRunner(stream=sys.stdout, buffer=True).run(suite)
