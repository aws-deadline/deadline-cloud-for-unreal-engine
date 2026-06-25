# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
from unittest.mock import patch, Mock, MagicMock
from openjd.model import parse_model
from openjd.model.v2023_09 import (
    JobTemplate,
    StepTemplate,
    StepScript,
    StepActions,
    Environment,
    Action,
    CommandString,
    EnvironmentVariableValueString,
    CancelationMethodNotifyThenTerminate,
    CancelationMode,
    ExtensionName,
)

from deadline.client.job_bundle.submission import AssetReferences

from test.deadline_submitter_for_unreal import fixtures

NoneType = type(None)

unreal_mock = MagicMock()
sys.modules["unreal"] = unreal_mock

from deadline.unreal_submitter.unreal_open_job.unreal_open_job import (  # noqa: E402
    UnrealOpenJob,
    RenderUnrealOpenJob,
    UgsUnrealOpenJobEnvironment,
    UnrealOpenJobParameterDefinition,
    TransferProjectFilesStrategy,
)
from deadline.unreal_submitter import exceptions  # noqa: E402


class TestUnrealOpenJobStepParameterDefinition:

    @pytest.mark.parametrize(
        "name, param_type, value, expected_python_type",
        [
            ("test", "INT", "1", int),
            ("test", "FLOAT", "1.0", float),
            ("test", "STRING", "foo", str),
            ("test", "PATH", "path/to/file", str),
            ("test", "INT", None, NoneType),
        ],
    )
    def test_from_unreal_param_definition(self, name, param_type, value, expected_python_type):
        # GIVEN
        u_param = MagicMock()
        u_param.name = name
        u_param.type.name = param_type
        u_param.value = value

        # WHEN
        param = UnrealOpenJobParameterDefinition.from_unreal_param_definition(u_param)

        # THEN
        assert param.name == name
        assert param.type == param_type
        assert isinstance(param.value, expected_python_type)

    @pytest.mark.parametrize(
        "name, param_type, default, expected_type",
        [
            ("test", "INT", 1, int),
            ("test", "FLOAT", 1.0, float),
            ("test", "STRING", "foo", str),
            ("test", "PATH", "path/to/file", str),
            ("test", "INT", None, NoneType),
        ],
    )
    def test_from_dict(self, name, param_type, default, expected_type):
        # GIVEN
        param_dict = dict(name=name, type=param_type)
        if default is not None:
            param_dict["default"] = default

        # WHEN
        param = UnrealOpenJobParameterDefinition.from_dict(param_dict)

        # THEN
        assert param.name == name
        assert param.type == param_type
        assert isinstance(param.value, expected_type)


