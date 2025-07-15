# Unreal Submitter Setup Instructions

This will walk you through setting up your Unreal Submitter and Deadline Cloud Service Managed Fleets (SMF) or Customer Managed Fleets (CMF).

## Branch to use - release vs mainline

These instructions are updated along with the corresponding code and scripts fairly often.  You'll later need to choose to pull down the code which corresponds to a specific branch. The usual choice is between release which is more stable, or mainline which has the latest changes.  If the version of the instructions you're currently reading doesn't come from the branch you intend to use, you should switch to the instructions from that branch now.  For example, if you're currently reading the mainline version of the instructions but intend to use the release branch, please switch to the release version [here](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/release/SETUP_SUBMITTER_CMF.md)

## Create a new Windows EC2 instance to install Unreal on (Optional)

If you’re setting up on a brand new Windows EC2 Instance as your submitter, a g5.2xlarge instance with 200 GB of storage will likely be reasonable minimum:

1. Launch EC2 instance with a valid Instance Profile. This is required to download NVIDIA GRID drivers as instructed below.
1. Download the Epic Installer and install a version of Unreal between versions 5.2 and 5.5.  Note that on version 5.5 with DirectX 11 there's a crash bug which can affect projects rendered using the Deadline Cloud plugin which has been fixed in Unreal's source and can be tracked [here](https://issues.unrealengine.com/issue/UE-276282).  Projects in Deadline Cloud should use DirectX 12 with UE 5.5.
1. NVIDIA GRID drivers - Follow Windows instructions - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-nvidia-driver.html#nvidia-GRID-driver

## Windows Long Paths

Many of the steps below may attempt to create files which exceed the default Windows maximum path length.  Before attempting to build and install the Deadline Cloud for Unreal Engine submitter or adapter on a Windows machine you are strongly encouraged to enable Windows Long path support by following the instructions in one of the options from [this page](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation?tabs=registry), such as by running the PowerShell command [here](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation?tabs=powershell#tabpanel_1_powershell).  Additionally there's currently an [open issue on the worker agent](https://github.com/aws-deadline/deadline-cloud-worker-agent/issues/520) due to a dependency which doesn't ship properly configured to support Windows long paths.  When setting up your workers you MUST follow the workaround steps described in the linked issue to fully support Windows long paths until the issue is resolved.

## Install Build Tools

The Unreal Submitter Plugin currently must be compiled locally.

1. Install Visual Studio using the Visual Studio Installer from https://visualstudio.microsoft.com/
1. Verify your Visual Studio and build tools version are compatible with your version of Unreal by checking the table [here](https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-visual-studio-development-environment-for-cplusplus-projects-in-unreal-engine?application_version=5.5)
1. Under "Individual Components", ensure that the MSVC build tools version selected ("Latest" by default) matches the recommended version in the table.  Even though the compatibility guidance may suggest a version "or later", build errors sometimes occur when using a newer version than the one listed as "recommended".
1. Under “Individual Components”, select a recent .NET Framework SDK (4.6.1 and 4.8.1 have been verified)
1. Under “Workloads” select “Desktop development with C++”

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
cd C:\Program Files\Epic Games\UE_5.5\Engine\Build\BatchFiles
runuat.bat BuildPlugin -plugin="C:\deadline\deadline-cloud-for-unreal-engine\src\unreal_plugin\UnrealDeadlineCloudService.uplugin" -package="C:\UnrealDeadlineCloudService"
```

- Copy the “package” folder above to your Unreal installation’s Plugins folder (C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService for example)

## Python Dependencies

There are 4 ways to install the required Python dependencies.

1. If you've built and installed the plugin from the release branch above, you can simply install from pip. Use the following install command, adjusting the paths to your Unreal installation:

```
"C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\ThirdParty\Python3\Win64\python" -m pip install deadline-cloud-for-unreal-engine --target "C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService\Content\Python\libraries"
```

2.  Alternatively in your .uplugin file (In the above steps this would live at C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService\UnrealDeadlineCloudService.uplugin) you can add a "PythonRequirements" section which matches the latest release of deadline-cloud-for-unreal-engine in GitHub/PyPi, for example:

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

3.  If you're pulling from mainline you may have python dependencies which are not yet released to PyPi - you'll need to build and install your local copy which can be done with hatch.  Note that the .whl file will need to be changed to reflect the version which is output by hatch build:

```
// Install hatch if not yet installed
pip install hatch
hatch build
"C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\ThirdParty\Python3\Win64\python" -m pip install dist\deadline_cloud_for_unreal_engine-0.2.2.post21-py3-none-any.whl --target "C:\Program Files\Epic Games\UE_5.5\Engine\Plugins\UnrealDeadlineCloudService\Content\Python\libraries"
```

4.  Lastly, Python dependencies can be installed by the submitter installer.  NOTE - these may be out of date with your code above from the release or mainline branch, and this method should not currently be preferred.

	1. Download submitter installer from Deadline Cloud AWS Console’s Downloads Tab or from within the Deadline Cloud Monitor under Workstation Setup -> Downloads
	1. Run, install for all users. Default install location is fine.
	1. Enable the Unreal Engine Plugin
	1. Make sure the Unreal Engine plugin install path matches where your plugin was copied to (In particular make sure your Unreal version matches)

## Submitter Installation Complete

If you don't need to set up a new fleet you can stop here, or skip down to the "Submit a Test Render" section.

# Create a Fleet

## Create a Service Managed Fleet (SMF)

1. Follow [Service-managed fleets](https://docs.aws.amazon.com/deadline-cloud/latest/userguide/smf-manage.html) user guide to create a Service Managed Fleet (SMF) if you don't already have one.

## Create a Customer Managed Fleet (CMF)

1. Follow [Create a customer-managed fleet](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/create-a-cmf.html) to create a Customer Managed Fleet (CMF) if you don't already have one.
	1. :warning: When associating your CMF to queues, remove the default Conda queue environment if you do not use it. This will prevent the Conda environment from being used and accidentally using the default SMF specific variables for jobs submitted to your CMF. If you use Conda in your CMF, remember to update "CondaPackages" and "CondaChannels" variables in "Parameter Definition Overrides" during job submission.
1. Follow [Worker host setup and configuration](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/worker-host.html) to set up a worker host.  
1. Follow [Manage access to Windows job user secrets](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/manage-access-windows-secrets.html) to set up the Windows job user secrets for your CMF worker.  
1. Follow [Install and configure software required for jobs](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/install-software.html) to install the software required to run jobs.
1. Follow [SETUP_CMF_WORKER](https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/blob/mainline/SETUP_CMF_WORKER.md) to set up your worker node to run Unreal Engine jobs.

# Submit a Test Render

This example will use the Meerkat Demo from the Unreal Marketplace:

1. Start the “Epic Games Launcher“
1. Install the “Meerkat Demo“ from “Samples“ tab
1. Create a Project from the “Meerkat Demo“, then open it
1. From the “Edit“ Menu, select “Plugins“, search for and enable “UnrealDeadlineCloudService“
1. Restart Unreal if you've enabled the plugin for the first time
1. Under “Edit“/“Project Settings“ search for the “Movie Render Pipeline“ section
	1. For “Default Remote Executor“, select “MoviePipelineDeadlineCloudRemoteExecutor“
	1. For “Default Executor Job“, select “MoviePipelineDeadlineCloudExecutorJob“
	1. Under “Default Job Settings Classes“, click add icon, and add “DeadlineCloudRenderStepSetting”
1. Now search for the settings for “Deadline Cloud” and ensure that your Status says “AUTHENTICATED” and your Deadline Cloud API says “AUTHORIZED”
	1. If it does not appear, first try using the Login button. If that doesn’t work, open your Deadline Cloud Monitor and ensure you're logged in.
	1. In “Deadline Cloud Workstation Configuration” section,
		1. Under “Global Settings”, ensure your AWS Profile is set correctly to your DCM Profile
		1. Under “Profile”, ensure your Default Farm is set to your farm
		1. Under “Farm” ensure your Default Queue is set to your CMF you set up
1. Exit the Project Settings window
1. Click on “Windows“/“Cinematics“, select “Movie Render Queue“
	1. Click “+Render“, and select "Main_SEQ"
	1. Click “UnsavedConfig” in the settings column 
		1. In the popup window, you should see DeadlineCloud settings on the left. This window can then be closed.
	1. On the right, 
		1. In “Preset Overrides” (You may need to widen this dialog)
			1. Set “Name” to “Unreal Test Job”
			1. Set “Maximum retries” to 2
		1. In "Parameter Definition Overrides"
			1. Update the Unreal Engine version in "CondaPackages" if you are using a different version than 5.6
		1. In "Steps Overrides"
			1. Optionally set "Task Chunk Size" to a number higher than 1 - this will tell Deadline Cloud to render the requested number of shots in groups as part of the same task, and may slightly increase performance in some cases.
		1. In Job Attachments, under “Input Files” select “Show Auto-Detected” and the list of Auto Detected Files should populate. 
	1. Ready to Go! Hit “Render (Remote)”. 
1. You can go to Deadline Cloud Monitor and watch the progress of your job. 
