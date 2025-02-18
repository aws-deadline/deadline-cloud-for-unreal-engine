# Unreal Submitter/CMF Worker Setup Instructions

This will walk you through setting up your Unreal Submitter with optional additional instructions for setting up an instance to act as a worker as part of a Customer Managed Fleet (CMF). The Unreal Submitter in Deadline Cloud can currently only work if you've set up a CMF and have connected a worker with Unreal installed on an appropriate instance type.

## Create a new Windows EC2 instance to install Unreal on (Optional)

If you’re setting up on a brand new Windows EC2 Instance as your submitter, a g5.2xlarge instance with 200 GB of storage will likely be reasonable minimum:

1. Download the Epic Installer and install a version of Unreal between versions 5.2 and 5.4. With 5.5 a bug has been observed that may prevent headless rendering on Deadline Cloud - we recommend using version 5.4.x at latest currently.
1. NVIDIA GRID drivers - Follow Windows instructions - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-nvidia-driver.html#nvidia-GRID-driver

## Windows Long Paths

Many of the steps below may attempt to create files which exceed the default Windows maximum path length.  Before attempting to build and install the Deadline Cloud for Unreal Engine submitter or adapter on a Windows machine you are strongly encouraged to enable Windows Long path support by following the instructions in one of the options from [this page](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation?tabs=registry), such as by running the PowerShell command [here](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation?tabs=powershell#tabpanel_1_powershell).

## Install Build Tools

The Unreal Submitter Plugin currently must be compiled locally.

1. Install Visual Studio 2022 or later using the Visual Studio Installer from https://visualstudio.microsoft.com/
1. When installing, under “Workloads” select “Desktop development with C++”
1. Under “Individual Components”, select a recent .NET Framework SDK (4.6.1 and 4.8.1 have been verified)

## Install Deadline Cloud Monitor

Deadline Cloud Monitor is used to both manage your credentials for submitting jobs to Deadline Cloud as well as monitoring the status of your jobs.

1. Follow the instructions at https://docs.aws.amazon.com/deadline-cloud/latest/userguide/submitter.html#install-deadline-cloud-monitor
1. Sign in

## Environment Setup

1. (If not already installed) Install a recent version of Python (3.12 has been verified)
1. Make sure your Environment Variables are set correctly. In System Environment Variables, your PATH should include:

- The path to your Python Installation (C:\Program Files\Python312 for example)
- The path to your Python Scripts folder (C:\Program Files\Python312\scripts for example)
- The path to your Unreal binaries (C:\Program Files\Epic Games\UE_5.4\Engine\Binaries\Win64)

## Deadline Software Installation

- clone or download `deadline-cloud-for-unreal-engine` either from the release branch or mainline depending on whether you'd like the most recent tested release or all of the most recent commits.

```
git clone https://github.com/aws-deadline/deadline-cloud-for-unreal-engine.git
cd deadline-cloud-for-unreal-engine
git switch release
```

## Optional - Build and Install Plugin with script

A helper script exists at scripts/build_plugin.py which will optionally automate the next 2 steps for you.  It will attempt to find the latest version of Unreal, build your plugin and python dependencies, and install them in the correct locations.  Settings like the Unreal version to use can be overridden.  See the full help list with:

```
python scripts/build_plugin.py -h
```

To build and install your current copy of deadline-cloud-for-unreal-engine as a submitter with the latest Unreal Engine installation, run:

```
python scripts/build_plugin.py --install
```

If you've installed with this script successfully, you can now skip to "Submitter Installation Complete"

## Build the Plugin

Adjust the first two paths below based on where your installation of Unreal lives, and where you installed deadline-cloud-for-unreal-engine.

From the Unreal Install Batchfiles Folder (Note the ‘package’ parameter can be any new directory, however you’ll want it to be called “UnrealDeadlineCloudService” later):

```
cd C:\Program Files\Epic Games\UE_5.4\Engine\Build\BatchFiles
runuat.bat BuildPlugin -plugin="C:\deadline\deadline-cloud-for-unreal-engine\src\unreal_plugin\UnrealDeadlineCloudService.uplugin" -package="C:\UnrealDeadlineCloudService"
```

- Copy the “package” folder above to your Unreal installation’s Plugins folder (C:\Program Files\Epic Games\UE_5.4\Engine\Plugins\UnrealDeadlineCloudService for example)

## Python Dependencies

There are 4 ways to install the required Python dependencies.

1. If you've built and installed the plugin from the release branch above, you can simply install from pip. Use the following install command, adjusting the paths to your Unreal installation:

```
"C:\Program Files\Epic Games\UE_5.4\Engine\Binaries\ThirdParty\Python3\Win64\python" -m pip install deadline-cloud-for-unreal-engine --target "C:\Program Files\Epic Games\UE_5.4\Engine\Plugins\UnrealDeadlineCloudService\Content\Python\libraries"
```

2.  Alternatively in your .uplugin file (In the above steps this would live at C:\Program Files\Epic Games\UE_5.4\Engine\Plugins\UnrealDeadlineCloudService\UnrealDeadlineCloudService.uplugin) you can add a "PythonRequirements" section which matches the latest release of deadline-cloud-for-unreal-engine in GitHub/PyPi, for example:

```
	"PythonRequirements":
	[
		{

			"Platform": "All",
			"Requirements":
			[
				"deadline-cloud-for-unreal-engine>=0.3.0"
			]
		}
	]
```

Note that you may wish to disable the "strict hash" feature in Unreal's Python settings, or add hash settings for specific library and dependency versions you wish to consume.

3.  If you're pulling from mainline you may have python dependencies which are not yet released to PyPi - you'll need to build and install your local copy which can be done with hatch.  Note that the .whl file will need to be changed to reflect the version which is output by hatch build:

```
// Install hatch if not yet installed
pip install hatch
hatch build
"C:\Program Files\Epic Games\UE_5.4\Engine\Binaries\ThirdParty\Python3\Win64\python" -m pip install dist\deadline_cloud_for_unreal_engine-0.2.2.post21-py3-none-any.whl --target "C:\Program Files\Epic Games\UE_5.4\Engine\Plugins\UnrealDeadlineCloudService\Content\Python\libraries"
```

4.  Lastly, Python dependencies can be installed by the submitter installer.  NOTE - these may be out of date with your code above from the release or mainline branch, and this method should not currently be preferred.

	1. Download submitter installer from Deadline Cloud AWS Console’s Downloads Tab or from within the Deadline Cloud Monitor under Workstation Setup -> Downloads
	1. Run, install for all users. Default install location is fine.
	1. Enable the Unreal Engine Plugin
	1. Make sure the Unreal Engine plugin install path matches where your plugin was copied to (In particular make sure your Unreal version matches)

## Submitter Installation Complete

If you don't need to set up your customer managed fleet you can stop here, or skip down to the "Submit a Test Render" section.

# Create a Customer Managed Fleet

If you don't yet have a CMF set up, you can complete the instructions below as part of the steps titled "Worker host setup" and "Install software for jobs" as you create the CMF with these instructions: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/create-a-cmf.html, and then (If you're using EC2) create an AMI which can function as your CMF worker.

