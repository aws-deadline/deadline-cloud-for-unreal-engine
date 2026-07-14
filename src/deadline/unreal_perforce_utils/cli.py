# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import argparse

from deadline.unreal_perforce_utils import app


def parse_args():
    argparser = argparse.ArgumentParser("unreal-perforce-utils")
    argparser.add_argument(
        "command",
        choices=[
            "create_workspace",
            "delete_workspace",
            "apply_perforce_secrets",
            "submit_renders",
            "assemble_shelves",
        ],
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
    argparser.add_argument(
        "-OutputDirectories",
        type=str,
        required=False,
        help=(
            "submit_renders: semicolon-separated list of local directories to "
            "reconcile and submit to Perforce."
        ),
    )
    argparser.add_argument(
        "-ChangelistDescription",
        type=str,
        required=False,
        help="submit_renders: extra text appended to the changelist description.",
    )
    argparser.add_argument(
        "-SubmitMode",
        choices=["", "submit", "shelve"],
        default="",
        required=False,
        help=(
            "submit_renders: empty (default) is a no-op so adding this step to "
            "a template doesn't surprise anyone; 'submit' commits immediately; "
            "'shelve' creates a shelved changelist and emits its number for "
            "downstream tasks to pick up."
        ),
    )
    argparser.add_argument(
        "-DeadlineJobId",
        type=str,
        required=False,
        help=(
            "assemble_shelves: the Deadline job ID whose task shelves should "
            "be aggregated. Defaults to $DEADLINE_JOB_ID which the worker "
            "agent injects."
        ),
    )
    argparser.add_argument(
        "-FinalMode",
        choices=["submit", "shelve"],
        required=False,
        help=(
            "assemble_shelves: what to do with the aggregated CL. 'submit' "
            "commits it; 'shelve' leaves it shelved for review."
        ),
    )

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

    if args.command == "submit_renders":
        if not args.UnrealProjectName:
            raise SystemExit("submit_renders requires -UnrealProjectName")
        if not args.OutputDirectories:
            raise SystemExit("submit_renders requires -OutputDirectories")
        # Semicolon split mirrors how Windows passes path lists; strip empties
        # so trailing separators (e.g. "a;b;") don't produce phantom paths.
        output_dirs = [d for d in args.OutputDirectories.split(";") if d.strip()]
        app.submit_renders(
            unreal_project_name=args.UnrealProjectName,
            output_directories=output_dirs,
            description=args.ChangelistDescription,
            mode=args.SubmitMode,
        )

    if args.command == "assemble_shelves":
        if not args.UnrealProjectName:
            raise SystemExit("assemble_shelves requires -UnrealProjectName")
        if not args.FinalMode:
            raise SystemExit("assemble_shelves requires -FinalMode (submit or shelve)")
        import os as _os

        job_id = args.DeadlineJobId or _os.getenv("DEADLINE_JOB_ID")
        if not job_id:
            raise SystemExit(
                "assemble_shelves requires -DeadlineJobId or the DEADLINE_JOB_ID env var"
            )
        app.assemble_shelves(
            unreal_project_name=args.UnrealProjectName,
            deadline_job_id=job_id,
            final_mode=args.FinalMode,
        )


if __name__ == "__main__":
    main()
