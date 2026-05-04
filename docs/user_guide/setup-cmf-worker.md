# Customer Managed Fleet (CMF) Worker Setup

This guide walks you through setting up an EC2 instance as a CMF worker for AWS Deadline Cloud with Unreal Engine.

## Overview

**CMF vs SMF Differences:**
- **CMF**: Manual installation of Unreal Engine and `deadline-cloud-worker-agent` on worker hosts
- **SMF**: Unreal Engine automatically available through the `deadline-cloud` Conda channel; `deadline-cloud-worker-agent` pre-installed on workers

## Choose Your Branch

Select the appropriate branch for your deployment:

| Branch | Stability | Use Case |
|--------|-----------|----------|
| **release** | Stable | Production deployments |
| **mainline** | Latest | Development/testing |

> **Compatibility**: Ensure your worker version matches your submitter version to avoid compatibility issues.

## EC2 Instance Setup

### Recommended Instance Configuration

- **Instance Type**: `g5.2xlarge` or higher
- **Storage**: 200 GB minimum
- **OS**: Windows Server 2019 or 2022

### Software Installation

**1. Install Unreal Engine**

1. Download the Epic Games Launcher
2. Install Unreal Engine 5.4 or higher

> **Note**: Unreal Engine 5.4+ is required for Deadline Cloud compatibility.

**2. Install NVIDIA GRID Drivers**

- Follow the [AWS NVIDIA GRID driver installation guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-nvidia-driver.html#nvidia-GRID-driver)
- Required for GPU-accelerated rendering on EC2 instances

## Install Build Tools

The Unreal plugin must be compiled locally.

1. Install Visual Studio from https://visualstudio.microsoft.com/
2. Verify your Visual Studio and build tools version are compatible with your Unreal version by checking the [UE Visual Studio setup guide](https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-visual-studio-development-environment-for-cplusplus-projects-in-unreal-engine?application_version=5.5)
3. Under **Individual Components**, ensure the MSVC build tools version matches the recommended version in the table (not just "Latest")
4. Under **Individual Components**, select a recent .NET Framework SDK (4.6.1 and 4.8.1 have been verified)
5. Under **Workloads**, select "Desktop development with C++"

## Environment Setup

1. Install Python 3.12 (if not already installed)
2. Add the following to your system `PATH`:
   - Python installation directory (e.g., `C:\Program Files\Python312`)
   - Python Scripts directory (e.g., `C:\Program Files\Python312\Scripts`)
   - Unreal Engine binaries (e.g., `C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\Win64`)

## Deadline Software Installation

Clone the repository:

```bat
git clone https://github.com/aws-deadline/deadline-cloud-for-unreal-engine.git
cd deadline-cloud-for-unreal-engine
git switch release
```

### Option A: Automated Installation (Recommended)

A helper script automates the build, plugin installation, and worker dependency setup:

```bat
python scripts/build_plugin.py --install --worker
```

This will:
- Find your Unreal Engine installation
- Build the plugin binaries
- Install the Python wheel and adaptor bundle into the plugin
- Install `deadline-cloud-worker-agent` and `pywin32`

To see all options (e.g., targeting a specific UE version):

```bat
python scripts/build_plugin.py -h
```

After the script completes, configure the worker agent:

```bat
install-deadline-worker ^
  --farm-id FARM_ID ^
  --fleet-id FLEET_ID ^
  --region REGION ^
  --allow-shutdown
```

Then skip to [Start Deadline Cloud Worker Agent Service](#start-deadline-cloud-worker-agent-service).

### Option B: Manual Installation

If you prefer to install components individually, follow these steps:

#### 1. Install the Worker Agent

```bat
python -m pip install deadline-cloud-worker-agent
```

#### 2. Build and Install the Plugin

From the Unreal Engine BatchFiles directory:

```bat
cd "C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles"
runuat.bat BuildPlugin -plugin="C:\deadline-cloud-for-unreal-engine\src\unreal_plugin\UnrealDeadlineCloudService.uplugin" -package="C:\UnrealDeadlineCloudService"
```

Copy the output folder to the Unreal Engine Plugins directory:

```bat
xcopy /E /I "C:\UnrealDeadlineCloudService" "C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService"
```

#### 3. Install the Python Wheel into the Plugin

Build and install the Python package into the plugin's libraries folder:

```bat
pip install hatch
hatch build
"C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\ThirdParty\Python3\Win64\python" -m pip install dist\deadline_cloud_for_unreal_engine-*.whl --target "C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService\Content\Python\libraries" --force-reinstall
```

#### 4. Build the Adaptor Bundle

The adaptor bundle is attached to each job and runs the adaptor on the worker:

```bat
python scripts/adaptorBundle.py --output "C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService\Content\Python\adaptor_bundle"
```

#### 5. Install pywin32 for Unreal's Python

```bat
"C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\ThirdParty\Python3\Win64\python" -m pip install pywin32
```

#### 6. Configure the Worker Agent

```bat
install-deadline-worker ^
  --farm-id FARM_ID ^
  --fleet-id FLEET_ID ^
  --region REGION ^
  --allow-shutdown
```

### Adaptor Installation

Starting with version 1.0.0, the adaptor is bundled with each job submission as a job attachment and **does not require separate installation on the worker**.

<details>
<summary>Legacy: Manual adaptor installation (submitter versions older than 1.0.0)</summary>

If your submitter is older than 1.0.0, install the adaptor manually:

```bat
python -m pip install deadline-cloud-for-unreal-engine
```

For development/mainline builds, build from source to ensure version compatibility:

```bat
pip install hatch
hatch build
python -m pip install dist\deadline_cloud_for_unreal_engine-*.whl
```

</details>

## Start Deadline Cloud Worker Agent Service

1. Open **Task Manager** and go to the **Services** tab
2. Find **DeadlineWorker**
   - If not listed, you may have missed the `install-deadline-worker` step. See the [CMF host setup docs](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/worker-host.html#worker-agent-config).
3. Right-click and select **Start** if the service is not running

**Troubleshooting:** If the service fails to start, check these logs:
- `C:\ProgramData\Amazon\Deadline\Logs\worker-agent.log`
- `C:\ProgramData\Amazon\Deadline\Logs\queue-<queueid>\session-<sessionid>.log`
