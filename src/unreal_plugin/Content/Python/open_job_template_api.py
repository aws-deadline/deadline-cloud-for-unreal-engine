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
            u_parameter_definition.value = str(job_parameter['default'])
            #value_attr = parameter_definition_value_type_mapping.get(job_parameter['type'])
            #setattr(u_parameter_definition, value_attr, job_parameter['default'])

        return u_parameter_definition

    @staticmethod
    def step_parameter_to_u_step_task_parameter(
            step_parameter: dict[str]
    ) -> unreal.StepTaskParameterDefinition:
        u_step_task_parameter_definition = unreal.StepTaskParameterDefinition()
        u_step_task_parameter_definition.name = step_parameter['name']
        u_step_task_parameter_definition.type = getattr(unreal.ValueType, step_parameter['type'])
        u_step_task_parameter_definition.range = [str(v) for v in step_parameter['range']]

        return u_step_task_parameter_definition

    @staticmethod
    def environment_to_u_environment(
            environment: dict[str, Any]
    ) -> unreal.EnvironmentStruct:
        u_environment = unreal.EnvironmentStruct()
        u_environment.name = environment['name']
        u_environment.description = environment.get('description', '')

        u_variables: list[unreal.EnvVariable] = []
        for k, v in environment.get('variables', {}).items():
            u_variable = unreal.EnvVariable()
            u_variable.name = k
            u_variable.value = v

            u_variables.append(u_variable.copy())

        u_environment.variables = u_variables

        return u_environment

    @unreal.ufunction(override=True)
    def open_job_file(self, path: str) -> list[unreal.ParameterDefinition]:
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
    def open_step_file(self, path: str) -> unreal.StepStruct:
        with open(path, 'r') as f:
            step_template = yaml.safe_load(f)

        u_step_task_parameter_definitions: list[unreal.StepTaskParameterDefinition] = []

        for task_parameter_definition in step_template['parameterSpace']['taskParameterDefinitions']:
            u_step_task_parameter_definition = PythonYamlLibraryImplementation.step_parameter_to_u_step_task_parameter(
                task_parameter_definition
            )
            u_step_task_parameter_definitions.append(u_step_task_parameter_definition.copy())

        u_step_struct = unreal.StepStruct()
        u_step_struct.name = step_template['name']
        u_step_struct.parameters = u_step_task_parameter_definitions

        return u_step_struct

    @unreal.ufunction(override=True)
    def open_env_file(self, path: str) -> unreal.EnvironmentStruct:
        with open(path, 'r') as f:
            environment_template = yaml.safe_load(f)

        u_environment = PythonYamlLibraryImplementation.environment_to_u_environment(
            environment_template
        )

        return u_environment