class TestUnrealOpenJob:

    @pytest.mark.parametrize(
        "existed_param, requested_param, found",
        [
            (("ExistedParam", "INT"), ("ExistedParam", "INT"), True),
            (("ExistedParam", "INT"), ("NotExistedParam", "INT"), False),
            (("ExistedParam", "INT"), ("ExistedParam", "FLOAT"), False),
        ],
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value=fixtures.f_job_template_default(),
    )
    def test__find_extra_parameter(
        self, get_template_object_mock, existed_param, requested_param, found
    ):
        # GIVEN
        job = UnrealOpenJob(
            file_path="",
            name="JobA",
            extra_parameters=[UnrealOpenJobParameterDefinition(existed_param[0], existed_param[1])],
        )

        # WHEN
        param = job._find_extra_parameter(
            parameter_name=requested_param[0], parameter_type=requested_param[1]
        )

        # THEN
        assert isinstance(param, UnrealOpenJobParameterDefinition) == found

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.SystemLibrary.get_engine_version",
        return_value="5.4",
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value=fixtures.f_job_template_default(),
    )
    def test__build_parameter_values(
        self, get_engine_version: Mock, get_template_object_mock: Mock
    ):
        # GIVEN
        yaml_parameters = fixtures.f_job_template_default()["parameterDefinitions"]
        open_job = UnrealOpenJob(
            file_path="",
            name="JobA",
            extra_parameters=[
                UnrealOpenJobParameterDefinition.from_dict(p) for p in yaml_parameters
            ],
        )

        # WHEN
        parameter_values = open_job._build_parameter_values()

        # THEN
        for p in yaml_parameters:
            assert p["name"], p.get("default") in [
                (p["name"], p["value"]) for p in parameter_values
            ]

    @patch("builtins.open", MagicMock())
    @patch("yaml.safe_load", MagicMock(side_effect=[fixtures.f_job_template_default()]))
    def test__check_parameter_consistency_passed(self):
        # GIVEN
        yaml_parameters = fixtures.f_job_template_default()["parameterDefinitions"]
        open_job = UnrealOpenJob(
            file_path="",
            name="JobA",
            extra_parameters=[
                UnrealOpenJobParameterDefinition.from_dict(p) for p in yaml_parameters
            ],
        )

        # WHEN
        consistency_check_result = open_job._check_parameters_consistency()

        # THEN
        assert consistency_check_result.passed
        assert "Parameters are consistent" in consistency_check_result.reason

    yaml_template = fixtures.f_job_template_default()
    yaml_template["parameterDefinitions"] = []

    @patch("builtins.open", MagicMock())
    @patch("yaml.safe_load", MagicMock(side_effect=[yaml_template]))
    def test__check_parameters_consistency_failed_yaml(self):
        # GIVEN
        open_job = UnrealOpenJob(
            file_path="",
            name="JobA",
            extra_parameters=[
                UnrealOpenJobParameterDefinition.from_dict(p)
                for p in fixtures.f_job_template_default()["parameterDefinitions"]
            ],
        )

        # WHEN
        consistency_check_result = open_job._check_parameters_consistency()

        # THEN
        assert not consistency_check_result.passed
        assert "Data Asset's parameters missed in YAML" in consistency_check_result.reason

    @patch("builtins.open", MagicMock())
    @patch("yaml.safe_load", MagicMock(side_effect=[fixtures.f_job_template_default()]))
    def test__check_parameters_consistency_failed_data_asset(self):
        # GIVEN
        open_job = UnrealOpenJob(file_path="", name="JobA", extra_parameters=[])

        # WHEN
        consistency_check_result = open_job._check_parameters_consistency()

        # THEN
        assert not consistency_check_result.passed
        assert "YAML's parameters missed in Data Asset" in consistency_check_result.reason

    yaml_template = fixtures.f_job_template_default()
    yaml_template["parameterDefinitions"] = [{"name": "ParamD", "type": "FLOAT", "value": 1.0}]

    @patch("builtins.open", MagicMock())
    @patch("yaml.safe_load", MagicMock(side_effect=[yaml_template]))
    def test__check_parameters_consistency_failed_same_parameters_different_types(self):
        # GIVEN
        extra_param = {"name": "ParamD", "type": "INT", "value": 1}
        openjd_step = UnrealOpenJob(
            file_path="",
            name="JobA",
            extra_parameters=[UnrealOpenJobParameterDefinition.from_dict(extra_param)],
        )

        # WHEN
        consistency_check_result = openjd_step._check_parameters_consistency()

        # THEN
        assert not consistency_check_result.passed
        assert "YAML's parameters missed in Data Asset" in consistency_check_result.reason
        assert "Data Asset's parameters missed in YAML" in consistency_check_result.reason

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={
            "parameterDefinitions": fixtures.f_job_template_default()["parameterDefinitions"]
        },
    )
    def test__build_template(self, get_template_object_mock):
        # GIVEN
        step_mock = MagicMock()
        step_build_template_mock = MagicMock()
        step_build_template_mock.return_value = StepTemplate(
            name="StepA",
            script=StepScript(
                actions=StepActions(
                    onRun=Action(
                        command=CommandString("echo hello world"),
                        cancelation=CancelationMethodNotifyThenTerminate(
                            mode=CancelationMode.NOTIFY_THEN_TERMINATE
                        ),
                    )
                )
            ),
        )
        step_mock.build_template = step_build_template_mock

        env_mock = MagicMock()
        env_build_template_mock = MagicMock()
        env_build_template_mock.return_value = Environment(
            name="EnvironmentA", variables={"VARIABLE_A": EnvironmentVariableValueString("VALUE_A")}
        )
        env_mock.build_template = env_build_template_mock

        open_job = UnrealOpenJob(
            file_path="",
            name="JobA",
            steps=[step_mock],
            environments=[env_mock],
            extra_parameters=[
                UnrealOpenJobParameterDefinition.from_dict(p)
                for p in fixtures.f_job_template_default()["parameterDefinitions"]
            ],
        )

        # WHEN
        openjd_template = open_job._build_template()

        # THEN
        assert isinstance(openjd_template, JobTemplate)
        get_template_object_mock.assert_called()
        step_build_template_mock.assert_called()
        env_build_template_mock.assert_called()

    @pytest.mark.parametrize(
        "param_name, param_value, new_param_name, new_param_value, updated",
        [
            ("ParamInt", 1, "ParamInt", 2, True),
            ("ParamString", "foo", "ParamString2", "bar", False),
        ],
    )
    def test_update_job_parameter_values_existed(
        self, param_name, param_value, new_param_name, new_param_value, updated
    ):
        # GIVEN
        job_parameter_values = [dict(name=param_name, value=param_value)]
        values_before_update = [p["value"] for p in job_parameter_values]

        # WHEN
        job_parameter_values = RenderUnrealOpenJob.update_job_parameter_values(
            job_parameter_values=job_parameter_values,
            job_parameter_name=new_param_name,
            job_parameter_value=new_param_value,
        )
        values_after_update = [p["value"] for p in job_parameter_values]

        # THEN
        assert (values_after_update != values_before_update) == updated

    @pytest.mark.parametrize(
        "steps, environments, expected_keys",
        [
            (
                [fixtures.f_step_template_default()],
                [fixtures.f_environment_template_default()],
                [
                    "specificationVersion",
                    "name",
                    "parameterDefinitions",
                    "jobEnvironments",
                    "steps",
                ],
            ),
            (
                [fixtures.f_step_template_default()],
                [],
                [
                    "specificationVersion",
                    "name",
                    "parameterDefinitions",
                    "steps",
                ],
            ),
        ],
    )
    def test_serialize_template(self, steps, environments, expected_keys):
        # GIVEN
        job_template_dict = fixtures.f_job_template_default()
        if steps:
            job_template_dict["steps"] = steps
        if environments:
            job_template_dict["jobEnvironments"] = environments
        job_template = parse_model(model=JobTemplate, obj=job_template_dict)

        # WHEN
        serialized = UnrealOpenJob.serialize_template(job_template)

        # THEN
        assert isinstance(serialized, dict)
        assert list(serialized.keys()) == expected_keys

    @pytest.mark.parametrize(
        "steps, environments, expected_keys",
        [
            (
                [fixtures.f_step_template_default()],
                [fixtures.f_environment_template_default()],
                [
                    "specificationVersion",
                    "extensions",
                    "name",
                    "parameterDefinitions",
                    "jobEnvironments",
                    "steps",
                ],
            ),
        ],
    )
    def test_serialize_template_extension(self, steps, environments, expected_keys):
        # GIVEN
        extension_list = ["REDACTED_ENV_VARS"]
        job_template_dict = fixtures.f_job_template_default()
        job_template_dict["extensions"] = extension_list
        job_template_dict["steps"] = steps
        job_template_dict["jobEnvironments"] = environments

        supported_extensions = [extension.value for extension in ExtensionName]
        job_template = parse_model(
            model=JobTemplate, obj=job_template_dict, supported_extensions=supported_extensions
        )

        # WHEN
        serialized = UnrealOpenJob.serialize_template(job_template)

        # THEN
        assert isinstance(serialized, dict)
        assert list(serialized.keys()) == expected_keys
        assert serialized["extensions"] == extension_list

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value=fixtures.f_job_template_default(),
    )
    def test_get_asset_references(self, get_template_object_mock):
        # GIVEN
        job_asset_references = AssetReferences(input_filenames={"job_ref"})
        step_asset_references = AssetReferences(input_filenames={"step_ref"})
        environment_asset_references = AssetReferences(input_filenames={"env_ref"})
        expected_asset_references = job_asset_references.union(
            step_asset_references.union(environment_asset_references)
        )

        step_mock = Mock()
        step_mock.get_asset_references.return_value = step_asset_references

        environment_mock = Mock()
        environment_mock.get_asset_references.return_value = environment_asset_references

        open_job = UnrealOpenJob(
            name="",
            steps=[step_mock],
            environments=[environment_mock],
            asset_references=job_asset_references,
        )

        # WHEN
        asset_references = open_job.get_asset_references()

        # THEN
        assert step_mock.get_asset_references.call_count == 1
        assert environment_mock.get_asset_references.call_count == 1
        assert expected_asset_references.input_filenames == asset_references.input_filenames

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value=fixtures.f_job_template_default(),
    )
    def test__create_missing_extra_parameters_from_template(self, get_template_object_mock: Mock):
        # WHEN
        open_job = UnrealOpenJob()

        # THEN
        parameter_names = [p.name for p in open_job._extra_parameters]
        yaml_parameter_names = [
            p["name"] for p in fixtures.f_job_template_default()["parameterDefinitions"]
        ]
        assert parameter_names == yaml_parameter_names