## Create a new Windows EC2 instance to install Unreal on (Optional)

If you’re setting up on a brand new Windows EC2 Instance as your CMF worker node, a g5.2xlarge instance with 200 GB of storage will likely be reasonable minimum:

1. Download the Epic Installer and install the latest version of Unreal (5.2 or higher is required)
1. NVIDIA GRID drivers - Follow Windows instructions - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-nvidia-driver.html#nvidia-GRID-driver

## Install Build Tools

The Unreal Plugin currently must be compiled locally.

1. Install Visual Studio 2022 or later using the Visual Studio Installer from https://visualstudio.microsoft.com/
1. When installing, under “Workloads” select “Desktop development with C++”
1. Under “Individual Components”, select a recent .NET Framework SDK (4.6.1 and 4.8.1 have been verified)

## Environment Setup

1. (If not already installed) Install a recent version of Python (3.12 has been verified)
1. Make sure your Environment Variables are set correctly. In System Environment Variables, your PATH should include:

- The path to your Python Installation (C:\Program Files\Python312 for example)
- The path to your Python Scripts folder (C:\Program Files\Python312\scripts for example)
- The path to your Unreal binaries (C:\Program Files\Epic Games\UE_5.4\Engine\Binaries\Win64)

## Deadline Software Installation

- clone or download `deadline-cloud-for-unreal-engine` either from the release branch or mainline depending on whether you'd like the most recent tested release or all of the most recent commits.  Note that you'll want to ensure your worker version of the libraries is compatible with the version being used from your submitters.

```
git clone https://github.com/aws-deadline/deadline-cloud-for-unreal-engine.git
cd deadline-cloud-for-unreal-engine
git switch release
```

Optional - Build and install plugin and dependencies with script

A helper script exists at scripts/build_plugin.py which will optionally automate the remaining installation steps for you.  It will attempt to find the latest version of Unreal, build your plugin and python dependencies, and install them in the correct locations.  Settings like the Unreal version to use can be overridden.  See the full help list with:

```
python scripts/build_plugin.py -h
```

To build and install your current copy of deadline-cloud-for-unreal-engine as a worker with the latest Unreal Engine installation, run:

```
python scripts/build_plugin.py --install --worker
```

