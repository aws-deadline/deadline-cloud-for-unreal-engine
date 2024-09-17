import unreal
import yaml



@unreal.uclass()
class PythonYamlLibraryImplementation(unreal.PythonYamlLibrary):

    @unreal.ufunction(override=True)
    def open_job_file(self, path: str):
        file = open(path, 'r')
        result = yaml.safe_load(file)

        struct = unreal.ParameterDefinition() # get struct
        structs = list()
        enum_value = unreal.ValueType  # get enum for struct

        data = result['parameterDefinitions']
        # check if list
        if isinstance(data, list):
            for index, item in enumerate(data):
                name_ = (item['name'])
                struct.name = name_
                enum_name = (item['type'])
                enum_value = getattr(unreal.ValueType, enum_name)
                struct.type = enum_value

                structs.append(struct.copy())
        else:
            print("parameterDefinitions is not a list")
        return structs

    @unreal.ufunction(override=True)
    def open_step_file(self, path: str):
        file = open(path, 'r')
        result = yaml.safe_load(file)

        struct = unreal.StepParameterDefinition() # get struct
        structs = list()
        struct_task = unreal.StepTaskParameterDefinition()  # get struct

        data = result['steps']

        # check if list
        if isinstance(data, list):
            for index, item in enumerate(data):
                name_ = (item['name'])
                struct.name = name_

                data_space = item['parameterSpace']
                data_def = data_space['taskParameterDefinitions']
                if isinstance(data_def, list):
                    for index, item_ in enumerate(data_def):
                        name_t = (item['name'])
                        struct_task.name = name_t
                        #todo: function to parse enums
                        #struct_task.type
                        range_t = (item['range'])
                        struct_task.range = range_t

                struct.task = struct_task

                
                script_ = (item['script'])
                struct.script = script_
                structs.append(struct.copy())
        else:
            print("parameterDefinitions is not a list")



        return structs



