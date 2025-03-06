// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.


#include "DeadlineCloudJobSettings/DeadlineCloudDeveloperSettings.h"


UDeadlineCloudDeveloperSettings::UDeadlineCloudDeveloperSettings()
{
    // UE_LOG(LogTemp, Log, TEXT("UDeadlineCloudDeveloperSettings::UDeadlineCloudDeveloperSettings()"));
    // if (const auto SettingsLib = UDeadlineCloudSettingsLibrary::Get())
    // {
    //     WorkStationConfiguration.Global.AWS_Profile = SettingsLib->GetProfile();
    //     UE_LOG(LogTemp, Log, TEXT("Update setting AWS profile: %s"), *WorkStationConfiguration.Global.AWS_Profile);
    // }
    OnSettingChanged().AddLambda([this](UObject*, const FPropertyChangedEvent& PropertyChangedEvent)
    {
        this->OnSettingsModified(PropertyChangedEvent.GetPropertyName().ToString());
    });
}

FText UDeadlineCloudDeveloperSettings::GetSectionText() const
{
    return NSLOCTEXT("DeadlineCloudDeveloperSettings", "DeadlineCloudDeveloperSettingsSection", "Deadline Cloud");
}

FName UDeadlineCloudDeveloperSettings::GetSectionName() const
{
    return TEXT("DeadlineCloud");
}


// TArray<FString> UDeadlineCloudDeveloperSettings::GetAwsProfiles()
// {
//     if (const auto SettingsLib = UDeadlineCloudSettingsLibrary::Get())
//     {
//     	return SettingsLib->GetProfiles();
// 	}
// 	return TArray<FString>();
// }

/*
void UDeadlineCloudDeveloperSettings::SaveConfig(uint64 Flags, const TCHAR* Filename, FConfigCacheIni* Config, bool bAllowCopyToDefaultObject)
{
	UE_LOG(LogTemp, Log, TEXT("Don't do anything"))
}
*/
