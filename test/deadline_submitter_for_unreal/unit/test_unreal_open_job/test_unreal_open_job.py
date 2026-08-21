# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import pytest
from types import SimpleNamespace
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
    ProfilingSettings,
    UnrealOpenJob,
    RenderUnrealOpenJob,
    P4RenderUnrealOpenJob,
    UgsUnrealOpenJobEnvironment,
    UnrealOpenJobParameterDefinition,
    TransferProjectFilesStrategy,
)
from deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity import (  # noqa: E402
    OpenJobParameterNames,
)
from deadline.unreal_submitter import exceptions  # noqa: E402
from deadline.unreal_cmd_utils import (  # noqa: E402
    parse_command_line,
)


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

    def test_profiling_settings_from_u_deadline_cloud_profiling_settings(self):
        class FakeProfilingStruct:
            def get_editor_property(self, name):
                values = {
                    "bInsightsCpu": True,
                    "bInsightsGpu": True,
                    "bInsightsMemory": False,
                    "bCsvProfiler": True,
                    "CsvCaptureFrames": 120,
                    "bMemReport": True,
                }
                return values[name]

        profiling_settings = ProfilingSettings.from_u_deadline_cloud_profiling_settings(
            FakeProfilingStruct()
        )

        assert profiling_settings.insights_cpu is True
        assert profiling_settings.insights_gpu is True
        assert profiling_settings.insights_memory is False
        assert profiling_settings.csv_profiler is True
        assert profiling_settings.csv_capture_frames == 120
        assert profiling_settings.memreport is True

    def test_profiling_settings_rejects_missing_or_unreadable_properties(self):
        class UnreadableProfilingStruct:
            @property
            def insights_cpu(self):
                raise AttributeError("insights_cpu is unavailable")

        for profiling_struct in (object(), UnreadableProfilingStruct()):
            with pytest.raises(
                exceptions.SubmitterInputValidationError, match="profiling property 'insights_cpu'"
            ):
                ProfilingSettings.from_u_deadline_cloud_profiling_settings(profiling_struct)

    def test_profiling_settings_build_cmd_args_includes_csv_capture_frames(self):
        profiling_settings = ProfilingSettings(
            insights_cpu=True,
            csv_profiler=True,
            csv_capture_frames=120,
            memreport=True,
        )

        cmd_args = profiling_settings.build_cmd_args()

        assert "-DeadlineCloudInsights=cpu,frame,bookmark,loadtime" in cmd_args
        assert "-csvGpuStats" in cmd_args
        assert "-csvCaptureFrames=120" in cmd_args
        assert "-MemReport" in cmd_args

    @pytest.mark.parametrize(
        "profiling_settings,expected",
        [
            (
                ProfilingSettings(insights_cpu=True, csv_profiler=True, memreport=True),
                [
                    "/project/Saved/Profiling/DeadlineCloud",
                    "/project/Saved/Profiling/CSV",
                    "/project/Saved/Profiling/MemReports",
                ],
            ),
            (
                ProfilingSettings(csv_profiler=True),
                ["/project/Saved/Profiling/CSV"],
            ),
            (
                ProfilingSettings(memreport=True),
                ["/project/Saved/Profiling/MemReports"],
            ),
            (
                ProfilingSettings(csv_profiler=True, memreport=True),
                [
                    "/project/Saved/Profiling/CSV",
                    "/project/Saved/Profiling/MemReports",
                ],
            ),
        ],
    )
    def test_profiling_settings_output_directories(self, profiling_settings, expected):
        assert profiling_settings.get_output_directories("/project/Saved/Profiling") == expected

    def test_profiling_settings_output_directories_normalizes_profiling_directory(self):
        profiling_settings = ProfilingSettings(csv_profiler=True)

        assert profiling_settings.get_output_directories(r"C:\project\Saved\Profiling\\") == [
            "C:/project/Saved/Profiling/CSV"
        ]

    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job_entity."
        "UnrealOpenJobEntity.get_template_object",
        return_value={
            "parameterDefinitions": [
                {"name": OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS, "type": "STRING"},
                {"name": OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS_FILE, "type": "PATH"},
                {"name": OpenJobParameterNames.UNREAL_PROJECT_PATH, "type": "PATH"},
                {"name": OpenJobParameterNames.MARKETPLACE_PLUGINS_DIR, "type": "PATH"},
            ]
        },
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job.common.get_in_process_executor_cmd_args",
        return_value=["-stdout", "-trace=gpu"],
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job.common.get_project_file_path",
        return_value="/project dir/MyProject.uproject",
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job.common.get_project_directory",
        return_value="/project dir",
    )
    @patch(
        "deadline.unreal_submitter.unreal_open_job.unreal_open_job.common.create_deadline_cloud_temp_file",
        return_value="/tmp/ExtraCmdArgsFile.txt",
    )
    @patch.object(
        UnrealOpenJob,
        "get_marketplace_plugins_dir",
        return_value="/Engine/Plugins/Marketplace",
    )
    def test__build_parameter_values_merges_profiling_cmd_args(
        self,
        get_marketplace_plugins_dir_mock,
        create_deadline_cloud_temp_file_mock,
        get_project_directory_mock,
        get_project_file_path_mock,
        get_in_process_executor_cmd_args_mock,
        get_template_object_mock,
    ):
        render_job = RenderUnrealOpenJob(
            file_path="",
            name="JobA",
            extra_parameters=[
                UnrealOpenJobParameterDefinition(
                    OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS,
                    "STRING",
                    '-execcmds="stat fps" -trace=cpu,frame -csvCaptureFrames=999',
                )
            ],
            profiling_settings=ProfilingSettings(
                insights_cpu=True,
                insights_memory=True,
                csv_profiler=True,
                csv_capture_frames=120,
                memreport=True,
            ),
        )

        parameter_values = render_job._build_parameter_values()
        file_data = create_deadline_cloud_temp_file_mock.call_args.kwargs["file_data"]
        _, switches, params = parse_command_line(file_data)

        assert {p["name"]: p["value"] for p in parameter_values}[
            OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS
        ] == ""
        assert {p["name"]: p["value"] for p in parameter_values}[
            OpenJobParameterNames.UNREAL_EXTRA_CMD_ARGS_FILE
        ] == "/tmp/ExtraCmdArgsFile.txt"
        assert {p["name"]: p["value"] for p in parameter_values}[
            OpenJobParameterNames.UNREAL_PROJECT_PATH
        ] == "/project dir/MyProject.uproject"
        assert {p["name"]: p["value"] for p in parameter_values}[
            OpenJobParameterNames.MARKETPLACE_PLUGINS_DIR
        ] == "/Engine/Plugins/Marketplace"
        assert set(switches) == {"stdout", "csvGpuStats", "MemReport"}
        assert params["trace"] == "gpu,cpu,frame"
        assert params["DeadlineCloudInsights"] == "cpu,frame,bookmark,loadtime,memory"
        assert "tracefile" not in params
        assert params["csvCaptureFrames"] == "999"
        assert "ExecCmds" not in params
        assert "/tmp/ExtraCmdArgsFile.txt" in render_job._asset_references.input_filenames

    def test_get_asset_references_adds_profiling_output_directories(self):
        render_job = RenderUnrealOpenJob.__new__(RenderUnrealOpenJob)
        render_job._transfer_files_strategy = None  # type: ignore[assignment]
        render_job._mrq_job = None
        render_job._extra_parameters = []
        render_job._profiling_settings = ProfilingSettings(
            insights_cpu=True, csv_profiler=True, csv_capture_frames=60, memreport=True
        )

        refs = AssetReferences()
        with (
            patch.object(UnrealOpenJob, "get_asset_references", return_value=refs),
            patch(
                "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
                "unreal.Paths.profiling_dir",
                return_value="../../../project/Saved/Profiling",
            ),
            patch(
                "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
                "unreal.Paths.convert_relative_path_to_full",
                return_value="/project/Saved/Profiling",
            ),
        ):
            result = render_job.get_asset_references()

        assert result.output_directories == {
            "/project/Saved/Profiling/DeadlineCloud",
            "/project/Saved/Profiling/CSV",
            "/project/Saved/Profiling/MemReports",
        }

    def test_profiling_output_directories_are_not_resolved_when_disabled(self):
        render_job = RenderUnrealOpenJob.__new__(RenderUnrealOpenJob)
        render_job._profiling_settings = ProfilingSettings()

        with patch(
            "deadline.unreal_submitter.unreal_open_job.unreal_open_job.unreal.Paths.profiling_dir"
        ) as profiling_dir:
            assert render_job._get_profiling_output_directories() == []

        profiling_dir.assert_not_called()

    def test_mrq_job_without_profiling_override_preserves_existing_settings(self):
        existing = ProfilingSettings(insights_cpu=True, csv_profiler=True)
        render_job = RenderUnrealOpenJob.__new__(RenderUnrealOpenJob)
        render_job._profiling_settings = existing
        render_job._extra_parameters = []
        render_job._steps = []
        render_job._environments = []
        render_job._name = "Job"
        mrq_job = SimpleNamespace(
            job_template_overrides=SimpleNamespace(parameters=[]),
            preset_overrides=SimpleNamespace(job_shared_settings=None),
            job_name="MRQ Job",
        )

        render_job.mrq_job = mrq_job

        assert render_job.profiling_settings is existing

    def test_mrq_job_profiling_override_replaces_existing_settings(self):
        render_job = RenderUnrealOpenJob.__new__(RenderUnrealOpenJob)
        render_job._profiling_settings = ProfilingSettings(insights_cpu=True)
        render_job._extra_parameters = []
        render_job._steps = []
        render_job._environments = []
        render_job._name = "Job"
        profiling_override = SimpleNamespace(
            insights_cpu=False,
            insights_gpu=True,
            insights_memory=False,
            csv_profiler=False,
            csv_capture_frames=300,
            memreport=True,
        )
        mrq_job = SimpleNamespace(
            job_template_overrides=SimpleNamespace(parameters=[]),
            preset_overrides=SimpleNamespace(
                job_shared_settings=None, profiling_settings=profiling_override
            ),
            job_name="MRQ Job",
        )

        render_job.mrq_job = mrq_job

        assert render_job.profiling_settings == ProfilingSettings(insights_gpu=True, memreport=True)


