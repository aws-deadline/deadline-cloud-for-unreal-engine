# Amazon Deadline Cloud for Unreal Development

## Building the docs

1. Install python requirements for building Sphinx documentation
   ```
   pip install -r docs_requirements.txt
   ```
2. Build and install the **deadline-cloud-for-unreal** package in the python that you use to build the docs
   ```
   cd .\path\to\deadline-cloud\for-unreal
   python -m build
   python -m pip install dist/deadline_cloud_for_unreal-*-py3-none-any.whl
   ```
3. Go to the "docs" folder
   ```
   cd docs
   ```

4. Run documentation building
   ```
   make.bat html
   ```
   
5. Generated documentation will be placed at *docs/build/html* folder.
   You can visit the "Home" page of the docs by opening the **index.html** file


## Run unit tests for UnrealSubmitter

1. Prepare the expected job bundle:
   1. Create the ```expected template.yaml```, ```parameter_values.yaml``` and ```asset_references.yaml``` files with the job properties
   2. Copy them to the ```..\..\deadline-cloud-for-unreal\test\deadline_submitter_for_unreal\unit\expected_job_bundle``` directory
2. Launch the Unreal project
3. Open the Movie Render Queue window (Go to header menu -> "Window" -> "Cinematics" -> "Movie Render Queue")
4. In the MRQ window add the render job, setup the Config, Map and JobPreset
3. Open the "Output Log" window (Go to header menu -> "Window" -> "Output Log")
4. In the Log window switch to "Cmd" type if it's not
(should be by default, possible variants: "Cmd", "Python", "Python (REPL)")
5. Run the unit tests for submitter here:
   ```
   py "C:\deadline\deadline-cloud-for-unreal\test\deadline_submitter_for_unreal\unit\test_submitter.py"
   ```
   Make sure, that you provide the absolute path to the ```test_submitter.py``` script on your computer
6. The possible successful output:
   ```
   Test Case TestUnrealDependencyCollector result:
   Total run: 5
   Successful: True
   Errors: 0
   Failures: []
   
   Test Case TestUnrealOpenJob result:
   Total run: 3
   Successful: True
   Errors: 0
   Failures: []
   
   Test Case TestUnrealSubmitter result:
   Total run: 4
   Successful: True
   Errors: 0
   Failures: []
   ```

## Building the Plugin

In order to use this plugin with Unreal Engine, you will need to build the plugin manually. To do this:  

0. Install Visual Studio with C++ components. 
1. Download this repository.
2. Open a command line window
3. Change the directory to Unreal Engine's Batchfiles folder.
    - eg. [installed UE location]\Engine\Build\Batchfiles
4. Run the following command:
    - `RunUAT.bat BuildPlugin -plugin="[root of this repository]\src\unreal_plugin\UnrealDeadlineCloudService.uplugin" -package="[temporary directory]"` 
5. Copy the temporary directory to Unreal Engine's plugins folder.
6. Open the uproject in Unreal and enable the UnrealDeadlineCloudService plugin. 

## Installing the Submitter and Adaptor client

Run the Deadline Cloud Submitter Installer and select the Unreal component then follow the prompts.