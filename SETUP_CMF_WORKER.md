# Unreal CMF Worker Setup Instructions

This will walk you through setting up an instance to act as a worker as part of a Customer Managed Fleet (CMF).

## Branch to use - release vs mainline

These instructions are updated along with the corresponding code and scripts fairly often.  You'll later need to choose to pull down the code which corresponds to a specific branch. The usual choice is between release which is more stable, or mainline which has the latest changes.  If the version of the instructions you're currently reading doesn't come from the branch you intend to use, you should switch to the instructions from that branch now.  For example, if you're currently reading the mainline version of the instructions but intend to use the release branch, please switch to the release version [here](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/release/SETUP_SUBMITTER_CMF.md)

## Create a new Windows EC2 instance to install Unreal on 

If you’re setting up on a brand new Windows EC2 Instance as your CMF worker node, a g5.2xlarge instance with 200 GB of storage will likely be reasonable minimum:

1. Download the Epic Installer and install the latest version of Unreal (5.2 or higher is required)
1. NVIDIA GRID drivers - Follow Windows instructions - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-nvidia-driver.html#nvidia-GRID-driver

## Install Build Tools

The Unreal Plugin currently must be compiled locally.

1. Install Visual Studio using the Visual Studio Installer from https://visualstudio.microsoft.com/
1. Verify your Visual Studio and build tools version are compatible with your version of Unreal by checking the table [here](https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-visual-studio-development-environment-for-cplusplus-projects-in-unreal-engine?application_version=5.5)
1. Under "Individual Components", ensure that the MSVC build tools version selected ("Latest" by default) matches the recommended version in the table.  Even though the compatibility guidance may suggest a version "or later", build errors sometimes occur when using a newer version than the one listed as "recommended".
1. Under “Individual Components”, select a recent .NET Framework SDK (4.6.1 and 4.8.1 have been verified)
1. Under “Workloads” select “Desktop development with C++”

## Environment Setup

1. (If not already installed) Install a recent version of Python (3.12 has been verified)
1. Make sure your Environment Variables are set correctly. In System Environment Variables, your PATH should include:

- The path to your Python Installation (C:\Program Files\Python312 for example)
- The path to your Python Scripts folder (C:\Program Files\Python312\scripts for example)
- The path to your Unreal binaries (C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\Win64)

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

Configure the Deadline Cloud worker agent by running:

```
install-deadline-worker ^
  --farm-id FARM_ID ^
  --fleet-id FLEET_ID ^
  --region REGION ^
  --allow-shutdown
```

If you've installed with this script and configured worker agent successfully, you can now skip to "Start Deadline Cloud Worker Agent Service"


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
cd C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles
runuat.bat BuildPlugin -plugin="C:\deadline\deadline-cloud-for-unreal-engine\src\unreal_plugin\UnrealDeadlineCloudService.uplugin" -package="C:\UnrealDeadlineCloudService"
```

- Copy the “package” folder above to your Unreal installation’s Plugins folder (C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService for example)

## pywin32

Unreal’s version of python will need pywin32. Pip install using copy of Unreal’s 3rd Party python installation:

```
"C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\ThirdParty\Python3\Win64\python" -m pip install pywin32
```

## Start Deadline Cloud Worker Agent Service

On your CMF Worker instance:

1. Open “Task Manager“
1. Click on the “Services“ tab on the right
1. Find “DeadlineWorker”
	1. If you don’t see it listed you’ve likely missed steps (install-deadline-worker in particular) from [the CMF host setup steps](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/worker-host.html#worker-agent-config)
1. If the status of the service isn’t currently “Running”, right click it and select “Start“
1. If your “DeadlineWorker“ service isn't starting, check the worker agent launch logs in these locations:
	1. C:\ProgramData\Amazon\Deadline\Logs\worker-agent.log
	1. C:\ProgramData\Amazon\Deadline\Logs\queue-<queueid>\session-<sessionid>.log
