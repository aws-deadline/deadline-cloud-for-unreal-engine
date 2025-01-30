REM This batch file is used for automating the update process of a UnrealDeadlineCloudService plugin.
REM
REM Usage:
REM   auto-update-plugin.bat
REM   -Branch {branch_name}
REM   -UnrealVersion {version_number}
REM   -ProjectDir {directory_path}
REM
REM Steps:
REM   1. Update this local repo by checking out the provided branch and pull changes
REM   2. Build UE plugin for provided UE version to %TEMP%\UnrealDeadlineCloudService folder.
REM      It's necessary to have UE installed in default location (C:\Program Files\Epic Games)
REM   3. Copy the built plugin to the Project's Plugins folder under the provided Project DIRECTORY
REM   4. Create pip packages destination folder inside the UE Plugin (Content\Python\Lib\Win64\site-packages)
REM   5. Install deadline-cloud-for-unreal-engine to UE Plugin site-packages in editable mode
REM   6. Clear build TMP folder
REM
REM Example: auto-update-plugin.bat -Branch mainline -UnrealVersion 5.4 -ProjectDir C:\Projects\MyProject


@echo off
setlocal

REM Initialize variables
set "Branch="
set "UnrealVersion="
set "ProjectDir="

:parseArgs
if "%~1"=="" goto endParseArgs

if "%~1"=="-Branch" (
    set "Branch=%~2"
    shift
    shift
    goto parseArgs
)

if "%~1"=="-UnrealVersion" (
    set "UnrealVersion=%~2"
    shift
    shift
    goto parseArgs
)

if "%~1"=="-ProjectDir" (
    set "ProjectDir=%~2"
    shift
    shift
    goto parseArgs
)

:endParseArgs
@echo off
setlocal

REM Initialize variables
set "Branch="
set "UnrealVersion="
set "ProjectDir="

:parseArgs
if "%~1"=="" goto endParseArgs

if "%~1"=="-Branch" (
    set "Branch=%~2"
    shift
    shift
    goto parseArgs
)

if "%~1"=="-UnrealVersion" (
    set "UnrealVersion=%~2"
    shift
    shift
    goto parseArgs
)

if "%~1"=="-ProjectDir" (
    set "ProjectDir=%~2"
    shift
    shift
    goto parseArgs
)


REM If an unknown argument is encountered
shift
goto parseArgs

:endParseArgs

echo Repo BRANCH: %Branch%
echo Unreal Engine VERSION: %UnrealVersion%
echo Unreal Project DIRECTORY: %ProjectDir%


REM 1. Update local repo
echo Update local repo
git checkout %Branch%
git pull origin %Branch%

REM 2. Build UE plugin with provided UE version
echo Build UE plugin with provided UE version
set UPluginPath="%cd%\src\unreal_plugin\UnrealDeadlineCloudService.uplugin"
set OutputDirectory="%TEMP%\UnrealDeadlineCloudService"

REM 3. Build UE Plugin
echo Build UE Plugin
call "C:\Program Files\Epic Games\UE_%UnrealVersion%\Engine\Build\BatchFiles\RunUAT.bat" BuildPlugin -Plugin=%UPluginPath% -Package=%OutputDirectory% -Rocket

REM 4. Copy Plugin to the Project
echo Copy Plugin to the Project
set UProjectPluginPath="%ProjectDir%\Plugins\UnrealDeadlineCloudService"
if not exist %UProjectPluginPath% (
    mkdir %UProjectPluginPath%
)
echo f | xcopy /s /i %OutputDirectory% %UProjectPluginPath%

REM 5. Create pip packages destination folder inside the UE Plugin
echo Create pip packages destination folder inside the UE Plugin
set SitePackagesPath="%UProjectPluginPath%\Content\Python\Lib\Win64\site-packages"
if not exist %SitePackagesPath% (
    mkdir %SitePackagesPath%
)

REM 6. Install deadline-cloud-for-unreal to UE Plugin site-packages in editable mode
echo Install deadline-cloud-for-unreal to UE Plugin site-packages in editable mode
"C:\Program Files\Epic Games\UE_%UnrealVersion%\Engine\Binaries\ThirdParty\Python3\Win64\python.exe" -m pip install -e %cd% --target %SitePackagesPath% --upgrade

REM 7. Clear build TMP folder
echo Clear build TMP folder %OutputDirectory%
rmdir /S /Q %OutputDirectory%

endlocal

pause