@unreal.uclass()
class ParametersConsistencyChecker(unreal.PythonParametersConsistencyChecker):

    @staticmethod
    def get_parameters_symmetric_difference(
            parameters_left: list[tuple[str, str]],
            parameters_right: list[tuple[str, str]]
    ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:

        missed_in_left = list(set(parameters_right).difference(set(parameters_left)))
        missed_in_right = list(set(parameters_left).difference(set(parameters_right)))
        return missed_in_left, missed_in_right

    @staticmethod
    def check_parameters_consistency(
            yaml_parameters: list[tuple[str, str]],
            data_asset_parameters: list[tuple[str, str]]
    ) -> unreal.ParametersConsistencyCheckResult:
        """
        Check the consistency of the parameters described in the YAML and OpenJob asset (Job, Step, Environment).
        Parameters are not consensual if:
        1. OpenJob asset's parameters are missed in YAML
        2. YAML parameters are missed in OpenJob asset
        """

        reasons = []
        passed = True

        missed_in_yaml, missed_in_data_asset = ParametersConsistencyChecker.get_parameters_symmetric_difference(
            parameters_left=yaml_parameters,
            parameters_right=data_asset_parameters
        )

        if missed_in_yaml:
            passed = False
            missed_in_yaml_str = [f'{p[0]} ({p[1]})' for p in missed_in_yaml]
            warn_message = 'Data Asset\'s parameters missed in YAML: {}'.format(', '.join(missed_in_yaml_str))
            unreal.log_warning(warn_message)
            reasons.append(warn_message)

        if missed_in_data_asset:
            passed = False
            missed_in_data_asset_str = [f'{p[0]} ({p[1]})' for p in missed_in_data_asset]
            warn_message = 'YAML\'s parameters missed in Data Asset: {}'.format(', '.join(missed_in_data_asset_str))
            unreal.log_warning(warn_message)
            reasons.append(warn_message)

        reason = '\n'.join(reasons) if not passed else 'Parameters are consensual'

        result = unreal.ParametersConsistencyCheckResult()
        result.passed = passed
        result.reason = reason

        unreal.log(f'Parameters consistency check result: {passed}, {reason}')

        return result

    @unreal.ufunction(override=True)
    def check_job_parameters_consistency(
            self,
            open_job: unreal.DeadlineCloudJob
    ) -> unreal.ParametersConsistencyCheckResult:

        unreal.log('Checking OpenJob parameters consistency ...')

        with open(open_job.path_to_template.file_path, 'r') as f:
            job_template = yaml.safe_load(f)

        return self.check_parameters_consistency(
            yaml_parameters=[(p['name'], p['type']) for p in job_template['parameterDefinitions']],
            data_asset_parameters=[(p.name, p.type.name) for p in open_job.get_job_parameters()]
        )

    @unreal.ufunction(override=True)
    def fix_job_parameters_consistency(self, open_job: unreal.DeadlineCloudJob):

        unreal.log('Fixing OpenJob parameters consistency ...')

        with open(open_job.path_to_template.file_path, 'r') as f:
            job_template = yaml.safe_load(f)

        missed_in_yaml, missed_in_data_asset = ParametersConsistencyChecker.get_parameters_symmetric_difference(
            parameters_left=[(p['name'], p['type']) for p in job_template['parameterDefinitions']],
            parameters_right=[(p.name, p.type.name) for p in open_job.get_job_parameters()]
        )

        unreal.log(f'FIXING Missed in YAML: {missed_in_yaml}')
        unreal.log(f'FIXING Missed in Data asset: {missed_in_data_asset}')

        if missed_in_yaml or missed_in_data_asset:
            fixed_parameter_definitions: list[unreal.ParameterDefinition] = []
            for u_parameter_definition in open_job.get_job_parameters():
                if (u_parameter_definition.name, u_parameter_definition.type.name) not in missed_in_yaml:
                    fixed_parameter_definitions.append(u_parameter_definition.copy())
                    unreal.log(f'DATA ASSET Parameter that in yaml and data asset {u_parameter_definition.name} {u_parameter_definition.type}')

            for parameter_definition in job_template['parameterDefinitions']:
                if (parameter_definition['name'], parameter_definition['type']) in missed_in_data_asset:
                    u_parameter_definition = PythonYamlLibraryImplementation.job_parameter_to_u_parameter_definition(
                        parameter_definition
                    )
                    fixed_parameter_definitions.append(u_parameter_definition.copy())
                    unreal.log(f'YAML Parameter that missed in DATA ASSET {parameter_definition["name"]} {parameter_definition["type"]}')

            unreal.log(f'Fixed OpenJob parameters: {fixed_parameter_definitions}')

            open_job.set_job_parameters(fixed_parameter_definitions)

    @unreal.ufunction(override=True)
    def check_step_parameters_consistency(
            self,
            open_job_step: unreal.DeadlineCloudStep
    ) -> unreal.ParametersConsistencyCheckResult:

        unreal.log('Checking OpenJobStep parameters consistency ...')

        with open(open_job_step.path_to_template.file_path, 'r') as f:
            step_template = yaml.safe_load(f)

        return self.check_parameters_consistency(
            yaml_parameters=[(p['name'], p['type']) for p in step_template['parameterSpace']['taskParameterDefinitions']],
            data_asset_parameters=[(p.name, p.type.name) for p in open_job_step.get_step_parameters()]
        )

    @unreal.ufunction(override=True)
    def fix_step_parameters_consistency(self, open_job_step: unreal.DeadlineCloudStep):

        unreal.log('Fixing OpenJobStep parameters consistency ...')

        with open(open_job_step.path_to_template.file_path, 'r') as f:
            step_template = yaml.safe_load(f)

        missed_in_yaml, missed_in_data_asset = ParametersConsistencyChecker.get_parameters_symmetric_difference(
            parameters_left=[(p['name'], p['type']) for p in step_template['parameterSpace']['taskParameterDefinitions']],
            parameters_right=[(p.name, p.type.name) for p in open_job_step.get_step_parameters()]
        )

        if missed_in_yaml or missed_in_data_asset:
            fixed_step_task_parameter_definitions: list[unreal.StepTaskParameterDefinition] = []
            for u_parameter_definition in open_job_step.task_parameter_definitions:
                if (u_parameter_definition.name, u_parameter_definition.type.name) not in missed_in_yaml:
                    fixed_step_task_parameter_definitions.append(u_parameter_definition.copy())

            for parameter_definition in step_template['parameterSpace']['taskParameterDefinitions']:
                if (parameter_definition['name'], parameter_definition['type']) in missed_in_data_asset:
                    u_parameter_definition = PythonYamlLibraryImplementation.step_parameter_to_u_step_task_parameter(
                        parameter_definition
                    )
                    fixed_step_task_parameter_definitions.append(u_parameter_definition.copy())

            unreal.log(f'Fixed OpenJobStep parameters: {fixed_step_task_parameter_definitions}')

            open_job_step.set_step_parameters(fixed_step_task_parameter_definitions)

    @unreal.ufunction(override=True)
    def check_environment_variables_consistency(
            self,
            open_job_environment: unreal.DeadlineCloudEnvironment
    ) -> unreal.ParametersConsistencyCheckResult:

        unreal.log('Checking OpenJobEnvironment variables consistency ...')

        with open(open_job_environment.path_to_template.file_path, 'r') as f:
            environment_template = yaml.safe_load(f)

        return self.check_parameters_consistency(
            yaml_parameters=[(k, 'VARIABLE') for k in environment_template['variables'].keys()],
            data_asset_parameters=[(v.name, 'VARIABLE') for v in open_job_environment.environment_structure.variables]
        )

    @unreal.ufunction(override=True)
    def fix_environment_variables_consistency(self, open_job_environment: unreal.DeadlineCloudEnvironment):

        unreal.log('Fixing OpenJobEnvironment variables consistency ...')

        with open(open_job_environment.path_to_template.file_path, 'r') as f:
            environment_template = yaml.safe_load(f)

        missed_in_yaml, missed_in_data_asset = ParametersConsistencyChecker.get_parameters_symmetric_difference(
            parameters_left=[(k, 'VARIABLE') for k in environment_template['variables'].keys()],
            parameters_right=[(v.name, 'VARIABLE') for v in open_job_environment.environment_structure.variables]
        )
        if missed_in_yaml or missed_in_data_asset:
            fixed_environment_variables: list[unreal.EnvVariable] = []
            for u_variable in open_job_environment.environment_structure.variables:
                if (u_variable.name, 'VARIABLE') not in missed_in_yaml:
                    fixed_environment_variables.append(u_variable.copy())

            for var_name, var_value in environment_template['variables'].items():
                if (var_name, 'VARIABLE') in missed_in_data_asset:
                    u_variable = unreal.EnvVariable()
                    u_variable.name = var_name
                    u_variable.value = var_value
                    fixed_environment_variables.append(u_variable.copy())

            unreal.log(f'Fixed OpenJobEnvironment variables: {fixed_environment_variables}')

            open_job_environment.environment_structure.variables = fixed_environment_variables
