# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import argparse

from deadline.unreal_perforce_utils import app


def parse_args():
    argparser = argparse.ArgumentParser("unreal-perforce-utils")
    argparser.add_argument(
        "command", choices=["create_workspace", "delete_workspace", "apply_perforce_secrets"]
    )
    argparser.add_argument("-UnrealProjectName", required=False, help="Unreal Project Name")
    argparser.add_argument(
        "-UnrealProjectRelativePath", required=False, help="Relative path to the workspace root"
    )
    argparser.add_argument(
        "-OverriddenWorkspaceRoot", required=False, help="New workspace root to create (Optional)"
    ),
    argparser.add_argument(
        "-PerforceWorkspaceSpecificationTemplate", required=False, help="P4 spec JSON file path"
    )
    argparser.add_argument(
        "-PerforceChangelistNumber", type=str, required=False, help="Changelist number to sync to"
    ),
    argparser.add_argument(
        "-PerforceWorkspaceName", type=str, required=False, help="Perforce workspace name"
    ),
    argparser.add_argument(
        "-MrqJobDependenciesDescriptor",
        type=str,
        required=False,
        help="Job dependencies descriptor file path",
    ),

    return argparser.parse_args()


def main():

    args = parse_args()

    if args.command == "create_workspace":
        app.create_workspace(
            perforce_specification_template_path=args.PerforceWorkspaceSpecificationTemplate,
            unreal_project_relative_path=args.UnrealProjectRelativePath,
            unreal_project_name=args.UnrealProjectName,
            overridden_workspace_root=args.OverriddenWorkspaceRoot,
            changelist=args.PerforceChangelistNumber,
            job_dependencies_descriptor_path=args.MrqJobDependenciesDescriptor,
        )

    if args.command == "delete_workspace":
        app.delete_workspace(
            workspace_name=args.PerforceWorkspaceName, project_name=args.UnrealProjectName
        )

    if args.command == "apply_perforce_secrets":
        app.apply_perforce_secrets()


if __name__ == "__main__":
    main()
