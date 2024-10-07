import yaml
import unreal
from typing import Any


parameter_definition_value_type_mapping = {
    'INT': 'int_value',
    'FLOAT': 'float_value',
    'STRING': 'string_value',
    'PATH': 'path_value'
}


@unreal.uclass()
class PythonYamlLibraryImplementation(unreal.PythonYamlLibrary):

    @staticmethod
    def job_parameter_to_u_parameter_definition(job_parameter: dict[str, Any]) -> unreal.ParameterDefinition:
        u_parameter_definition = unreal.ParameterDefinition()
        u_parameter_definition.name = job_parameter['name']
        u_parameter_definition.type = getattr(unreal.ValueType, job_parameter['type'])

        if job_parameter.get('default') is not None:
            value_attr = parameter_definition_value_type_mapping.get(job_parameter['type'])
            setattr(u_parameter_definition, value_attr, job_parameter['default'])

        return u_parameter_definition

    @staticmethod
    def step_parameter_to_u_step_task_parameter_definition(
            step_parameter: dict[str]
    ) -> unreal.StepTaskParameterDefinition:
        u_step_task_parameter_definition = unreal.StepTaskParameterDefinition()
        u_step_task_parameter_definition.name = step_parameter['name']
        u_step_task_parameter_definition.type = getattr(unreal.ValueType, step_parameter['type'])
        u_step_task_parameter_definition.range = [v for v in step_parameter['range']]

        return u_step_task_parameter_definition

    @staticmethod
    def environment_to_u_environment(
            environment: dict[str, Any]
    ) -> unreal.EnvironmentStruct:
        u_environment = unreal.EnvironmentStruct()
        u_environment.name = environment['name']
        u_environment.description = environment.get('description', '')
        # TODO i.alekseeva variables should be a list of pairs, not just a string joind by "="
        u_environment.variables = [f'{k}={v}' for k, v in environment.get('variables', {}).items()]

        return u_environment

    @unreal.ufunction(override=True)
    def open_job_file(self, path: str):
        with open(path, 'r') as f:
            job_template = yaml.safe_load(f)

        u_parameter_definitions: list[unreal.ParameterDefinition] = []

        for parameter_definition in job_template['parameterDefinitions']:
            u_parameter_definition = PythonYamlLibraryImplementation.job_parameter_to_u_parameter_definition(
                parameter_definition
            )
            u_parameter_definitions.append(u_parameter_definition.copy())

        return u_parameter_definitions

    @unreal.ufunction(override=True)
    def open_step_file(self, path: str):
        with open(path, 'r') as f:
            step_template = yaml.safe_load(f)

        u_step_parameter_space = unreal.StepParameterSpace()
        u_step_parameter_space.name = step_template['name']  # TODO i.alekseeva Only step has name, not the params space

        u_step_task_parameter_definitions = []

        for task_parameter_definition in step_template['parameterSpace']['taskParameterDefinitions']:
            u_step_task_parameter_definition = PythonYamlLibraryImplementation.step_parameter_to_u_step_task_parameter_definition(
                task_parameter_definition
            )
            u_step_task_parameter_definitions.append(u_step_task_parameter_definition.copy())

        u_step_parameter_space.step_task_parameter_definition = u_step_task_parameter_definitions

        return [u_step_parameter_space]

    @unreal.ufunction(override=True)
    def open_env_file(self, path: str):
        with open(path, 'r') as f:
            environment_template = yaml.safe_load(f)

        u_environment = PythonYamlLibraryImplementation.environment_to_u_environment(
            environment_template
        )

        # TODO i.alekseeva should return single struct
        return [u_environment]


# TODO i.alekseeva mocked consistency check structure, need to implement in C++
from dataclasses import dataclass


@dataclass
class ParametersConsistencyCheckResult:

    passed: bool
    reason: str


