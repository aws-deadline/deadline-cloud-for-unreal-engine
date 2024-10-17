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
echo Unrel Project DIRECTORY: %ProjectDir%


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