If you've installed with this script successfully, you can now skip to "Submit a Test Render"


```
python -m pip install deadline-cloud-worker-agent
```

The correct version of the adaptor must be installed depending on the version of the submitter being used.  If you are using the version of the submitter from the release branch in GitHub, you can simply install with pip:

```
python -m pip install deadline-cloud-for-unreal-engine
```

If you're using mainline or a custom/in development version of the submitter in order to avoid compatibility issues it's advised to build and install from the same version of code or transfer over the .whl file from your submitter build:

```
// Install hatch if not yet installed
pip install hatch
hatch build
python -m pip install dist\my-built-wheel.whl
```


## Build the Plugin

Adjust the first two paths below based on where your installation of Unreal lives, and where you installed deadline-cloud-for-unreal-engine.

From the Unreal Install Batchfiles Folder (Note the ‘package’ parameter can be any new directory, however you’ll want it to be called “UnrealDeadlineCloudService” later):

```
cd C:\Program Files\Epic Games\UE_5.4\Engine\Build\BatchFiles
runuat.bat BuildPlugin -plugin="C:\deadline\deadline-cloud-for-unreal-engine\src\unreal_plugin\UnrealDeadlineCloudService.uplugin" -package="C:\UnrealDeadlineCloudService"
```

- Copy the “package” folder above to your Unreal installation’s Plugins folder (C:\Program Files\Epic Games\UE_5.4\Engine\Plugins\UnrealDeadlineCloudService for example)

## pywin32

Unreal’s version of python will need pywin32. Pip install using copy of Unreal’s 3rd Party python installation:

```
"C:\Program Files\Epic Games\UE_5.4\Engine\Binaries\ThirdParty\Python3\Win64\python" -m pip install pywin32
```

## Submit a Test Render (Optional)

Assuming you’ve created a CMF and have connected at least one worker that’s had Unreal installed as above, you should be able to submit a test render at this point.

To verify your CMF worker is connected:

On your CMF Worker:

1. Open Task Manager
1. Open the Services tab
1. Find “DeadlineWorker”
1. If you don’t see it listed you’ve likely missed steps (install-deadline-worker in particular) from the CMF host setup steps
1. If the status of the service isn’t currently “Running”, right click it and select start
1. Logs when launching the worker agent to help diagnose installation issues which can cause problems starting the service can be found in C:\ProgramData\Amazon\Deadline\Logs\worker-agent.log\* and C:\ProgramData\Amazon\Deadline\Logs\queue-<queueid>\session-<sessionid>.log

This example will use the Meerkat Demo from the Unreal Marketplace:

1. Start the Epic Games Launcher
1. Install the Meerkat Demo from the Unreal Marketplace
1. Create a Project from the Meerkat Demo
1. Open the Project
1. From the Edit Menu, select Plugins, search for and enable UnrealDeadlineCloudService
1. Restart Unreal if you've enabled the plugin for the first time
1. Under Edit/Project Settings search for the Movie Render Pipeline section
1. For Default Remote Executor, select MoviePipelineDeadlineCloudRemoteExecutor
1. For Default Executor Job, select MoviePipelineDeadlineCloudExecutorJob
1. Under Default Job Settings Classes, Click Add New, and add “DeadlineCloudRenderStepSetting”
1. Now search for the settings for “Deadline Cloud” and ensure that your Status says “AUTHENTICATED” and your Deadline Cloud API says “AUTHORIZED”
1. If it does not appear, first try using the Login button. If that doesn’t work, open your Deadline Cloud Monitor and ensure you're logged in.
1. Open “Deadline Cloud Workstation Configuration”:
1. Under “Global Settings” ensure your AWS Profile is set correctly to your DCM Profile
1. Under “Profile” ensure your Default Farm is set to your farm
1. Under “Farm” ensure your Default Queue is set to your CMF you set up
1. Optionally set your Job Attachments Filesystem to VIRTUAL
1. Under Windows/Cinematics select Movie Render Queue
1. Click Render, and select "Main_SEQ"
1. Click “UnsavedConfig” in the top in the settings column 1. you should see DeadlineCloud settings on the left. This window can then be closed.
1. On the right, drop down “Preset Overrides” (You may need to widen this dialog)
1. Set “Name” to “Unreal Test Job”
1. Set “Maximum retries” to 2
1. Optionally set "Task Chunk Size" to a number higher than 1 - this will tell Deadline Cloud to render the requested number of shots in groups as part of the same task, and may slightly increase performance in some cases.
1. In Job Attachments, under “Input Files” select “Show Auto-Detected” and the list of Auto Detected Files should populate
1. Ready to Go! Hit Render (Remote)
1. You can go to Deadline Cloud Monitor and watch the progress of your job