class TestP4RenderUnrealOpenJobSubmitModeSkipsJA:
    """
    When SubmitMode is set (submit/shelve), the customer has explicitly opted
    into pushing renders through Perforce and does NOT want the same bytes
    also going to S3 as Job Attachments. Verify get_asset_references clears
    output_directories in that case only.
    """

    def _make_job(self, submit_mode_value):
        """Build a P4RenderUnrealOpenJob with just enough state to exercise
        _submit_mode_active + get_asset_references. Bypass __init__ which
        needs a live Unreal MRQ Job."""
        job = P4RenderUnrealOpenJob.__new__(P4RenderUnrealOpenJob)
        if submit_mode_value is None:
            job._extra_parameters = []
        else:
            job._extra_parameters = [
                UnrealOpenJobParameterDefinition(
                    name="SubmitMode", type="STRING", value=submit_mode_value
                )
            ]
        # get_asset_references gates the "add MRQ overrides" and "add
        # dependencies" branches on state we haven't set up here; providing
        # sane defaults lets us focus the test on the SubmitMode clear.
        job._transfer_files_strategy = None  # type: ignore[assignment]
        job._mrq_job = None
        return job

    def _refs_with_outputs(self):
        refs = AssetReferences()
        refs.output_directories.add("C:/renders/MyProject/Saved/MovieRenders")
        refs.output_directories.add("C:/renders/MyProject/Saved/Logs")
        return refs

    def test_submit_mode_active_returns_false_when_param_missing(self):
        job = self._make_job(submit_mode_value=None)
        assert job._submit_mode_active() is False

    def test_submit_mode_active_returns_false_for_empty_string(self):
        # empty string is the "off" default
        job = self._make_job(submit_mode_value="")
        assert job._submit_mode_active() is False

    @pytest.mark.parametrize("mode", ["submit", "shelve"])
    def test_submit_mode_active_returns_true_for_submit_or_shelve(self, mode):
        job = self._make_job(submit_mode_value=mode)
        assert job._submit_mode_active() is True

    def test_get_asset_references_preserves_outputs_when_mode_empty(self):
        # Patch UnrealOpenJob (grandparent) so RenderUnrealOpenJob's logic
        # (including the SubmitMode reroute) still runs.
        job = self._make_job(submit_mode_value="")
        refs = self._refs_with_outputs()
        with patch.object(UnrealOpenJob, "get_asset_references", return_value=refs):
            result = job.get_asset_references()
        assert len(result.output_directories) == 2
        assert len(result.referenced_paths) == 0

    @pytest.mark.parametrize("mode", ["submit", "shelve"])
    def test_get_asset_references_moves_outputs_to_referenced_when_mode_set(self, mode):
        # SubmitMode active: output dirs must move to referenced_paths so
        # OpenJD still creates path-mapping rules for them, but the worker
        # doesn't upload them to S3 as Job Attachments outputs.
        job = self._make_job(submit_mode_value=mode)
        refs = self._refs_with_outputs()
        original = set(refs.output_directories)
        with patch.object(UnrealOpenJob, "get_asset_references", return_value=refs):
            result = job.get_asset_references()
        assert result.output_directories == set()
        assert result.referenced_paths == original

    def test_get_asset_references_leaves_input_directories_untouched(self):
        # Skipping JA output upload must not affect input attachments —
        # the render still needs its project files.
        job = self._make_job(submit_mode_value="submit")
        refs = AssetReferences()
        refs.input_directories.add("C:/project/input")
        refs.input_filenames.add("C:/project/input/foo.txt")
        refs.output_directories.add("C:/renders/output")
        with patch.object(UnrealOpenJob, "get_asset_references", return_value=refs):
            result = job.get_asset_references()
        assert result.output_directories == set()
        assert result.referenced_paths == {"C:/renders/output"}
        assert len(result.input_directories) == 1
        assert len(result.input_filenames) == 1

    def test_submit_mode_keeps_profiling_outputs_in_job_attachments(self):
        job = self._make_job(submit_mode_value="submit")
        job._profiling_settings = ProfilingSettings(insights_cpu=True)
        refs = AssetReferences()
        refs.output_directories.add("C:/renders/output")

        with (
            patch.object(UnrealOpenJob, "get_asset_references", return_value=refs),
            patch(
                "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
                "unreal.Paths.profiling_dir",
                return_value="../../../project/Saved/Profiling",
            ),
            patch(
                "deadline.unreal_submitter.unreal_open_job.unreal_open_job."
                "unreal.Paths.convert_relative_path_to_full",
                return_value=r"C:\project\Saved\Profiling\\",
            ),
        ):
            result = job.get_asset_references()

        assert result.output_directories == {"C:/project/Saved/Profiling/DeadlineCloud"}


