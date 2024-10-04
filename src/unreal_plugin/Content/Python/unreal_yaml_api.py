import unreal
import yaml


parameter_definition_value_type_mapping = {
    'INT': 'int_value',
    'FLOAT': 'float_value',
    'STRING': 'string_value',
    'PATH': 'path_value'
}


@unreal.uclass()
class PythonYamlLibraryImplementation(unreal.PythonYamlLibrary):

    @unreal.ufunction(override=True)
    def open_job_file(self, path: str):
        with open(path, 'r') as f:
            job_template = yaml.safe_load(f)

        u_parameter_definitions: list[unreal.ParameterDefinition] = []

        for parameter_definition in job_template['parameterDefinitions']:
            u_parameter_definition = unreal.ParameterDefinition()
            u_parameter_definition.name = parameter_definition['name']
            u_parameter_definition.type = getattr(unreal.ValueType, parameter_definition['type'])

            if parameter_definition.get('default') is not None:
                value_attr = parameter_definition_value_type_mapping.get(parameter_definition['type'])
                setattr(u_parameter_definition, value_attr, parameter_definition['default'])

            u_parameter_definitions.append(u_parameter_definition.copy())

        # name, job params
        return u_parameter_definitions

    @unreal.ufunction(override=True)
    def open_step_file(self, path: str):
        with open(path, 'r') as f:
            step_template = yaml.safe_load(f)

        u_step_parameter_space = unreal.StepParameterSpace()
        u_step_parameter_space.name = step_template['name']  # Step has name, not the StepParameterSpace

        u_step_task_parameter_definitions = []

        for task_parameter_definition in step_template['parameterSpace']['taskParameterDefinitions']:
            u_step_task_parameter_definition = unreal.StepTaskParameterDefinition()
            u_step_task_parameter_definition.name = task_parameter_definition['name']
            u_step_task_parameter_definition.type = getattr(unreal.ValueType, task_parameter_definition['type'])
            u_step_task_parameter_definition.range = [v for v in task_parameter_definition['range']]
            u_step_task_parameter_definitions.append(u_step_task_parameter_definition.copy())

        # u_step_parameter_space.depends_on = [d['dependsOn'] for d in step_template.get('dependencies', [])]

        u_step_parameter_space.step_task_parameter_definition = u_step_task_parameter_definitions

        # name, task params
        return [u_step_parameter_space]

    @unreal.ufunction(override=True)
    def open_env_file(self, path: str):
        file = open(path, 'r')
        result = yaml.safe_load(file)

        struct = unreal.EnvironmentStruct() # get struct
        structs = list()
        data = result['jobEnvironments']
        # check if list
        if isinstance(data, list):
            for index, item in enumerate(data):
                name_ = (item['name'])
                struct.name = name_
                desc_ = (item['description'])
                struct.description = desc_

                vars_ = (item['variables'])

                if isinstance(vars_, list):
                    unreal_string_array = list()

                    for item in vars_:
                        if isinstance(item, str):
                            unreal_string_array.append(item)

                    struct.variables = unreal_string_array
                    unreal_string_array.clear()


                structs.append(struct.copy())
        else:
            print("parameterDefinitions is not a list")
        return structs

