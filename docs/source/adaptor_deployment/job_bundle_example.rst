###############################
Unreal Job Bundle example
###############################

************
template.yml
************

.. code-block:: YAML

    specificationVersion: jobtemplate-2023-09
    name: TestLevelSequence
    parameterDefinitions:
    - name: ProjectFilePath
     type: PATH
     objectType: FILE
     dataFlow: IN
    - name: ProjectDirectory
     type: STRING
     default: ''
    - name: LevelPath
     type: STRING
     default: ''
    - name: LevelSequencePath
     type: STRING
     default: ''
    - name: JobConfigurationPath
     type: STRING
     default: ''
    - name: OutputPath
     type: STRING
     default: ''
    jobEnvironments:
    - name: RemoteExecution
     description: Define the current context as Remote Execution
     variables:
       REMOTE_EXECUTION: 'True'
    steps:
    - name: Render
     parameterSpace:
       taskParameterDefinitions:
       - name: Handler
         type: STRING
         range:
         - render
       - name: QueueManifestPath
         type: PATH
         range:
         - C:/LocalProjects/UnrealDeadlineCloudTest/Saved/MovieRenderPipeline/QueueManifest.utxt
     script:
       embeddedFiles:
       - name: runData
         filename: run-data.yaml
         type: TEXT
         data: |
           handler: {{Task.Param.Handler}}
           queue_manifest_path: {{Task.Param.QueueManifestPath}}
       - name: initData
         filename: init-data.yaml
         type: TEXT
         data: |
           project_path: {{Param.ProjectFilePath}}
       actions:
         onRun:
           command: UnrealAdaptor
           args:
           - run
           - --init-data
           - file://{{Task.File.initData}}
           - --run-data
           - file://{{ Task.File.runData }}
           cancelation:
             mode: NOTIFY_THEN_TERMINATE
     dependencies:
     - dependsOn: BeforeRender1
    - name: BeforeRender1
     parameterSpace:
       taskParameterDefinitions:
       - name: Handler
         type: STRING
         range:
         - custom
       - name: ScriptPath
         type: PATH
         range:
         - C:/DeadlineCloudScripts/before.py
     script:
       embeddedFiles:
       - name: runData
         filename: run-data.yaml
         type: TEXT
         data: |
           handler: {{Task.Param.Handler}}
           script_path: {{Task.Param.ScriptPath}}
       - name: initData
         filename: init-data.yaml
         type: TEXT
         data: |
           project_path: {{Param.ProjectFilePath}}
       actions:
         onRun:
           command: UnrealAdaptor
           args:
           - run
           - --init-data
           - file://{{Task.File.initData}}
           - --run-data
           - file://{{ Task.File.runData }}
           cancelation:
             mode: NOTIFY_THEN_TERMINATE
    - name: AfterRender1
     parameterSpace:
       taskParameterDefinitions:
       - name: Handler
         type: STRING
         range:
         - custom
       - name: ScriptPath
         type: PATH
         range:
         - C:/DeadlineCloudScripts/after.py
     script:
       embeddedFiles:
       - name: runData
         filename: run-data.yaml
         type: TEXT
         data: |
           handler: {{Task.Param.Handler}}
           script_path: {{Task.Param.ScriptPath}}
       - name: initData
         filename: init-data.yaml
         type: TEXT
         data: |
           project_path: {{Param.ProjectFilePath}}
       actions:
         onRun:
           command: UnrealAdaptor
           args:
           - run
           - --init-data
           - file://{{Task.File.initData}}
           - --run-data
           - file://{{ Task.File.runData }}
           cancelation:
             mode: NOTIFY_THEN_TERMINATE
     dependencies:
     - dependsOn: Render

********************
parameter_values.yml
********************

.. code-block:: YAML

    parameterValues:
    - name: LevelPath
     value: /Game/Test/TestLevel.TestLevel
    - name: LevelSequencePath
     value: /Game/Test/TestLevelSequence.TestLevelSequence
    - name: ProjectFilePath
     value: C:/LocalProjects/UnrealDeadlineCloudTest/DeadlineCloud.uproject
    - name: ProjectDirectory
     value: C:/LocalProjects/UnrealDeadlineCloudTest
    - name: OutputPath
     value: C:/LocalProjects/UnrealDeadlineCloudTest/Saved/MovieRenders/

********************
asset_references.yml
********************

.. code-block:: YAML

    assetReferences:
     inputs:
       directories:
       - C:/LocalProjects/UnrealDeadlineCloudTest/Config
       filenames:
       - C:/DeadlineCloudScripts/after.py
       - C:/DeadlineCloudScripts/before.py
       - C:/LocalProjects/UnrealDeadlineCloudTest/Content/Test/Cube.uasset
       - C:/LocalProjects/UnrealDeadlineCloudTest/Content/Test/TestLevel.umap
       - C:/LocalProjects/UnrealDeadlineCloudTest/Content/Test/TestLevelSequence.uasset
       - C:/LocalProjects/UnrealDeadlineCloudTest/Content/Test/TestLevel_HLOD0_Instancing.uasset
       …
    outputs:
     directories:
     - C:/LocalProjects/UnrealDeadlineCloudTest/Saved/MovieRenders
    referencedPaths: []