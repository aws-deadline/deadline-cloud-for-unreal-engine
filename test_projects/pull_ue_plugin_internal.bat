mkdir Plugins
cd Plugins

git clone --branch mainline https://github.com/casillas2/deadline-cloud-for-unreal-engine.git

ren AWS.UnrealDeadlineCloudService.Unreal UnrealDeadlineCloudService

cd UnrealDeadlineCloudService

git checkout develop
git lfs fetch --all