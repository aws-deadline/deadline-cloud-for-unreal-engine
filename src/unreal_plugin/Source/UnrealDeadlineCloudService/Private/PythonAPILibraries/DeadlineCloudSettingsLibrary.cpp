// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "PythonAPILibraries/DeadlineCloudSettingsLibrary.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDeveloperSettings.h"

void UDeadlineCloudSettingsLibrary::InitFromPython()
{
	if (!bInitialized)
	{
		bInitialized = true;
		UDeadlineCloudDeveloperSettings* Settings = UDeadlineCloudDeveloperSettings::GetMutable();
		if (Settings)
		{
			Settings->Refresh();
		}
	}
}