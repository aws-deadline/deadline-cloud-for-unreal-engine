def f_job_template_default() -> dict:
    return {
        "specificationVersion": "jobtemplate-2023-09",
        "name": "JobA",
        "parameterDefinitions": [
            {
                "name": "ParamA",
                "type": "PATH",
                "objectType": "FILE",
                "dataFlow": "IN",
                "default": "path/to/file",
            },
            {"name": "ParamB", "type": "STRING", "default": "foo"},
            {"name": "ParamC", "type": "INT", "default": 1},
            {"name": "ParamD", "type": "FLOAT", "default": 1.0},
        ],
    }


def f_step_template_default() -> dict:
    return {
        "name": "StepA",
        "parameterSpace": {
            "taskParameterDefinitions": [
                {"name": "ParamA", "type": "PATH", "range": ["path/to/file"]},
                {"name": "ParamB", "type": "STRING", "range": ["foo"]},
                {"name": "ParamC", "type": "INT", "range": [1]},
                {"name": "ParamD", "type": "FLOAT", "range": [1.0]},
            ]
        },
        "script": {
            "embeddedFiles": [
                {
                    "name": "Run",
                    "filename": "run.bat",
                    "runnable": True,
                    "type": "TEXT",
                    "data": "echo {{Task.Param.ParamA}}\necho {{Task.Param.ParamB}}\necho {{Task.Param.ParamC}}\necho {{Task.Param.ParamD}}\n",
                }
            ],
            "actions": {
                "onRun": {
                    "command": "{{Task.File.Run}}",
                    "cancelation": {"mode": "NOTIFY_THEN_TERMINATE"},
                }
            },
        },
    }


def f_environment_template_default() -> dict:
    return {
        "name": "EnvironmentA",
        "variables": {"VARIABLE_A": "VALUE_A", "VARIABLE_B": "VALUE_B"},
        "script": {
            "embeddedFiles": [
                {
                    "name": "Init",
                    "filename": "init.bat",
                    "runnable": True,
                    "type": "TEXT",
                    "data": "echo {{Param.ParamA}}\necho {{Param.ParamB}}\necho {{Param.ParamC}}\necho {{Param.ParamD}}\n",
                },
                {
                    "name": "Exit",
                    "filename": "exit.bat",
                    "runnable": True,
                    "type": "TEXT",
                    "data": "echo {{Param.ParamD}}\necho {{Param.ParamC}}\necho {{Param.ParamB}}\necho {{Param.ParamA}}\n",
                },
            ],
            "actions": {
                "onEnter": {
                    "command": "{{Env.File.Init}}",
                    "cancelation": {"mode": "NOTIFY_THEN_TERMINATE"},
                },
                "onExit": {
                    "command": "{{Env.File.Exit}}",
                    "cancelation": {"mode": "NOTIFY_THEN_TERMINATE"},
                },
            },
        },
    }
