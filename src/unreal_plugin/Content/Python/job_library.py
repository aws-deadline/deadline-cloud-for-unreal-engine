import os

import unreal

from deadline.unreal_submitter.common import soft_obj_path_to_str
from deadline.unreal_submitter.unreal_dependency_collector.collector import DependencyCollector
from deadline.unreal_submitter.unreal_dependency_collector.common import (
    DependencyFilters,
    os_path_from_unreal_path,
)

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.


@unreal.uclass()
class DeadlineCloudJobBundleLibraryImplementation(unreal.DeadlineCloudJobBundleLibrary):
    @unreal.ufunction(override=True)
    def get_job_dependencies(self, mrq_job):
        level_sequence_path = soft_obj_path_to_str(mrq_job.sequence)
        level_path = soft_obj_path_to_str(mrq_job.map)

        level_sequence_path, _ = os.path.splitext(level_sequence_path)
        level_path, _ = os.path.splitext(level_path)

        dependency_collector = DependencyCollector()
        unreal.log("Level sequence: " + level_sequence_path)
        unreal.log("Level: " + level_path)

        unreal_dependencies = dependency_collector.collect(
            asset_path=level_sequence_path,
            filter_method=DependencyFilters.dependency_in_game_folder,
        )

        unreal_dependencies += dependency_collector.collect(
            asset_path=level_path, filter_method=DependencyFilters.dependency_in_game_folder
        )

        unreal_dependencies += [level_sequence_path, level_path]

        unreal.log(
            f"Converted level path: {os_path_from_unreal_path(level_sequence_path, with_ext=True)}"
        )

        unreal_dependencies = list(set(unreal_dependencies))

        return [os_path_from_unreal_path(d, with_ext=True) for d in unreal_dependencies]

    @unreal.ufunction(override=True)
    def get_cpu_architectures(self):
        return ["x86_64", "arm64"]

    @unreal.ufunction(override=True)
    def get_operating_systems(self):
        return ["linux", "macos", "windows"]

    @unreal.ufunction(override=True)
    def get_job_initial_state_options(self):
        return ["READY", "SUSPENDED"]