class TestRenderUnrealOpenJob:

    @pytest.mark.parametrize(
        "environment, strategy",
        [
            (UgsUnrealOpenJobEnvironment(""), TransferProjectFilesStrategy.UGS),
            (None, TransferProjectFilesStrategy.S3),
        ],
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value=fixtures.f_job_template_default(),
    )
    def test__transfer_files_strategy(self, get_template_object_mock, environment, strategy):
        # GIVEN
        render_job = RenderUnrealOpenJob(file_path="", name="JobA", environments=[environment])

        # WHEN
        transfer_strategy = render_job._transfer_files_strategy

        # THEN
        assert transfer_strategy == strategy

    @pytest.mark.parametrize(
        "workspace_root, project_path, expected_relative_path",
        [
            (
                "C:/Workspaces/Workspace1",
                "C:/Workspaces/Workspace1\Project1.uproject",
                "Project1.uproject",
            ),
            (
                "C:\Workspaces/workspace1",
                "C:/workspaces/Workspace1/UE5\Project1.uproject",
                "UE5/Project1.uproject",
            ),
        ],
    )
    def test__get_project_path_relative_to_workspace_root(
        self, workspace_root: str, project_path: str, expected_relative_path: str
    ):
        # GIVEN & WHEN
        with patch(
            "deadline.unreal_submitter.common.get_project_file_path", return_value=project_path
        ):
            relative_path = RenderUnrealOpenJob._get_project_path_relative_to_workspace_root(
                workspace_root=workspace_root,
            )

        # THEN
        assert relative_path == expected_relative_path

    @pytest.mark.parametrize(
        "workspace_root, project_path",
        [
            ("C:/Workspaces/Workspace1", "C:/Workspaces/Workspace2\Project1.uproject"),
            ("C:\Workspaces/workspace1", "C:/workspaces/Workspace2/UE5\Project1.uproject"),
        ],
    )
    def test__get_project_path_relative_to_workspace_root_failed(
        self, workspace_root: str, project_path: str
    ):
        # GIVEN & WHEN $ THEN
        with patch(
            "deadline.unreal_submitter.common.get_project_file_path", return_value=project_path
        ):
            with pytest.raises(exceptions.ProjectIsNotUnderWorkspaceError):
                RenderUnrealOpenJob._get_project_path_relative_to_workspace_root(workspace_root)

    PROJECT_PLUGINS = "C:/Project/Plugins"
    ENGINE_PLUGINS = "C:/Engine/Engine/Plugins"
    MARKETPLACE_DIR = "C:/Engine/Engine/Plugins/Marketplace"

    @pytest.mark.parametrize(
        "project_plugins, marketplace_plugins, marketplace_exists, enabled, expected_dirs",
        [
            # Project plugin enabled
            (
                ["PluginA"],
                [],
                False,
                {"PluginA": True},
                {f"{PROJECT_PLUGINS}/PluginA"},
            ),
            # Project plugin not enabled
            (
                ["PluginA"],
                [],
                False,
                {"PluginA": False},
                set(),
            ),
            # Deadline Cloud plugin excluded
            (
                ["UnrealDeadlineCloudService"],
                [],
                False,
                {"UnrealDeadlineCloudService": True},
                set(),
            ),
            # Marketplace plugin enabled
            (
                [],
                ["PaidPlugin"],
                True,
                {"PaidPlugin": True},
                {f"{MARKETPLACE_DIR}/PaidPlugin"},
            ),
            # Marketplace plugin not enabled
            (
                [],
                ["PaidPlugin"],
                True,
                {"PaidPlugin": False},
                set(),
            ),
            # Mix: project + marketplace, some enabled
            (
                ["ProjectPlugin", "DisabledPlugin"],
                ["PaidPlugin"],
                True,
                {"ProjectPlugin": True, "DisabledPlugin": False, "PaidPlugin": True},
                {
                    f"{PROJECT_PLUGINS}/ProjectPlugin",
                    f"{MARKETPLACE_DIR}/PaidPlugin",
                },
            ),
            # No plugins at all
            (
                [],
                [],
                False,
                {},
                set(),
            ),
            # No marketplace dir exists
            (
                ["PluginA"],
                [],
                False,
                {"PluginA": True},
                {f"{PROJECT_PLUGINS}/PluginA"},
            ),
        ],
    )
    def test_get_plugins_references(
        self,
        monkeypatch,
        project_plugins,
        marketplace_plugins,
        marketplace_exists,
        enabled,
        expected_dirs,
    ):
        fake_lib = MagicMock()
        fake_lib.get_enabled_plugin_names.return_value = [
            name for name, is_enabled in enabled.items() if is_enabled
        ]

        monkeypatch.setattr(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.PluginBlueprintLibrary",
            fake_lib,
        )

        fake_paths = MagicMock()
        fake_paths.project_plugins_dir.return_value = "Plugins/"
        fake_paths.engine_plugins_dir.return_value = "Engine/Plugins/"

        def fake_convert(path):
            if path == "Plugins/":
                return self.PROJECT_PLUGINS
            if path == "Engine/Plugins/":
                return self.ENGINE_PLUGINS
            return path

        fake_paths.convert_relative_path_to_full.side_effect = fake_convert

        monkeypatch.setattr(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.Paths", fake_paths
        )

        def fake_scan(scan_dir):
            normalized = scan_dir.replace("\\", "/")
            if normalized == self.PROJECT_PLUGINS:
                return [(name, f"{self.PROJECT_PLUGINS}/{name}") for name in project_plugins]
            if normalized == self.MARKETPLACE_DIR:
                return [(name, f"{self.MARKETPLACE_DIR}/{name}") for name in marketplace_plugins]
            return []

        monkeypatch.setattr(UnrealOpenJob, "_scan_plugin_dirs", staticmethod(fake_scan))
        monkeypatch.setattr(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.os.path.isdir",
            lambda p: marketplace_exists if p.replace("\\", "/") == self.MARKETPLACE_DIR else False,
        )

        refs: AssetReferences = UnrealOpenJob.get_plugins_references()
        assert refs.input_directories == expected_dirs

    def test_get_marketplace_plugins_dir_exists(self, monkeypatch):
        fake_paths = MagicMock()
        fake_paths.engine_plugins_dir.return_value = "Engine/Plugins/"
        fake_paths.convert_relative_path_to_full.return_value = self.ENGINE_PLUGINS

        monkeypatch.setattr(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.Paths", fake_paths
        )
        monkeypatch.setattr(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.os.path.isdir",
            lambda p: True,
        )

        result = UnrealOpenJob.get_marketplace_plugins_dir()
        assert "Marketplace" in result

    def test_get_marketplace_plugins_dir_not_exists(self, monkeypatch):
        fake_paths = MagicMock()
        fake_paths.engine_plugins_dir.return_value = "Engine/Plugins/"
        fake_paths.convert_relative_path_to_full.return_value = self.ENGINE_PLUGINS

        monkeypatch.setattr(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.Paths", fake_paths
        )
        monkeypatch.setattr(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.os.path.isdir",
            lambda p: False,
        )

        result = UnrealOpenJob.get_marketplace_plugins_dir()
        assert result == ""

    def test_auto_inject_marketplace_env_when_marketplace_exists(self, monkeypatch):
        from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (
            InstallMarketplacePluginsEnvironment,
        )

        monkeypatch.setattr(
            UnrealOpenJob,
            "get_marketplace_plugins_dir",
            staticmethod(lambda: "C:/Engine/Plugins/Marketplace"),
        )
        monkeypatch.setattr(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.UnrealOpenJobEntity.__init__",
            lambda *a, **kw: None,
        )
        monkeypatch.setattr(
            InstallMarketplacePluginsEnvironment, "__init__", lambda self, **kw: None
        )
        monkeypatch.setattr(
            UnrealOpenJob, "_create_missing_extra_parameters_from_template", lambda self: None
        )

        job = UnrealOpenJob()
        assert isinstance(job._environments[0], InstallMarketplacePluginsEnvironment)

    def test_no_inject_marketplace_env_when_no_marketplace(self, monkeypatch):
        from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (
            InstallMarketplacePluginsEnvironment,
        )

        monkeypatch.setattr(UnrealOpenJob, "get_marketplace_plugins_dir", staticmethod(lambda: ""))
        monkeypatch.setattr(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.UnrealOpenJobEntity.__init__",
            lambda *a, **kw: None,
        )
        monkeypatch.setattr(
            UnrealOpenJob, "_create_missing_extra_parameters_from_template", lambda self: None
        )

        job = UnrealOpenJob()
        assert not any(
            isinstance(e, InstallMarketplacePluginsEnvironment) for e in job._environments
        )

    def test_no_duplicate_inject_marketplace_env(self, monkeypatch):
        from deadline.unreal_submitter.unreal_open_job.unreal_open_job_environment import (
            InstallMarketplacePluginsEnvironment,
        )

        monkeypatch.setattr(
            UnrealOpenJob,
            "get_marketplace_plugins_dir",
            staticmethod(lambda: "C:/Engine/Plugins/Marketplace"),
        )
        monkeypatch.setattr(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.UnrealOpenJobEntity.__init__",
            lambda *a, **kw: None,
        )
        monkeypatch.setattr(
            InstallMarketplacePluginsEnvironment, "__init__", lambda self, **kw: None
        )
        monkeypatch.setattr(
            UnrealOpenJob, "_create_missing_extra_parameters_from_template", lambda self: None
        )

        existing_env = InstallMarketplacePluginsEnvironment()
        job = UnrealOpenJob(environments=[existing_env])
        count = sum(
            1 for e in job._environments if isinstance(e, InstallMarketplacePluginsEnvironment)
        )
        assert count == 1
