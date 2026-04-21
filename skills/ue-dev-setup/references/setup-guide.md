# Unreal Engine Dev Setup — Agent Workflow

Step-by-step workflow the agent follows to automate environment setup. Execute each step, validate, and only prompt the user when required.

> **Source of truth:** The canonical setup instructions live in
> [docs/user_guide/setup-submitter.md](../../../docs/user_guide/setup-submitter.md) and
> [DEVELOPMENT.md](../../../DEVELOPMENT.md).
> This guide tells the agent *how to automate* those steps — refer to the source docs for full details.

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

**If not found:** Inform user GPU/drivers are required. Refer to the NVIDIA driver instructions in `docs/user_guide/setup-submitter.md`.

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

If winget fails, instruct user to install from https://www.python.org/downloads/. Wait for confirmation.

## Step 4: Verify Build Tools

**Action:** Check for Visual Studio and MSBuild.

```powershell
where.exe msbuild
Get-ChildItem "C:\Program Files\Microsoft Visual Studio" -Directory
```

**If not found:** Attempt install via winget:
```powershell
winget install Microsoft.VisualStudio.2022.Community --override "--add Microsoft.VisualStudio.Workload.NativeDesktop --passive"
```

If winget fails, inform user to install manually. Refer to `docs/user_guide/setup-submitter.md` for version requirements. Wait for user confirmation.

## Step 5: Verify Deadline Cloud Monitor

**Action:** Check for Deadline CLI and Monitor.

```powershell
deadline --version
Test-Path "$env:LOCALAPPDATA\DeadlineCloudMonitor\DeadlineCloudMonitor.exe"
```

**If not found:** Deadline Cloud Monitor must be downloaded manually from the AWS console. Instruct user to download and install it, then re-run `deadline --version` to confirm. Refer to `docs/user_guide/setup-submitter.md` for details.

## Step 6: Detect Unreal Engine

**Action:** Search default install location.

```powershell
Get-ChildItem "C:\Program Files\Epic Games" -Directory | Where-Object {$_.Name -match "^UE_\d+\.\d+$"} | Sort-Object Name -Descending
```

**If found:** Use newest version, display it, continue.

**If not found:** Prompt user to install UE (5.4+) or enter custom path. Validate: `Test-Path "$USER_PATH\Engine\Binaries\Win64\UnrealEditor.exe"`

## Step 7: Install Hatch

**Action:** Check and install.

```powershell
hatch --version
```

**If not installed:**
```powershell
python -m pip install hatch
```

## Step 8: Build and Install Plugin

**Action:** Run the automated build script from the repo root.

```powershell
python scripts/build_plugin.py --ueversion {VERSION} --install
```

## Step 9: Verify Environment Variables

**Action:** Check PATH includes Python and UE binaries.

```powershell
$env:PATH -split ';' | Select-String "Python"
$env:PATH -split ';' | Select-String "Epic Games"
```

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

## Step 11: Enable Plugin and Test (MANUAL)

This is the only manual step. Refer user to the "Submit a Test Render" section in `docs/user_guide/setup-submitter.md`.

## Troubleshooting

Refer to the Troubleshooting section in `DEVELOPMENT.md` for common issues and solutions.
