// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "Misc/AutomationTest.h"
#include "CoreMinimal.h"
#include "Engine/Engine.h"
#include "UObject/UObjectGlobals.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDeveloperSettings.h"
#include "PythonAPILibraries/DeadlineCloudSettingsLibrary.h"

// ---------------------------------------------------------------------------
// Spec tests for the update dialog flow.
//
// The update-notification dialog itself is driven by Python
// (update_check.py -> unreal.EditorDialog.show_message) and is covered by
// the Python unit tests in test_update_check.py.
//
// These C++ automation tests verify the settings-layer contract that the
// Python code depends on:
//   - The ShowUpdateNotifications property defaults to true.
//   - The config key "settings.submitter_update_notification" is readable
//     and returns a valid value via the settings library.
//   - Toggling the setting via the UI persists through SaveToFile and
//     is correctly restored by RefreshFromDefaultProfileInternal.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// 1. Default value: a fresh struct should have notifications enabled
// ---------------------------------------------------------------------------
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUpdateDialog_SettingDefaultIsTrue,
	"DeadlineCloud.Offline.UpdateDialog.Setting.DefaultIsTrue",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUpdateDialog_SettingDefaultIsTrue::RunTest(const FString& Parameters)
{
	FDeadlineCloudGeneralPluginSettings DefaultGeneral;
	TestTrue(
		TEXT("ShowUpdateNotifications should default to true on a fresh struct"),
		DefaultGeneral.ShowUpdateNotifications);

	return true;
}

// ---------------------------------------------------------------------------
// 2. Save-and-reload round-trip through the config file
//    Toggles the setting off, saves to the Deadline Cloud config file via
//    SaveToFile(), reloads via RefreshFromDefaultProfileInternal(), and
//    verifies the bool was correctly persisted as the string "false" and
//    mapped back to false. Then does the same for true. Restores original.
// ---------------------------------------------------------------------------
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUpdateDialog_SettingSaveAndReloadRoundTrip,
	"DeadlineCloud.Offline.UpdateDialog.Setting.SaveAndReloadRoundTrip",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUpdateDialog_SettingSaveAndReloadRoundTrip::RunTest(const FString& Parameters)
{
	UDeadlineCloudDeveloperSettings* Settings = UDeadlineCloudDeveloperSettings::GetMutable();
	TestNotNull(TEXT("DeveloperSettings singleton must exist"), Settings);
	if (!Settings) return false;

	UDeadlineCloudSettingsLibrary* Library = UDeadlineCloudSettingsLibrary::Get();
	if (!Library)
	{
		AddWarning(TEXT("DeadlineCloudSettingsLibrary not available (Python not initialized). Skipping round-trip test."));
		return true;
	}

	const bool bOriginal = Settings->WorkStationConfiguration.General.ShowUpdateNotifications;
	const FString ConfigKey = TEXT("settings.submitter_update_notification");

	// --- Toggle OFF, save, reload, verify ---
	Settings->WorkStationConfiguration.General.ShowUpdateNotifications = false;
	Settings->SaveToFile();

	FString SavedValue = Library->GetAWSStringConfigSetting(ConfigKey);
	TestTrue(
		TEXT("Config should contain 'false' after saving with notifications off"),
		SavedValue.Equals(TEXT("false"), ESearchCase::IgnoreCase));

	Settings->RefreshFromDefaultProfileInternal();
	TestFalse(
		TEXT("ShowUpdateNotifications should be false after reload"),
		Settings->WorkStationConfiguration.General.ShowUpdateNotifications);

	// --- Toggle ON, save, reload, verify ---
	Settings->WorkStationConfiguration.General.ShowUpdateNotifications = true;
	Settings->SaveToFile();

	SavedValue = Library->GetAWSStringConfigSetting(ConfigKey);
	TestTrue(
		TEXT("Config should contain 'true' after saving with notifications on"),
		SavedValue.Equals(TEXT("true"), ESearchCase::IgnoreCase));

	Settings->RefreshFromDefaultProfileInternal();
	TestTrue(
		TEXT("ShowUpdateNotifications should be true after reload"),
		Settings->WorkStationConfiguration.General.ShowUpdateNotifications);

	// --- Restore original ---
	Settings->WorkStationConfiguration.General.ShowUpdateNotifications = bOriginal;
	Settings->SaveToFile();

	return true;
}
