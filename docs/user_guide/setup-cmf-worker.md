# Customer Managed Fleet (CMF) Worker Setup

This guide walks you through setting up an EC2 instance as a CMF worker for AWS Deadline Cloud with Unreal Engine.

## Overview

**CMF vs SMF Differences:**
- **CMF**: Manual installation of Unreal Engine and adaptor on worker hosts
- **SMF**: Automatic availability through `deadline-cloud Conda` channel

## Choose Your Branch

Select the appropriate branch for your deployment:

| Branch | Stability | Use Case |
|--------|-----------|----------|
| **release** | ✅ Stable | Production deployments |
| **mainline** | 🔄 Latest | Development/testing |

> **⚠️ Compatibility**: Ensure your worker version matches your submitter version to avoid compatibility issues.

## EC2 Instance Setup

### Recommended Instance Configuration

**Minimum Specifications:**
- **Instance Type**: g5.2xlarge or higher
- **Storage**: 200 GB minimum
- **OS**: Windows Server 2019/2022

### Software Installation

**1. Install Unreal Engine**
1. Download the Epic Games Launcher
2. Install Unreal Engine 5.3 or higher
   > **📝 Note**: Unreal Engine 5.3+ is required for Deadline Cloud compatibility

**2. Install NVIDIA GRID Drivers**
- Follow the [AWS NVIDIA GRID driver installation guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-nvidia-driver.html#nvidia-GRID-driver)
- Required for GPU-accelerated rendering on EC2 instances

## Install Build Tools

The Unreal Plugin currently must be compiled locally.

1. Install Visual Studio using the Visual Studio Installer from https://visualstudio.microsoft.com/
1. Verify your Visual Studio and build tools version are compatible with your version of Unreal by checking the table [here](https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-visual-studio-development-environment-for-cplusplus-projects-in-unreal-engine?application_version=5.5)
1. Under "Individual Components", ensure that the MSVC build tools version selected ("Latest" by default) matches the recommended version in the table. Even though the compatibility guidance may suggest a version "or later", build errors sometimes occur when using a newer version than the one listed as "recommended".
1. Under "Individual Components", select a recent .NET Framework SDK (4.6.1 and 4.8.1 have been verified)
1. Under "Workloads" select "Desktop development with C++"

## Environment Setup

1. (If not already installed) Install a recent version of Python (3.12 has been verified)
1. Make sure your Environment Variables are set correctly. In System Environment Variables, your PATH should include:

- The path to your Python Installation (C:\Program Files\Python312 for example)
- The path to your Python Scripts folder (C:\Program Files\Python312\scripts for example)
- The path to your Unreal binaries (C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\Win64)

## Deadline Software Installation

- clone or download `deadline-cloud-for-unreal-engine` either from the release branch or mainline depending on whether you'd like the most recent tested release or all of the most recent commits. Note that you'll want to ensure your worker version of the libraries is compatible with the version being used from your submitters.

```
git clone https://github.com/aws-deadline/deadline-cloud-for-unreal-engine.git
cd deadline-cloud-for-unreal-engine
git switch release
```

Optional - Build and install plugin and dependencies with script

A helper script exists at scripts/build_plugin.py which will optionally automate the remaining installation steps for you. It will attempt to find the latest version of Unreal, build your plugin and python dependencies, and install them in the correct locations. Settings like the Unreal version to use can be overridden. See the full help list with:

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

The correct version of the adaptor must be installed depending on the version of the submitter being used. If you are using the version of the submitter from the release branch in GitHub, you can simply install with pip:

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

From the Unreal Install Batchfiles Folder (Note the "package" parameter can be any new directory, however you'll want it to be called "UnrealDeadlineCloudService" later):

```
cd C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles
runuat.bat BuildPlugin -plugin="C:\deadline\deadline-cloud-for-unreal-engine\src\unreal_plugin\UnrealDeadlineCloudService.uplugin" -package="C:\UnrealDeadlineCloudService"
```

- Copy the "package" folder above to your Unreal installation's Plugins folder (C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService for example)

## pywin32

Unreal's version of python will need pywin32. Pip install using copy of Unreal's 3rd Party python installation:

```
"C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\ThirdParty\Python3\Win64\python" -m pip install pywin32
```

## Start Deadline Cloud Worker Agent Service

On your CMF Worker instance:

1. Open "Task Manager"
1. Click on the "Services" tab on the right
1. Find "DeadlineWorker"
	1. If you don't see it listed you've likely missed steps (install-deadline-worker in particular) from [the CMF host setup steps](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/worker-host.html#worker-agent-config)
1. If the status of the service isn't currently "Running", right click it and select "Start"
1. If your "DeadlineWorker" service isn't starting, check the worker agent launch logs in these locations:
	1. C:\ProgramData\Amazon\Deadline\Logs\worker-agent.log
	1. C:\ProgramData\Amazon\Deadline\Logs\queue-<queueid>\session-<sessionid>.log
