mkdir Plugins
cd Plugins

git clone https://github.com/casillas2/deadline-cloud-for-unreal-engine.git

ren AWS.UnrealDeadlineCloudService.Unreal UnrealDeadlineCloudService

cd UnrealDeadlineCloudService

git checkout mainline
git lfs fetch --all