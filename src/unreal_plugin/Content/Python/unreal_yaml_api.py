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

        step_struct = unreal.StepParameterSpace() # get struct
        step_structs = list()
        struct_task = unreal.StepTaskParameterDefinition()  # get struct
        struct_tasks = list()
        enum_value = unreal.ValueType  # get enum for struct

        steps_ = result['steps'] #steps = parameterSpaces

        # check if list
        if isinstance(steps_, list):
            for index, item in enumerate(steps_):
                name_ = (item['name'])
                step_struct.name = name_

                step_space = item['parameterSpace']
                task_def = step_space['taskParameterDefinitions']
                if isinstance(task_def, list):
                    for index, item_ in enumerate(task_def):
                        name_t = (item_['name'])
                        struct_task.name = name_t

                        stype = (item_['type'])
                        enum_value = getattr(unreal.ValueType, stype)
                        struct_task.type = enum_value

                        struct_tasks.append(struct_task.copy())

                step_struct.step_task_parameter_definition = struct_tasks
                
               # script_ = (item['script'])
               # struct.script = script_
                step_structs.append(step_struct.copy())
        else:
            print("parameterDefinitions is not a list")



        return step_structs



