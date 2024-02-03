:: 0. Get url from env
set DEADLINE_CLOUD_FOR_UNREAL_GIT_URL=https://github.com/casillas2/deadline-cloud-for-unreal-engine.git
set DEADLINE_CLOUD_FOR_UNREAL_GIT_BRANCH=release

set DEADLINE_CLOUD_GIT_URL=https://github.com/casillas2/deadline-cloud.git
set DEADLINE_CLOUD_GIT_BRANCH=release

:: 1. Remove all files from Content/Python/libraries
rmdir /S /Q Content\Python\libraries

:: 2. Cloning deadline-cloud-for-unreal, deadline-cloud
mkdir Content\Python\libraries

mkdir tmp
cd tmp

git clone --branch %DEADLINE_CLOUD_FOR_UNREAL_GIT_BRANCH% %DEADLINE_CLOUD_FOR_UNREAL_GIT_URL%
git clone --branch %DEADLINE_CLOUD_GIT_BRANCH% %DEADLINE_CLOUD_GIT_URL%

:: 3. pip install deadline-cloud/ --target=Content/Python/libraries
python -m pip install --target=../Content/Python/libraries deadline-cloud/

:: 4. Copy deadline-cloud-for-unreal/src/deadline/unreal_submitter to Content/Python/libraries folder
echo f | xcopy /s /i AWS.DeadlineCloudForUnreal.Python\src\deadline\unreal_submitter ..\Content\Python\libraries\deadline\unreal_submitter\

:: 5. Delete cloned repos.
cd ..
rmdir /S /Q tmp
