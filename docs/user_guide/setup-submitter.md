# Unreal Submitter Setup Guide

This guide walks you through installing and configuring the Unreal Engine submitter plugin for AWS Deadline Cloud, including setup for both Service Managed Fleets (SMF) and Customer Managed Fleets (CMF).

## Choose Your Branch

Select the appropriate branch for your deployment:

| Branch | Stability | Use Case | Recommended For |
|--------|-----------|----------|-----------------|
| **release** | ✅ Stable | Production | Most users |
| **mainline** | 🔄 Latest features | Development/Testing | Advanced users |

> **💡 Tip**: Use the **release** branch for production environments to ensure stability.

## Create a new Windows EC2 instance to install Unreal on (Optional)

If you’re setting up on a brand new Windows EC2 Instance as your submitter, a g5.2xlarge instance with 200 GB of storage will likely be reasonable minimum:

1. Launch EC2 instance with a valid Instance Profile. This is required to download NVIDIA GRID drivers as instructed below.
1. Download the Epic Installer and install a supported version of Unreal Engine (5.4 through 5.8).
    - UE 5.5 has a known crash bug when running with the DirectX 11 plugin, see UI issue #UE-276282. If you need DirectX support on UE 5.5, use DirectX 12+.
1. NVIDIA GRID drivers - Follow Windows instructions - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-nvidia-driver.html#nvidia-GRID-driver

## Submitter Installation

If you're using an AI coding agent, you can automate the entire setup below by running the `ue-dev-setup` skill. Just ask: *"use ue-dev-setup skill to setup this computer"*. The agent will handle as much as it can and prompt you only when manual action is needed.

If you prefer to set up manually, expand the section below.

<details markdown="1">
<summary><strong>Manual Setup Steps</strong></summary>


## Windows Long Paths

