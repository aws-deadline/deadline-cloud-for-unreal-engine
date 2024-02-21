import os
import sys
import unreal
import unittest

sys.path.insert(0, f"{os.path.dirname(__file__)}/cases")

from test_unreal_dependency_collector import TestUnrealDependencyCollector  # noqa: E402
from test_unreal_open_job import TestUnrealOpenJob  # noqa: E402
from test_unreal_submitter import TestUnrealSubmitter  # noqa: E402


if __name__ == "__main__":
    test_results = []

    for test_case in [TestUnrealDependencyCollector, TestUnrealOpenJob, TestUnrealSubmitter]:
        suite = unittest.TestLoader().loadTestsFromTestCase(test_case)
        result = unittest.TextTestRunner(stream=sys.stdout, buffer=True).run(suite)
        test_results.append((test_case.__name__, result))

    for suite, result in test_results:
        unreal.log(
            f"Test Case {suite} result:\n"
            f"Total run: {result.testsRun}\n"
            f"Successful: {result.wasSuccessful()}\n"
            f"Errors: {len(result.errors)}\n"
            f"Failures: {result.failures}\n\n"
        )
