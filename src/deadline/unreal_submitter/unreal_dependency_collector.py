import unreal
from typing import Optional, Callable
from dataclasses import dataclass, asdict

from deadline.unreal_submitter import common
from deadline.unreal_logger import get_logger


logger = get_logger()

asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()


class DependencyFilters:
    """
    Class container that contains methods for filtering dependencies
    """

    @staticmethod
    def dependency_in_game_folder(dependency_path: str) -> bool:
        """Checks if /Game/ exists in passed path

        :param dependency_path: The path to dependency
        :return: True if dependency path in `/Game/`, False otherwise
        :rtype: bool
        """
        return "/Game/" in str(dependency_path)


@dataclass
class DependencyOptions:
    """
    Dataclass which contains the default options for getting the asset dependencies
    """

    include_hard_package_references: bool = True
    include_soft_package_references: bool = True
    include_hard_management_references: bool = True
    include_soft_management_references: bool = True
    include_searchable_names: bool = False

    def as_dict(self):
        """
        Return Dependency Search Options as dictionary

        :return: search options dictionary
        :rtype: dict
        """

        return asdict(self)


class DependencyCollector:
    """
    Helper class to collect asset dependencies recursively.
    """

    def __init__(self):
        self._all_dependencies = list()
        self._missing_dependencies = list()
        self._already_synced = list()

    def collect(
        self,
        asset_path: str,
        dependency_options=DependencyOptions(),
        filter_method: Optional[Callable] = None,
        sync_assets: bool = False,
    ) -> list[str]:
        """The method starts the algorithm for obtaining dependencies on the passed asset

        :param asset_path: Path to the dependency asset to be obtained
        :param dependency_options: Settings for obtaining dependencies.
        :param filter_method: Method by which dependencies will be filtered for synchronization
        :param sync_assets: Whether to sync any found assets or not

        :return: list of collected dependencies (UE paths, start with /Game, etc.)
        :rtype: list[str]
        """

        self._all_dependencies.clear()

        udependency_options = unreal.AssetRegistryDependencyOptions(**dependency_options.as_dict())

        if sync_assets and not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
            self._sync_assets([asset_path])

        _, missing_dependencies = self._get_dependencies(
            asset_path, udependency_options, filter_method
        )
        while missing_dependencies:
            if sync_assets:
                self._sync_assets(missing_dependencies)
            # Anyway extend synced even if source control is not available.
            # In that case first recursion before loop and recursion in loop will run one time
            self._already_synced.extend(missing_dependencies)
            self._missing_dependencies.clear()
            self._all_dependencies.clear()
            _, missing_dependencies = self._get_dependencies(
                asset_path, udependency_options, filter_method
            )

        if sync_assets:
            self._sync_assets(
                list(set([d for d in self._all_dependencies if d not in self._already_synced]))
            )

        return list(set(self._all_dependencies))

    def _get_dependencies(
        self,
        asset_path: str,
        udependency_options: unreal.AssetRegistryDependencyOptions,
        filter_method: Optional[Callable] = None,
    ) -> tuple[list, list]:
        """
        The method recursively all dependencies on the passed asset

        :param asset_path: Path to the dependency asset to be obtained
        :param udependency_options: Settings for obtaining dependencies
        :param filter_method: Method by which dependencies will be filtered for synchronization

        :return: List of all downloaded dependencies and list of missing dependencies
        :rtype: list[str]
        """

        dependencies_raw = (
            asset_registry.get_dependencies(
                package_name=asset_path, dependency_options=udependency_options
            )
            or []
        )

        missing_dependencies = list()
        all_dependencies = list()
        for dependency_raw in dependencies_raw:
            dependency_path = str(dependency_raw)
            does_confirm_filter = filter_method(dependency_path) if filter_method else True
            is_not_collected = dependency_raw not in self._all_dependencies

            if does_confirm_filter and is_not_collected:
                # If Source Control off,
                # last missed deps (synced or not) will be already in synced list.
                # So we don't fall in infinite recursion
                if (
                    not unreal.EditorAssetLibrary.does_asset_exist(dependency_path)
                    and dependency_path not in self._already_synced
                ):
                    missing_dependencies.append(dependency_path)
                else:
                    all_dependencies.append(dependency_path)

        self._all_dependencies.extend(all_dependencies)

        self._missing_dependencies.extend(missing_dependencies)

        for dependency in all_dependencies:
            self._get_dependencies(dependency, udependency_options, filter_method)

        return list(set(self._all_dependencies)), list(set(self._missing_dependencies))

    def _sync_assets(self, asset_paths: list[str]):
        """
        Sync given asset paths via `unreal.SourceControl <https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/SourceControl?application_version=5.3#unreal.SourceControl>`__

        :param asset_paths: List of assets to sync
        """

        if not asset_paths:
            return

        synced = unreal.SourceControl.sync_files(
            [common.os_path_from_unreal_path(path, with_ext=False) for path in asset_paths]
        )

        if not synced:
            logger.info(
                "Failed to complete the synchronization process. Reason: {}".format(
                    unreal.SourceControl.last_error_msg()
                )
            )

        unreal.AssetRegistryHelpers().get_asset_registry().scan_modified_asset_files(asset_paths)
        unreal.AssetRegistryHelpers().get_asset_registry().scan_paths_synchronous(
            asset_paths, True, True
        )
