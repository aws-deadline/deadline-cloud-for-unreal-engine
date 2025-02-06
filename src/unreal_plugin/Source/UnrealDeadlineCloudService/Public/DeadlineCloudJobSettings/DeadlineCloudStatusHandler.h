// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"

class UDeadlineCloudDeveloperSettings;
/**
 * Deadline Cloud status handler
 */
class UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudStatusHandler
{
    inline static const FName NAME_DirectoryWatcher = "DirectoryWatcher";
	/** Help struct to keep a list of config directory watch handlers */
	struct FConfigWatchedDirInfo
	{
		FDelegateHandle DirectoryWatcherHandle;
		FString FolderPath;
	};

	/** List of config directory watch handlers */
	TArray<FConfigWatchedDirInfo> WatchedDirectories;

	/** Reference to Deadline Cloud settings */
	TWeakObjectPtr<UDeadlineCloudDeveloperSettings> Settings;

public:
	/** Starts tracking directories updates */
	void StartDirectoryWatch();

	/** Stops tracking directories updates */
	void StopDirectoryWatch();

	/**
	 * @param InSettings Deadline Cloud plugin settings
	 */
	explicit FDeadlineCloudStatusHandler(TWeakObjectPtr<UDeadlineCloudDeveloperSettings> InSettings);
	~FDeadlineCloudStatusHandler();
};
