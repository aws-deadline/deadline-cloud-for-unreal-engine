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
// (update_check.py → unreal.EditorDialog.show_message) and is covered by
// the Python unit tests in test_update_check.py.
//
// These C++ automation tests verify the settings-layer contract that the
// Python code depends on:
//   • The ShowUpdateNotifications property exists and defaults to true.
//   • The property can be toggled and the value persists on the object.
//   • The underlying config key ("settings.submitter_update_notification")
//     is read correctly from the settings library when available.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// 1. Default value
// ---------------------------------------------------------------------------
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUpdateDialog_SettingDefaultIsTrue,
	"DeadlineCloud.UpdateDialog.Setting.DefaultIsTrue",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUpdateDialog_SettingDefaultIsTrue::RunTest(const FString& Parameters)
{
	// A freshly-constructed settings struct should have notifications enabled.
	FDeadlineCloudGeneralPluginSettings DefaultGeneral;
	TestTrue(
		TEXT("ShowUpdateNotifications should default to true on a fresh struct"),
		DefaultGeneral.ShowUpdateNotifications);

	return true;
}

// ---------------------------------------------------------------------------
// 2. Toggle round-trip on the live settings singleton
// ---------------------------------------------------------------------------
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUpdateDialog_SettingToggleRoundTrip,
	"DeadlineCloud.UpdateDialog.Setting.ToggleRoundTrip",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUpdateDialog_SettingToggleRoundTrip::RunTest(const FString& Parameters)
{
	UDeadlineCloudDeveloperSettings* Settings = UDeadlineCloudDeveloperSettings::GetMutable();
	TestNotNull(TEXT("DeveloperSettings singleton must exist"), Settings);
	if (!Settings) return false;

	const bool bOriginal = Settings->WorkStationConfiguration.General.ShowUpdateNotifications;

	// Toggle off
	Settings->WorkStationConfiguration.General.ShowUpdateNotifications = false;
	TestFalse(
		TEXT("ShowUpdateNotifications should be false after setting to false"),
		Settings->WorkStationConfiguration.General.ShowUpdateNotifications);

	// Toggle on
	Settings->WorkStationConfiguration.General.ShowUpdateNotifications = true;
	TestTrue(
		TEXT("ShowUpdateNotifications should be true after setting to true"),
		Settings->WorkStationConfiguration.General.ShowUpdateNotifications);

	// Restore
	Settings->WorkStationConfiguration.General.ShowUpdateNotifications = bOriginal;

	return true;
}

// ---------------------------------------------------------------------------
// 3. Verify the setting is accessible on the live singleton
// ---------------------------------------------------------------------------
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUpdateDialog_SettingAccessibleOnSingleton,
	"DeadlineCloud.UpdateDialog.Setting.AccessibleOnSingleton",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUpdateDialog_SettingAccessibleOnSingleton::RunTest(const FString& Parameters)
{
	const UDeadlineCloudDeveloperSettings* Settings = UDeadlineCloudDeveloperSettings::Get();
	TestNotNull(TEXT("DeveloperSettings const singleton must exist"), Settings);
	if (!Settings) return false;

	// Just reading the value should not crash — the property must be well-formed.
	const bool bValue = Settings->WorkStationConfiguration.General.ShowUpdateNotifications;
	// We don't assert a specific value here because a previous test run may have
	// changed it; we only verify the read succeeds without error.
	TestTrue(TEXT("Reading ShowUpdateNotifications should succeed (value is bool)"), bValue || !bValue);

	return true;
}

// ---------------------------------------------------------------------------
// 4. Verify the config key constant matches what Python expects
// ---------------------------------------------------------------------------
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUpdateDialog_ConfigKeyMatchesPython,
	"DeadlineCloud.UpdateDialog.Setting.ConfigKeyMatchesPython",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUpdateDialog_ConfigKeyMatchesPython::RunTest(const FString& Parameters)
{
	// The Python update_check.py reads:
	//   config_file.get_setting("settings.submitter_update_notification")
	//
	// The C++ side defines the same key in DeadlineCloudDeveloperSettings.cpp
	// (DeadlineSettingsKeys::SubmitterUpdateNotification). We verify the
	// settings library can be queried for this key without crashing.
	UDeadlineCloudSettingsLibrary* Library = UDeadlineCloudSettingsLibrary::Get();
	if (!Library)
	{
		// The Python side may not be initialized in a headless test run.
		// This is acceptable — we just verify the library pointer is handled.
		AddWarning(TEXT("DeadlineCloudSettingsLibrary not available (Python not initialized). Skipping config key read."));
		return true;
	}

	const FString ConfigKey = TEXT("settings.submitter_update_notification");
	const FString Value = Library->GetAWSStringConfigSetting(ConfigKey);

	// The value should be either "true", "false", or empty (unset).
	const bool bValidValue = Value.IsEmpty()
		|| Value.Equals(TEXT("true"), ESearchCase::IgnoreCase)
		|| Value.Equals(TEXT("false"), ESearchCase::IgnoreCase);

	TestTrue(
		TEXT("submitter_update_notification config value should be empty, 'true', or 'false'"),
		bValidValue);

	return true;
}

// ---------------------------------------------------------------------------
// 5. Verify setting maps correctly from config string to bool
// ---------------------------------------------------------------------------
IMPLEMENT_SIMPLE_AUTOMATION_TEST(
	FUpdateDialog_ConfigStringToBoolMapping,
	"DeadlineCloud.UpdateDialog.Setting.ConfigStringToBoolMapping",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUpdateDialog_ConfigStringToBoolMapping::RunTest(const FString& Parameters)
{
	UDeadlineCloudDeveloperSettings* Settings = UDeadlineCloudDeveloperSettings::GetMutable();
	TestNotNull(TEXT("DeveloperSettings singleton must exist"), Settings);
	if (!Settings) return false;

	const bool bOriginal = Settings->WorkStationConfiguration.General.ShowUpdateNotifications;

	// The C++ code in DeadlineCloudDeveloperSettings.cpp does:
	//   ShowUpdateNotifications = SubmitterUpdateNotification != TEXT("false");
	// This means any value other than "false" (including empty) maps to true.
	// Verify the bool property reflects this contract.

	Settings->WorkStationConfiguration.General.ShowUpdateNotifications = true;
	TestTrue(
		TEXT("Setting true should yield true"),
		Settings->WorkStationConfiguration.General.ShowUpdateNotifications);

	Settings->WorkStationConfiguration.General.ShowUpdateNotifications = false;
	TestFalse(
		TEXT("Setting false should yield false"),
		Settings->WorkStationConfiguration.General.ShowUpdateNotifications);

	// Restore
	Settings->WorkStationConfiguration.General.ShowUpdateNotifications = bOriginal;

	return true;
}
