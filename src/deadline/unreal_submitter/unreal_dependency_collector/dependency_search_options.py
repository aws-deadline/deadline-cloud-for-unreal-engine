#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from dataclasses import dataclass, asdict


@dataclass
class DependencySearchOptions:
    """
    A dataclass for storing dependencies search options

    include_hard_package_references (True by default)- Dependencies which are required for correct usage of the source asset, and must be loaded at the same time
    include_soft_package_references (True by default)- Dependencies which don't need to be loaded for the object to be used (i.e. soft object paths)
    include_hard_management_references (True by default)- Reference that says one object directly manages another object, set when Primary Assets manage things explicitly
    include_soft_management_references (True by default)- Indirect management references, these are set through recursion for Primary Assets that manage packages or other primary assets
    include_searchable_names (False by default)- References to specific SearchableNames inside a package
    """

    include_hard_package_references: bool = True
    include_soft_package_references: bool = True
    include_hard_management_references: bool = True
    include_soft_management_references: bool = True
    include_searchable_names: bool = False

    def as_dict(self):
        """
        Represent fields of dataclass as dictionary

        :return: A dictionary from its attributes
        :rtype: dict
        """
        return asdict(self)