class ParametersConsistencyChecker:

    @staticmethod
    def get_parameters_symmetric_difference(
            parameters_left: list[str],
            parameters_right: list[str]
    ) -> tuple[list[str], list[str]]:

        missed_in_left = list(set(parameters_right).difference(set(parameters_left)))
        missed_in_right = list(set(parameters_left).difference(set(parameters_right)))
        return missed_in_left, missed_in_right

    @staticmethod
    def check_parameters_consistency(
            yaml_parameter_names: list[str],
            data_asset_parameter_names: list[str]
    ) -> ParametersConsistencyCheckResult:
        """
        Check the consistency of the parameters described in the YAML and OpenJob asset (Job, Step, Environment).
        Parameters are not consensual if:
        1. OpenJob asset's parameters are missed in YAML
        2. YAML parameters are missed in OpenJob asset
        """

        reasons = []
        passed = True

        missed_in_yaml, missed_in_data_asset = ParametersConsistencyChecker.get_parameters_symmetric_difference(
            parameters_left=yaml_parameter_names,
            parameters_right=data_asset_parameter_names
        )

        if missed_in_yaml:
            passed = False
            reasons.append(
                'Data Asset\'s parameters missed in YAML: {}'.format(', '.join(missed_in_yaml))
            )

        if missed_in_data_asset:
            passed = False
            reasons.append(
                'YAML\'s parameters missed in Data Asset: {}'.format(', '.join(missed_in_data_asset))
            )

        reason = '\n'.join(reasons) if not passed else 'Parameters are consensual'

        return ParametersConsistencyCheckResult(passed, reason)

    def check_job_parameters_consistency(
            self,
            open_job: unreal.DeadlineCloudJob
    ) -> ParametersConsistencyCheckResult:

        with open(open_job.path_to_template, 'r') as f:
            job_template = yaml.safe_load(f)

        yaml_parameter_names = [p['name'] for p in job_template['parameterDefinitions']]
        open_job_parameters = [p.name for p in open_job.job_parameters]

        return self.check_parameters_consistency(
            yaml_parameter_names=yaml_parameter_names,
            data_asset_parameter_names=open_job_parameters
        )

    def fix_job_parameters_consistency(self, open_job: unreal.DeadlineCloudJob):
        with open(open_job.path_to_template, 'r') as f:
            job_template = yaml.safe_load(f)

        yaml_parameter_names = [p['name'] for p in job_template['parameterDefinitions']]
        open_job_parameters = [p.name for p in open_job.job_parameters]

        missed_in_yaml, missed_in_data_asset = ParametersConsistencyChecker.get_parameters_symmetric_difference(
            parameters_left=yaml_parameter_names,
            parameters_right=open_job_parameters
        )

        if missed_in_yaml or missed_in_data_asset:
            fixed_parameter_definitions: list[unreal.ParameterDefinition] = []
            for u_parameter_definition in open_job.job_parameters:
                if u_parameter_definition.name not in missed_in_yaml:
                    fixed_parameter_definitions.append(u_parameter_definition.copy())

            for parameter_definition in job_template['parameterDefinitions']:
                if parameter_definition['name'] in missed_in_data_asset:
                    u_parameter_definition = PythonYamlLibraryImplementation.job_parameter_to_u_parameter_definition(
                        parameter_definition
                    )
                    fixed_parameter_definitions.append(u_parameter_definition.copy())

            open_job.job_parameters = fixed_parameter_definitions

    def check_step_parameters_consistency(
            self,
            open_job_step: unreal.DeadlineCloudStep
    ) -> ParametersConsistencyCheckResult:
        with open(open_job_step.path_to_template, 'r') as f:
            step_template = yaml.safe_load(f)

        yaml_parameter_names = [p['name'] for p in step_template['parameterSpace']['taskParameterDefinitions']]
        open_job_step_parameters = [p.name for p in open_job_step.step_parameters]

        return self.check_parameters_consistency(
            yaml_parameter_names=yaml_parameter_names,
            data_asset_parameter_names=open_job_step_parameters
        )

    def fix_step_parameters_consistency(self, open_job_step: unreal.DeadlineCloudStep):
        with open(open_job_step.path_to_template, 'r') as f:
            step_template = yaml.safe_load(f)

        yaml_parameter_names = [p['name'] for p in step_template['parameterSpace']['taskParameterDefinitions']]
        open_job_step_parameters = [p.name for p in open_job_step.step_parameters]

        missed_in_yaml, missed_in_data_asset = ParametersConsistencyChecker.get_parameters_symmetric_difference(
            parameters_left=yaml_parameter_names,
            parameters_right=open_job_step_parameters
        )

        if missed_in_yaml or missed_in_data_asset:
            # TODO i.alekseeva Step has only one ParameterSpace
            fixed_step_task_parameter_definitions: list[unreal.StepTaskParameterDefinition] = []
            for u_parameter_definition in open_job_step.step_parameters[0].step_task_parameter_definition:
                if u_parameter_definition.name not in missed_in_yaml:
                    fixed_step_task_parameter_definitions.append(u_parameter_definition.copy())

            for parameter_definition in step_template['parameterSpace']['taskParameterDefinitions']:
                if parameter_definition['name'] in missed_in_data_asset:
                    u_parameter_definition = PythonYamlLibraryImplementation.step_parameter_to_u_step_task_parameter_definition(
                        parameter_definition
                    )
                    fixed_step_task_parameter_definitions.append(u_parameter_definition.copy())

            open_job_step.step_parameters[0].step_task_parameter_definition = fixed_step_task_parameter_definitions

    def check_environment_variables_consistency(
            self,
            open_job_environment: unreal.DeadlineCloudEnvironment
    ) -> ParametersConsistencyCheckResult:
        with open(open_job_environment.path_to_template, 'r') as f:
            environment_template = yaml.safe_load(f)

        # TODO i.alekseeva variables should be a list of pairs, not just a string joined by "="
        yaml_variable_names = [k for k in environment_template['variables'].keys()]
        open_job_environment_variable_names = [
            v.split('=')[0] for v in open_job_environment.environment_structure.variables
        ]

        return self.check_parameters_consistency(
            yaml_parameter_names=yaml_variable_names,
            data_asset_parameter_names=open_job_environment_variable_names
        )

    def fix_environment_variables_consistency(self, open_job_environment: unreal.DeadlineCloudEnvironment):
        with open(open_job_environment.path_to_template, 'r') as f:
            environment_template = yaml.safe_load(f)

        # TODO i.alekseeva variables should be a list of pairs, not just a string joined by "="
        yaml_variable_names = [k for k in environment_template['variables'].keys()]
        open_job_environment_variable_names = [
            v.split('=')[0] for v in open_job_environment.environment_structure.variables
        ]

        missed_in_yaml, missed_in_data_asset = ParametersConsistencyChecker.get_parameters_symmetric_difference(
            parameters_left=yaml_variable_names,
            parameters_right=open_job_environment_variable_names
        )

        if missed_in_yaml or missed_in_data_asset:
            fixed_environment_variables: dict = {}
            for u_variable in open_job_environment.environment_structure.variables:
                var_name, var_value = u_variable.split('=')
                if var_name not in missed_in_yaml:
                    fixed_environment_variables[var_name] = var_value

            for var_name, var_value in environment_template['variables'].items():
                if var_name in missed_in_data_asset:
                    fixed_environment_variables[var_name] = var_value

            open_job_environment.environment_structure.variables = [
                f'{k}={v}' for k, v in fixed_environment_variables.items()
            ]