Many of the steps below may attempt to create files which exceed the default Windows maximum path length. Before attempting to build and install the Deadline Cloud for Unreal Engine submitter or adapter on a Windows machine you are strongly encouraged to enable Windows Long path support by following the instructions in one of the options from [this page](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation?tabs=registry), such as by running the PowerShell command [here](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation?tabs=powershell#tabpanel_1_powershell). Additionally there's currently an [open issue on the worker agent](https://github.com/aws-deadline/deadline-cloud-worker-agent/issues/520) due to a dependency which doesn't ship properly configured to support Windows long paths. When setting up your workers you MUST follow the workaround steps described in the linked issue to fully support Windows long paths until the issue is resolved.

## Install Build Tools

The Unreal Submitter Plugin currently must be compiled locally.

1. Install Visual Studio using the Visual Studio Installer from https://visualstudio.microsoft.com/
1. Verify your Visual Studio and build tools version are compatible with your version of Unreal by checking the table [here](https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-visual-studio-development-environment-for-cplusplus-projects-in-unreal-engine?application_version=5.5)
1. Under "Individual Components", ensure that the MSVC build tools version selected ("Latest" by default) matches the recommended version in the table. Even though the compatibility guidance may suggest a version "or later", build errors sometimes occur when using a newer version than the one listed as "recommended".
1. Under "Individual Components", select a recent .NET Framework SDK (4.6.1 and 4.8.1 have been verified)
1. Under "Workloads" select "Desktop development with C++"

## Install Deadline Cloud Monitor

Deadline Cloud Monitor is used to both manage your credentials for submitting jobs to Deadline Cloud as well as monitoring the status of your jobs.

1. Follow the instructions at https://docs.aws.amazon.com/deadline-cloud/latest/userguide/submitter.html#install-deadline-cloud-monitor
1. Sign in

## Environment Setup

1. (If not already installed) Install a recent version of Python for all users (3.12 has been verified)
1. Make sure your Environment Variables are set correctly. In System Environment Variables, your PATH should include:

- The path to your Python Installation (C:\Program Files\Python312 for example)
- The path to your Python Scripts folder (C:\Program Files\Python312\scripts for example)
- The path to your Unreal binaries (C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\Win64)

## Deadline Software Installation

- clone or download `deadline-cloud-for-unreal-engine` either from the release branch or mainline depending on whether you'd like the most recent tested release or all of the most recent commits.

```
git clone https://github.com/aws-deadline/deadline-cloud-for-unreal-engine.git
cd deadline-cloud-for-unreal-engine
git switch release
```

## Optional - Build and Install Plugin with script

A helper script exists at scripts/build_plugin.py which will optionally automate the next 2 steps for you. It will attempt to find the latest version of Unreal, build your plugin and python dependencies, and install them in the correct locations. Settings like the Unreal version to use can be overridden. See the full help list with:

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

From the Unreal Install Batchfiles Folder (Note the ‘package’ parameter can be any new directory, however you’ll want it to be called "UnrealDeadlineCloudService" later):

```
cd C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles
runuat.bat BuildPlugin -plugin="C:\deadline\deadline-cloud-for-unreal-engine\src\unreal_plugin\UnrealDeadlineCloudService.uplugin" -package="C:\UnrealDeadlineCloudService"
```

- Copy the "package" folder above to your Unreal installation’s Plugins folder (C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService for example)

## Python Dependencies

There are 4 ways to install the required Python dependencies.

_1._ If you've built and installed the plugin from the release branch above, you can simply install from pip. Use the following install command, adjusting the paths to your Unreal installation:

```
"C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\ThirdParty\Python3\Win64\python" -m pip install deadline-cloud-for-unreal-engine --target "C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService\Content\Python\libraries"
```

_2._ Alternatively in your .uplugin file (In the above steps this would live at C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService\UnrealDeadlineCloudService.uplugin) you can add a "PythonRequirements" section which matches the latest release of deadline-cloud-for-unreal-engine in GitHub/PyPi, for example:

```
	"PythonRequirements":
	[
		{

			"Platform": "All",
			"Requirements":
			[
				"deadline-cloud-for-unreal-engine>=0.5.0"
			]
		}
	]
```

Note that you may wish to disable the "strict hash" feature in Unreal's Python settings, or add hash settings for specific library and dependency versions you wish to consume.

_3._ If you're pulling from mainline you may have python dependencies which are not yet released to PyPi - you'll need to build and install your local copy which can be done with hatch. Note that the .whl file will need to be changed to reflect the version which is output by hatch build:

```
// Install hatch if not yet installed
pip install hatch
hatch build
"C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\ThirdParty\Python3\Win64\python" -m pip install dist\deadline_cloud_for_unreal_engine-0.2.2.post21-py3-none-any.whl --target "C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService\Content\Python\libraries"
```

_4._ Lastly, Python dependencies can be installed by the submitter installer. NOTE - these may be out of date with your code above from the release or mainline branch, and this method should not currently be preferred.

1. Download submitter installer from Deadline Cloud AWS Console’s Downloads Tab or from within the Deadline Cloud Monitor under Workstation Setup -> Downloads
1. Run, install for all users. Default install location is fine.
1. Enable the Unreal Engine Plugin
1. Make sure the Unreal Engine plugin install path matches where your plugin was copied to (In particular make sure your Unreal version matches)

</details>

# Create a Fleet

If you already have a Windows fleet and don't need to set up a new fleet, you can stop here or skip down to the "Submit a Test Render" section.

## Create a Service Managed Fleet (SMF)

1. Follow [Service-managed fleets](https://docs.aws.amazon.com/deadline-cloud/latest/userguide/smf-manage.html) user guide to create a Service Managed Fleet (SMF) if you don't already have one.
	On [Service Managed Fleets (SMF)](https://docs.aws.amazon.com/deadline-cloud/latest/userguide/smf-manage.html), the Unreal Engine and adaptor are automatically available via the `deadline-cloud-v2` and `deadline-cloud` Conda channels with the [default Queue Environment](https://docs.aws.amazon.com/deadline-cloud/latest/userguide/create-queue-environment.html#conda-queue-environment). You are ready to start rendering now! Continue with "Submit a Test Render" section below to submit a test render job.

## Create a Customer Managed Fleet (CMF)

1. Follow [Create a customer-managed fleet](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/create-a-cmf.html) to create a Customer Managed Fleet (CMF) if you don't already have one.
	1. :warning: When associating your CMF to queues, remove the default Conda queue environment if you do not use it. This will prevent the Conda environment from being used and accidentally using the default SMF specific variables for jobs submitted to your CMF. If you use Conda in your CMF, remember to update "CondaPackages" and "CondaChannels" variables in "Parameter Definition Overrides" during job submission.
1. Follow [Worker host setup and configuration](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/worker-host.html) to set up a worker host. 
1. Follow [Manage access to Windows job user secrets](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/manage-access-windows-secrets.html) to set up the Windows job user secrets for your CMF worker. 
1. Follow [Install and configure software required for jobs](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/install-software.html) to install the software required to run jobs.
1. Follow [CMF Worker Setup Guide](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/docs/user_guide/setup-cmf-worker.md) to set up your worker node to run Unreal Engine jobs.

# Submit a Test Render

This example will use the Meerkat Demo from the Unreal Marketplace:

1. Start the "Epic Games Launcher"
1. Install the "Meerkat Demo" from "Samples" tab
1. Create a Project from the "Meerkat Demo", then open it
1. From the "Edit" Menu, select "Plugins", search for and enable "UnrealDeadlineCloudService"
1. Restart Unreal if you've enabled the plugin for the first time
1. Under "Edit"/"Project Settings" search for the "Movie Render Pipeline" section
	1. For "Default Remote Executor", select "MoviePipelineDeadlineCloudRemoteExecutor"
	1. For "Default Executor Job", select "MoviePipelineDeadlineCloudExecutorJob"
	1. Under "Default Job Settings Classes", click add icon, and add "DeadlineCloudRenderStepSetting"
1. Search for "Deadline Cloud" settings and verify authentication:
	1. Ensure your Status shows "AUTHENTICATED" and Deadline Cloud API shows "AUTHORIZED"
	1. If it does not appear, first try using the Login button. If that doesn’t work, open your Deadline Cloud Monitor and ensure you're logged in.
	1. In "Deadline Cloud Workstation Configuration" section,
		1. Under "Global Settings", ensure your AWS Profile is set correctly to your DCM Profile
		1. Under "Profile", ensure your Default Farm is set to your farm
		1. Under "Farm", ensure your Default Queue is set to a queue that is associated with the fleet you set up above.
1. Exit the Project Settings window
1. Click on "Windows"/"Cinematics", select "Movie Render Queue"
	1. Click "+Render", and select "Main_SEQ"
	1. Click "UnsavedConfig" in the settings column 
		1. In the popup window, you should see DeadlineCloud settings on the left. This window can then be closed.
	1. On the right side of the dialog, configure the job settings:
		1. Under "Preset Overrides" (you may need to widen this dialog):
			1. Expand "Job Shared Settings":
				1. Set "Name" to "Unreal Test Job"
				1. Set "Maximum retries" to 2
			1. Expand "Job Attachments":
				1. Under "Input Files", select "Show Auto-Detected" 
				1. Verify that the list of Auto Detected Files populates correctly
		1. Under "Job Template Overrides":
			1. Update the Unreal Engine version in "CondaPackages" if you are using a different version than 5.6
				1. Note: Unreal Engine version autodetection is coming in a future release
		
	1. Ready to Go! Hit "Render (Remote)". 
1. You can go to Deadline Cloud Monitor and watch the progress of your job. 


# Submission Hooks (Pre-GUI)

The submitter runs **pre-GUI** submission hooks sourced from `DEADLINE_HOOKS_DIR`. A pre-GUI hook runs when a Deadline Cloud job's **Details panel is built**, letting a studio pre-populate the job's shared settings (name, description, priority, initial state, maximum failed tasks / retries) and template parameters *before* the artist reviews them.

## Enable pre-GUI hooks

1. Set `DEADLINE_HOOKS_DIR` to a directory containing a `hooks.yaml` with a `preGUI` entry (see the Deadline Cloud submission-hooks documentation for the file format). This environment variable must be set **before** you launch Unreal Editor.
1. Allow environment-sourced hooks:
	```
	deadline config set settings.allow_environment_hooks true
	```
1. (Optional) Skip the per-run confirmation dialog:
	```
	deadline config set settings.auto_accept true
	```
	When `auto_accept` is `false` (the default), opening a job's Details panel shows a confirmation dialog listing the hooks that will run; the hook applies only after you accept.

## When pre-GUI hooks run

Pre-GUI hooks are **panel-tied** — they run when a job's Deadline Cloud Details panel is built:

- **Data asset** — when you open a `DeadlineCloudRenderJob` (`UDeadlineCloudJob`) data asset in the editor.
- **Movie Render Queue** — when you select a Deadline Cloud job in the Movie Render Queue so its **Preset Overrides** panel is shown. Because **Render (Remote)** submits every job in the queue, open each job you want hooked at least once; a job whose panel is never opened is submitted without the pre-GUI hook applied.

A value a hook sets is skipped (and surfaced as an editor notification instead of written to the job) when it fails the panel's validation, matches no field, or names a parameter the submitter resolves itself at submit time (for example `ProjectFilePath`, `ExtraCmdArgs`, `Frames`, or Perforce settings).


# Update Notifications

The submitter plugin automatically checks for newer releases on GitHub when Unreal Editor starts. If an update is available, a dialog will prompt you to visit the release page.

To deactivate update notifications, uncheck "Show submitter update notifications" under "General Settings" in the Deadline Cloud settings panel (Edit > Project Settings > Plugins > Deadline Cloud).

Alternatively, you can use the CLI:

```
deadline config set settings.submitter_update_notification false
```

To re-enable:

```
deadline config set settings.submitter_update_notification true
```
