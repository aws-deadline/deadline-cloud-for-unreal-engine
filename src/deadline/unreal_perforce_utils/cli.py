#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import argparse
from pathlib import Path

from deadline.unreal_perforce_utils import app


def parse_args():
    argparser = argparse.ArgumentParser('unreal-perforce-utils')
    argparser.add_argument('command', choices=['create_workspace', 'delete_workspace'])
    argparser.add_argument(
        '-UnrealProjectRelativePath', required=False, help='Relative path to the workspace root'
    )
    argparser.add_argument(
        '-PerforceWorkspaceSpecificationTemplate', required=False, help='P4 spec JSON file path'
    )
    argparser.add_argument(
        '-OverriddenWorkspaceRoot', required=False, help='New workspace root to create (Optional)'
    ),
    argparser.add_argument(
        "-ChangelistNumber", type=int, required=False, help='Changelist number to sync to'
    )

    return argparser.parse_args()


def main():

    args = parse_args()

    if args.command == 'create_workspace':
        app.create_workspace(
            perforce_specification_template_path=args.PerforceWorkspaceSpecificationTemplate,
            unreal_project_relative_path=args.UnrealProjectRelativePath,
            overridden_workspace_root=args.OverriddenWorkspaceRoot,
            changelist=args.ChangelistNumber,
        )

    if args.command == 'delete_workspace':
        app.delete_workspace(project_name=Path(args.UnrealProjectRelativePath).stem)


if __name__ == '__main__':
    main()