class TestP4RenderUnrealOpenJobAssembleShelvesInjection:
    """
    When SubmitMode is set, an AssembleShelves step gets appended to the
    job so all render tasks' shelved CLs are aggregated into one final CL.
    Verify the injection logic: added when needed, not when not, idempotent.
    """

    def _make_job(self, submit_mode_value, existing_steps=None):
        job = P4RenderUnrealOpenJob.__new__(P4RenderUnrealOpenJob)
        if submit_mode_value is None:
            job._extra_parameters = []
        else:
            job._extra_parameters = [
                UnrealOpenJobParameterDefinition(
                    name="SubmitMode", type="STRING", value=submit_mode_value
                )
            ]
        job._steps = list(existing_steps or [])
        return job

    def test_no_step_injected_when_submit_mode_empty(self):
        from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
            P4AssembleShelvesUnrealOpenJobStep,
        )

        job = self._make_job(submit_mode_value="")
        job._ensure_assemble_shelves_step()
        assert not any(isinstance(s, P4AssembleShelvesUnrealOpenJobStep) for s in job._steps)

    @pytest.mark.parametrize("mode", ["submit", "shelve"])
    def test_step_injected_when_submit_mode_set(self, mode):
        from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
            P4AssembleShelvesUnrealOpenJobStep,
        )

        # Bypass the __init__ chain that reads yaml files off disk
        with patch.object(P4AssembleShelvesUnrealOpenJobStep, "__init__", lambda self: None):
            job = self._make_job(submit_mode_value=mode)
            job._ensure_assemble_shelves_step()
        assemble_steps = [
            s for s in job._steps if isinstance(s, P4AssembleShelvesUnrealOpenJobStep)
        ]
        assert len(assemble_steps) == 1

    def test_step_injection_is_idempotent(self):
        # Calling _ensure_assemble_shelves_step twice must not stack
        # duplicates — _build_template can be called more than once during
        # a submission flow.
        from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step import (
            P4AssembleShelvesUnrealOpenJobStep,
        )

        with patch.object(P4AssembleShelvesUnrealOpenJobStep, "__init__", lambda self: None):
            job = self._make_job(submit_mode_value="submit")
            job._ensure_assemble_shelves_step()
            job._ensure_assemble_shelves_step()
            job._ensure_assemble_shelves_step()
        assemble_steps = [
            s for s in job._steps if isinstance(s, P4AssembleShelvesUnrealOpenJobStep)
        ]
        assert len(assemble_steps) == 1
