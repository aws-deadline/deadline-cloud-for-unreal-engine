#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import unreal
import unittest
from pathlib import Path

from deadline.unreal_submitter.unreal_dependency_collector import (
    common,
    collector,
    dependency_search_options,
)


UNREAL_PROJECT_DIRECTORY = str(
    Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.get_project_file_path())).parent
).replace("\\", "/")

UNREAL_ASSET_PATH = "/Game/Test/TestLevelSequence"
UNREAL_ASSET_DEPENDENCIES_PATHS = ["/Game/Test/Cube"]


class TestUnrealDependencyCollector(unittest.TestCase):
    def test_dependency_filter_in_game_folder(self):
        for case in [
            ("/Game/Test/MyAsset", True),
            ("/Engine/Basic/Cube", False),
            ("Game/Test/MyAsset", False),
            ("Engine/Game/MyAsset", True),
        ]:
            self.assertEqual(common.DependencyFilters.dependency_in_game_folder(case[0]), case[1])

    def test_os_path_from_unreal_path(self):
        for case in [
            (
                "/Game/Test/TestLevelSequence",
                True,
                f"{UNREAL_PROJECT_DIRECTORY}/Content/Test/TestLevelSequence.uasset",
            ),
            (
                "/Game/Test/TestLevel",
                True,
                f"{UNREAL_PROJECT_DIRECTORY}/Content/Test/TestLevel.umap",
            ),
            ("/Game/JohnDoe", False, f"{UNREAL_PROJECT_DIRECTORY}/Content/JohnDoe.*"),
            ("/Game/JohnDoe", True, f"{UNREAL_PROJECT_DIRECTORY}/Content/JohnDoe.uasset"),
        ]:
            self.assertEqual(common.os_path_from_unreal_path(case[0], with_ext=case[1]), case[2])

    def test_os_abs_from_relative(self):
        for case in [
            (
                "RelativePath/WithoutDiskLetter/test.py",
                f"{UNREAL_PROJECT_DIRECTORY}/RelativePath/WithoutDiskLetter/test.py",
            ),
            ("C:/Users", "C:/Users"),
        ]:
            self.assertEqual(common.os_abs_from_relative(case[0]), case[1])

    def test_search_options_as_dict_representation(self):
        expected_search_options = dict(
            include_hard_package_references=False,
            include_soft_package_references=False,
            include_hard_management_references=False,
            include_soft_management_references=False,
            include_searchable_names=False,
        )

        self.assertEqual(
            dependency_search_options.DependencySearchOptions(
                False, False, False, False, False
            ).as_dict(),
            expected_search_options,
        )

    def test_dependency_collector(self):
        dependency_collector = collector.DependencyCollector()

        dependencies = dependency_collector.collect(
            UNREAL_ASSET_PATH, filter_method=common.DependencyFilters.dependency_in_game_folder
        )

        self.assertEqual(dependencies, UNREAL_ASSET_DEPENDENCIES_PATHS)
        self.assertEqual(len(dependencies), len(UNREAL_ASSET_DEPENDENCIES_PATHS))


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUnrealDependencyCollector)
    unittest.TextTestRunner(stream=sys.stdout, buffer=True).run(suite)
