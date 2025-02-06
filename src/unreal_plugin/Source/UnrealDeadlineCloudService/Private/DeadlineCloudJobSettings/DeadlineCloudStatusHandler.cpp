// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.


#include "DeadlineCloudJobSettings/DeadlineCloudStatusHandler.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDeveloperSettings.h"
#include "DirectoryWatcherModule.h"
#include "IDirectoryWatcher.h"

FDeadlineCloudStatusHandler::FDeadlineCloudStatusHandler(TWeakObjectPtr<UDeadlineCloudDeveloperSettings> InSettings)
    : Settings(InSettings)
{
}

FDeadlineCloudStatusHandler::~FDeadlineCloudStatusHandler()
{
    StopDirectoryWatch();
}

void FDeadlineCloudStatusHandler::StopDirectoryWatch()
{
    FDirectoryWatcherModule& DirectoryWatcherModule = FModuleManager::LoadModuleChecked<FDirectoryWatcherModule>(NAME_DirectoryWatcher);
    if (const auto DirectoryWatcher = DirectoryWatcherModule.Get())
    {
        for (auto& WatchedDirectory : WatchedDirectories)
        {
            if (WatchedDirectory.DirectoryWatcherHandle.IsValid())
            {
    			DirectoryWatcher->UnregisterDirectoryChangedCallback_Handle(
					WatchedDirectory.FolderPath, WatchedDirectory.DirectoryWatcherHandle);
				WatchedDirectory.FolderPath.Empty();
			}
		}
	}
}

void FDeadlineCloudStatusHandler::StartDirectoryWatch()
{
	FDirectoryWatcherModule& DirectoryWatcherModule =
	FModuleManager::LoadModuleChecked<FDirectoryWatcherModule>(NAME_DirectoryWatcher);
	if (IDirectoryWatcher* DirectoryWatcher = DirectoryWatcherModule.Get())
	{
		const FString UserDocDir = FPlatformProcess::UserDir();
		FDirectoryPath DirectoryPath;

		FString DocDir;
		const FString UserDir = FPaths::GetPath(UserDocDir.TrimChar('/'));
		TArray<FString> AwsCredPaths = {
			UserDir / FString(".aws"),
			UserDir / FString(".aws") / FString("sso") / FString("cache"),
//		};
//		TArray<FString> DeadlineConfigPaths = {
			UserDir /  FString(".deadline")
		};

		// StopDirectoryWatch();
		for (auto AwsCredPath : AwsCredPaths)
		{
			FConfigWatchedDirInfo WatchedDirectory;
			WatchedDirectory.FolderPath = MoveTemp(AwsCredPath);
			{
				DirectoryWatcher->RegisterDirectoryChangedCallback_Handle(
					WatchedDirectory.FolderPath,
					IDirectoryWatcher::FDirectoryChanged::CreateLambda([this](const TArray<FFileChangeData>& FileChanges)
					{
						Settings->RefreshState();
					}),
					WatchedDirectory.DirectoryWatcherHandle,
					/*Flags*/ 0
				);
			}
			WatchedDirectories.Emplace(WatchedDirectory);
		}
	}
}
