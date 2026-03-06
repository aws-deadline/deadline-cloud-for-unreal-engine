# Unreal Engine Dev Setup — Agent Workflow

Step-by-step workflow the agent follows to automate environment setup. Execute each step, validate, and only prompt the user when required.

## Step 0: Verify Windows OS

**Action:** Check OS.

```powershell
[System.Environment]::OSVersion.Platform
```

**If not Windows:** Display "This setup only supports Windows. Unreal Engine development for Deadline Cloud requires Windows OS." and abort.

## Step 1: Check GPU and Drivers

**Action:** Verify NVIDIA GPU.

```powershell
Get-WmiObject Win32_VideoController | Where-Object {$_.Name -like "*NVIDIA*"}
nvidia-smi
```

**If not found:** Inform user GPU/drivers are required. Provide links:
- Local: https://www.nvidia.com/Download/index.aspx
- EC2: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/install-nvidia-driver.html#nvidia-GRID-driver

Wait for user confirmation before continuing.

## Step 2: Enable Windows Long Paths

**Action:** Check and enable.

```powershell
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled"
```

**If not enabled:** Attempt to enable:
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

If that fails (needs admin), instruct user to run as admin or follow: https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation

## Step 3: Verify Python 3.9+

**Action:** Check Python.

```powershell
python --version
```

**If missing or < 3.9:** Attempt install:
```powershell
winget install Python.Python.3.12 --scope machine
```

If winget fails, instruct user to install from https://www.python.org/downloads/ (install for all users). Wait for confirmation.

## Step 4: Verify Build Tools

**Action:** Check for Visual Studio and MSBuild.

```powershell
where.exe msbuild
Get-ChildItem "C:\Program Files\Microsoft Visual Studio" -Directory
```

**If not found:** Inform user Visual Studio with C++ tools is required:
- Download: https://visualstudio.microsoft.com/
- Workload: "Desktop development with C++"
- Individual Components: MSVC build tools (match UE version per https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-visual-studio-development-environment-for-cplusplus-projects-in-unreal-engine)
- Individual Components: .NET Framework SDK (4.6.1 or 4.8.1)

Wait for user confirmation.

## Step 5: Verify Deadline Cloud Monitor

**Action:** Check for Deadline CLI and Monitor.

```powershell
deadline --version
Test-Path "$env:LOCALAPPDATA\DeadlineCloudMonitor\DeadlineCloudMonitor.exe"
```

**If found:** Display version and continue.

**If not found:** Inform user DCM is required. Install from: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/submitter.html#install-deadline-cloud-monitor

Note: The Windows installer includes the Deadline CLI.

## Step 6: Detect Unreal Engine

**Action:** Search default install location.

```powershell
Get-ChildItem "C:\Program Files\Epic Games" -Directory | Where-Object {$_.Name -match "^UE_\d+\.\d+$"} | Sort-Object Name -Descending
```

**If found:** Use newest version, display it, continue.

**If not found:** Prompt user to either:
1. Install UE (5.4+) from https://www.unrealengine.com/download
2. Enter custom installation path

Validate custom path: `Test-Path "$USER_PATH\Engine\Binaries\Win64\UnrealEditor.exe"`

## Step 7: Install Hatch

**Action:** Check and install.

```powershell
hatch --version
```

**If not installed:**
```powershell
python -m pip install hatch
```

Verify with `hatch --version`.

## Step 8: Build and Install Plugin

**Action:** Run the automated build script from the repo root.

```powershell
python scripts/build_plugin.py --ueversion {VERSION} --install
# Or with custom path:
python scripts/build_plugin.py --ueversion {VERSION} --engine-root "{CUSTOM_UE_PATH}" --install
```

Monitor output and report progress. This builds the C++ plugin AND installs Python dependencies.

## Step 9: Verify Environment Variables

**Action:** Check PATH.

```powershell
$env:PATH -split ';' | Select-String "Python"
$env:PATH -split ';' | Select-String "Epic Games"
```

Required on PATH:
- Python install dir (e.g. `C:\Program Files\Python312`)
- Python Scripts dir (e.g. `C:\Program Files\Python312\Scripts`)
- UE binaries (e.g. `C:\Program Files\Epic Games\UE_5.5\Engine\Binaries\Win64`)

If missing, inform user which paths to add.

## Step 10: Display Summary

```
✓ Automated Setup Complete!

Installed:
  - Python: [VERSION]
  - Hatch: [VERSION]
  - Unreal Engine: [VERSION] at [PATH]
  - Plugin built and installed to: [PATH]
```

## Step 11: Enable Plugin in Unreal Engine (MANUAL)

This is the only manual step. Instruct the user:

> The plugin is installed but must be enabled manually in Unreal Engine.
> Follow: https://aws-deadline.github.io/unreal-engine/setup-submitter/#submitter-installation-complete
>
> 1. Open Unreal Engine
> 2. Edit → Plugins → search "UnrealDeadlineCloudService" → enable
> 3. Restart UE
> 4. Configure Movie Render Pipeline settings (see DEVELOPMENT.md "Submit a test render")
> 5. Submit a test render to verify

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `build_plugin.py` can't find UE | Use `--engine-root` to specify custom path |
| MSVC version mismatch | Match exact recommended version for your UE version |
| Long path errors | Ensure Step 2 completed successfully |
| `hatch` not found after install | Restart terminal or add Python Scripts to PATH |
| Plugin not visible in UE | Verify plugin was copied to `Engine\Plugins\UnrealDeadlineCloudService` |
| Credential errors at runtime | Open Deadline Cloud Monitor and sign in |
