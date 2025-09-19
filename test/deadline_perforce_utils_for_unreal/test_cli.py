# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from unittest.mock import patch, Mock


class TestUnrealP4UtilsCli:

    def test_parse_args_with_job_dependencies_descriptor(self):
        """Test that the new MrqJobDependenciesDescriptor argument is parsed correctly."""
        # Mock the P4 module to avoid import errors
        with patch.dict("sys.modules", {"P4": Mock()}):
            from deadline.unreal_perforce_utils import cli

            # GIVEN
            test_args = [
                "create_workspace",
                "-PerforceWorkspaceSpecificationTemplate",
                "/path/to/template.json",
                "-UnrealProjectName",
                "TestProject",
                "-MrqJobDependenciesDescriptor",
                "/path/to/deps.json",
            ]

            # WHEN
            with patch("sys.argv", ["cli.py"] + test_args):
                args = cli.parse_args()

            # THEN
            assert args.command == "create_workspace"
            assert args.PerforceWorkspaceSpecificationTemplate == "/path/to/template.json"
            assert args.UnrealProjectName == "TestProject"
            assert args.MrqJobDependenciesDescriptor == "/path/to/deps.json"
