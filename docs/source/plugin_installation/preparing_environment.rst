###############################
Preparing Environment
###############################

#. Get the UE test project. Go to the any folder, where you want to keep your Unreal projects and pull the UE project from GitHub, for example:

    a. Open Command Line and run next commands
    #. git clone https://github.com/casillas2/deadline-cloud-for-unreal
    #. cd deadline-cloud-for-unreal/test_projects
    #. git lfs fetch --all

    #. Open the File Explorer and go to the project folder and launch the
       **deadline-cloud-for-unreal/test_projects/pull_ue_plugin.bat** file to download the plugin for Unreal.
       This action put the plugin files in *C:/LocalProjects/UnrealDeadlineCloudTest/Plugins/UnrealDeadlineCloudService*

    #. Go to the plugin folder - UnrealDeadlineCloudService and run
       **deadline-cloud-for-unreal/test_projects/Plugins/UnrealDeadlineCloudService/install_unreal_submitter.bat**.
       This script will download the deadline-cloud and submitter part from deadline-cloud-for-unreal to the *UnrealDeadlineCloudService/Content/Python/libraries*
