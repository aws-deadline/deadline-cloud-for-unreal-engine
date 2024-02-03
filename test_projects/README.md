# UnrealDeadlineCloudTest

The test Unreal project for demonstrating deadline-cloud-for-unreal plugin's features.

## Requirements
- Unreal Engine 5.2

## Scripts
We provide additional scripts to make it easy to do some routine stuff while getting the project
- [pull_ue_plugin.bat](pull_ue_plugin.bat) \
Put the UE plugin UnrealDeadlineCloudService files in ./UnrealDeadlineCloudTest/Plugins
- [delete_git_source.bat](delete_git_source.bat) \
[WIP] During testing, we noticed that synchronizing the session directory with the S3 bucket while running jobs ends 
with an error related to copying files from the “.git” and “Source” folders inside of UnrealDeadlineCloudService plugin 
directory under UE project. To avoid the errors, just remove those folders from the directory via that script

## License

This project is licensed under the Apache-2.0 License. 
