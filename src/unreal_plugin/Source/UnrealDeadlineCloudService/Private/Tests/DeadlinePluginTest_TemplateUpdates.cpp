// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "Misc/AutomationTest.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "Serialization/ObjectReader.h"
#include "Serialization/ObjectWriter.h"
#include "UObject/Package.h"
#include "Misc/FileHelper.h"
#include "Misc/App.h"
#include "Misc/EngineVersion.h"
#include "HAL/FileManager.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDeadlineCloudTemplateUpdates,
	"DeadlineCloud.Offline.MRQ.TemplateUpdates",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDeadlineCloudTemplateUpdates::RunTest(const FString& Parameters)
{
	auto Parameter = [](const FString& Name, const FString& Value, EValueType Type = EValueType::STRING)
	{
		FParameterDefinition Result;
		Result.Name = Name;
		Result.Value = Value;
		Result.Type = Type;
		return Result;
	};
	auto* Queue = NewObject<UMoviePipelineQueue>();
	auto* Preset = NewObject<UDeadlineCloudRenderJob>();
	Preset->ParameterDefinition.Parameters = {
		Parameter(TEXT("CondaChannels"), TEXT("studio-channel")),
		Parameter(TEXT("Removed"), TEXT("old")),
		Parameter(TEXT("ChangedType"), TEXT("invalid-integer")),
		Parameter(TEXT("HiddenByArtist"), TEXT("private"))
	};
	Preset->GetHiddenManager().Add(TEXT("HiddenByArtist"));
	TArray<FParameterDefinition> Current = {
		Parameter(TEXT("CondaChannels"), TEXT("new-default")),
		Parameter(TEXT("IgnorePlugins"), TEXT("false")),
		Parameter(TEXT("ChangedType"), TEXT("1"), EValueType::INT),
		Parameter(TEXT("HiddenByArtist"), TEXT("default")),
		Parameter(TEXT("Internal"), TEXT("internal-default"))
	};
	Current[1].UserInterfaceControl = EUserInterfaceControl::DROPDOWN_LIST;
	Current.Last().UserInterfaceControl = EUserInterfaceControl::HIDDEN;
	int32 PresetNotifications = 0;
	Preset->GetHiddenManager().OnChanged.BindLambda([&]() { ++PresetNotifications; });

	for (int32 Index = 0; Index < 100; ++Index)
	{
		auto* Job = Cast<UMoviePipelineDeadlineCloudExecutorJob>(
			Queue->AllocateNewJob(UMoviePipelineDeadlineCloudExecutorJob::StaticClass()));
		Job->JobPreset = Preset;
		Job->JobTemplateOverrides.Parameters = {
			Parameter(TEXT("CondaChannels"), FString::Printf(TEXT("artist-%d"), Index)),
			Parameter(TEXT("Removed"), TEXT("old")),
			Parameter(TEXT("ChangedType"), TEXT("saved-string"))
		};
		Job->PresetOverrides.JobSharedSettings.Priority = 73;
		TestTrue(TEXT("Detect stale definitions"), Job->ReconcileJobTemplateParameters(Current, false));
		TestEqual(TEXT("Preview preserves old overrides"), Job->JobTemplateOverrides.Parameters[1].Name, FString(TEXT("Removed")));
		TestTrue(TEXT("Apply update"), Job->ReconcileJobTemplateParameters(Current, true));
		TestEqual(TEXT("Keep each job's value"), Job->JobTemplateOverrides.Parameters[0].Value, FString::Printf(TEXT("artist-%d"), Index));
		TestEqual(TEXT("New parameter default"), Job->JobTemplateOverrides.Parameters[1].Value, FString(TEXT("false")));
		TestEqual(TEXT("New parameter UI"), Job->JobTemplateOverrides.Parameters[1].UserInterfaceControl, EUserInterfaceControl::DROPDOWN_LIST);
		TestEqual(TEXT("Changed type uses new default"), Job->JobTemplateOverrides.Parameters[2].Value, FString(TEXT("1")));
		TestEqual(TEXT("Obsolete and hidden parameters excluded"), Job->JobTemplateOverrides.Parameters.Num(), 3);
		TestEqual(TEXT("Shared settings preserved"), Job->PresetOverrides.JobSharedSettings.Priority, 73);
		TestFalse(TEXT("Update is idempotent"), Job->ReconcileJobTemplateParameters(Current, false));
	}
	TestEqual(TEXT("Shared preset keeps its value"), Preset->ParameterDefinition.Parameters[0].Value, FString(TEXT("studio-channel")));
	TestEqual(TEXT("Shared preset definitions updated"), Preset->ParameterDefinition.Parameters.Num(), 5);
	TestEqual(TEXT("Shared preset is refreshed once"), PresetNotifications, 1);
	Preset->GetHiddenManager().OnChanged.Unbind();

	auto* CondaPreset = NewObject<UDeadlineCloudRenderJob>();
	auto* CondaJob = NewObject<UMoviePipelineDeadlineCloudExecutorJob>(Queue);
	CondaJob->JobPreset = CondaPreset;
	const TArray<FParameterDefinition> CondaDefaults = {
		Parameter(TEXT("CondaPackages"), TEXT("unrealengine=0.0")),
		Parameter(TEXT("CondaChannels"), TEXT("template-channel"))
	};
	const FString EnginePackage = FString::Printf(TEXT("unrealengine=%d.%d"),
		FEngineVersion::Current().GetMajor(), FEngineVersion::Current().GetMinor());
	const FString ChannelOverride = FPlatformMisc::GetEnvironmentVariable(TEXT("DEADLINE_CONDA_CHANNELS"));
	for (int32 Mode = 0; Mode < 3; ++Mode)
	{
		const EValueType SavedType = Mode == 1 ? EValueType::INT : EValueType::STRING;
		CondaPreset->ParameterDefinition.Parameters = Mode == 0 ? TArray<FParameterDefinition>{} : TArray<FParameterDefinition>{
			Parameter(TEXT("CondaPackages"), TEXT("unrealengine=9.9"), SavedType),
			Parameter(TEXT("CondaChannels"), TEXT("artist-channel"), SavedType)
		};
		CondaJob->JobTemplateOverrides.Parameters = CondaPreset->ParameterDefinition.Parameters;
		CondaJob->JobTemplateOverrides.Parameters.Add(Parameter(TEXT("Removed"), TEXT("old")));
		TestTrue(TEXT("Preview detects Conda definition changes"), CondaJob->ReconcileJobTemplateParameters(CondaDefaults, false));
		TestEqual(TEXT("Preview preserves saved parameters"), CondaJob->JobTemplateOverrides.Parameters.Num(), Mode == 0 ? 1 : 3);
		TestTrue(TEXT("Apply Conda definition update"), CondaJob->ReconcileJobTemplateParameters(CondaDefaults, true));
		TestTrue(TEXT("New/retyped engine defaults normalize; matching values stay saved"),
			CondaJob->JobTemplateOverrides.Parameters[0].Value.Contains(Mode == 2 ? TEXT("unrealengine=9.9") : EnginePackage));
		TestEqual(TEXT("New/retyped channels inherit the override; matching values stay saved"),
			CondaJob->JobTemplateOverrides.Parameters[1].Value,
			Mode == 2 ? FString(TEXT("artist-channel")) : ChannelOverride.IsEmpty() ? FString(TEXT("template-channel")) : ChannelOverride);
		TestFalse(TEXT("Conda update is idempotent"), CondaJob->ReconcileJobTemplateParameters(CondaDefaults, false));
	}

	auto* Job = Cast<UMoviePipelineDeadlineCloudExecutorJob>(Queue->GetJobs()[0]);
	Current[0].Value = TEXT("another-default");
	TestFalse(TEXT("Default-only changes do not trigger migration"), Job->ReconcileJobTemplateParameters(Current, false));
	Current[0].UserInterfaceControl = EUserInterfaceControl::MULTILINE_EDIT;
	TestTrue(TEXT("UI control changes trigger migration"), Job->ReconcileJobTemplateParameters(Current, false));
	Current.Last().UserInterfaceControl = EUserInterfaceControl::LINE_EDIT;
	Job->ReconcileJobTemplateParameters(Current, true);
	TestEqual(TEXT("Previously internal parameter becomes editable"), Job->JobTemplateOverrides.Parameters.Num(), 4);
	TestFalse(TEXT("Old template visibility cleared"), Preset->GetHiddenManager().Contains(TEXT("Internal")));
	TestTrue(TEXT("Artist visibility retained"), Preset->GetHiddenManager().Contains(TEXT("HiddenByArtist")));

	Job->LastCheckedPluginVersion = TEXT("1.2.0");
	Job->bTemplateUpdatePrompted = true;
	Job->ReloadDataFromJobPreset();
	TestTrue(TEXT("Reloading a preset re-arms the version check"), Job->LastCheckedPluginVersion.IsEmpty());
	TestFalse(TEXT("Reloading a preset re-arms the prompt"), Job->bTemplateUpdatePrompted);
	Job->LastCheckedPluginVersion = TEXT("1.2.0");
	TArray<uint8> Saved;
	FObjectWriter Writer(Job, Saved);
	auto* Restored = NewObject<UMoviePipelineDeadlineCloudExecutorJob>(Queue);
	FObjectReader Reader(Restored, Saved);
	TestEqual(TEXT("Version marker survives serialization"), Restored->LastCheckedPluginVersion, FString(TEXT("1.2.0")));
	// A marked queue must not need Python or template files to repeat a completed check.
	for (auto* QueueJob : Queue->GetJobs())
	{
		auto* MarkedJob = Cast<UMoviePipelineDeadlineCloudExecutorJob>(QueueJob);
		MarkedJob->ReconcileJobTemplateParameters(Current, true);
		MarkedJob->LastCheckedPluginVersion = TEXT("1.2.0");
	}
	TestTrue(TEXT("Same version skips the queue"), UMoviePipelineDeadlineCloudExecutorJob::CheckForTemplateUpdates(Queue, TEXT("1.2.0")));
	auto VisibleInternal = Parameter(TEXT("ArtistUnhidden"), TEXT("default"));
	VisibleInternal.UserInterfaceControl = EUserInterfaceControl::HIDDEN;
	Current.Add(VisibleInternal);
	Preset->ParameterDefinition.Parameters.Add(VisibleInternal);
	VisibleInternal.Value = TEXT("artist-value");
	Job->JobTemplateOverrides.Parameters.Add(VisibleInternal);
	TestFalse(TEXT("Artist-unhidden parameter stays editable"), Job->ReconcileJobTemplateParameters(Current, false));
	TestEqual(TEXT("Artist-unhidden value retained"), Job->JobTemplateOverrides.Parameters.Last().Value, FString(TEXT("artist-value")));
	Preset->PathToTemplate.FilePath = TEXT("missing-template.yml");
	Preset->ParameterDefinition.Parameters.RemoveAt(0);
	TestFalse(TEXT("Same-version queue rechecks an unsaved preset"), UMoviePipelineDeadlineCloudExecutorJob::CheckForTemplateUpdates(Queue, TEXT("1.2.0")));
	TestFalse(TEXT("Unavailable template leaves migration pending"), UMoviePipelineDeadlineCloudExecutorJob::CheckForTemplateUpdates(Queue, TEXT("1.3.0")));
	TestEqual(TEXT("Failed check preserves marker"), Job->LastCheckedPluginVersion, FString(TEXT("1.2.0")));
	auto* QueuePackage = CreatePackage(*FString::Printf(TEXT("/Temp/DeadlineTemplateUpdate_%s"), *FGuid::NewGuid().ToString()));
	auto* DisabledQueue = NewObject<UMoviePipelineQueue>(QueuePackage);
	auto* DisabledJob = Cast<UMoviePipelineDeadlineCloudExecutorJob>(
		DisabledQueue->AllocateNewJob(UMoviePipelineDeadlineCloudExecutorJob::StaticClass()));
	DisabledJob->JobPreset = Preset;
	DisabledJob->SetIsEnabled(false);
	TestTrue(TEXT("Disabled missing template does not block submission"),
		UMoviePipelineDeadlineCloudExecutorJob::CheckForTemplateUpdates(DisabledQueue, TEXT("1.3.0"), true));
	auto* EmptyPreset = NewObject<UDeadlineCloudRenderJob>();
	EmptyPreset->PathToTemplate.FilePath = FPaths::CreateTempFilename(
		*FPaths::ProjectSavedDir(), TEXT("DeadlineEmptyTemplate"), TEXT(".yml"));
	FFileHelper::SaveStringToFile(TEXT("specificationVersion: jobtemplate-2023-09\nname: Empty\n")
		TEXT("steps:\n- name: Test\n  script:\n    actions:\n      onRun:\n        command: echo\n        args: [test]\n"),
		*EmptyPreset->PathToTemplate.FilePath);
	DisabledJob->JobPreset = EmptyPreset;
	DisabledJob->JobTemplateOverrides.Parameters.Reset();
	DisabledJob->SetIsEnabled(true);
	DisabledQueue->SetIsDirty(false);
	QueuePackage->SetDirtyFlag(false);
	TestTrue(TEXT("Valid template without parameters can submit"),
		UMoviePipelineDeadlineCloudExecutorJob::CheckForTemplateUpdates(DisabledQueue, TEXT("1.3.0"), true));
	TestFalse(TEXT("Version-only check does not require saving the package"), QueuePackage->IsDirty());
	TestEqual(TEXT("Version-only check records the current version"), DisabledJob->LastCheckedPluginVersion, FString(TEXT("1.3.0")));
	TestTrue(TEXT("Version marker makes the working queue dirty"), DisabledQueue->IsDirty());
	auto* MixedQueue = NewObject<UMoviePipelineQueue>();
	auto* BrokenPreset = NewObject<UDeadlineCloudRenderJob>();
	BrokenPreset->PathToTemplate.FilePath = FPaths::CreateTempFilename(*FPaths::ProjectSavedDir(), TEXT("DeadlineBrokenTemplate"), TEXT(".yml"));
	FFileHelper::SaveStringToFile(TEXT("parameterDefinitions:\n- {}\n"), *BrokenPreset->PathToTemplate.FilePath);
	for (auto* InvalidPreset : TArray<UDeadlineCloudRenderJob*>{ nullptr, Preset, BrokenPreset })
	{
		auto* InvalidJob = Cast<UMoviePipelineDeadlineCloudExecutorJob>(MixedQueue->AllocateNewJob(UMoviePipelineDeadlineCloudExecutorJob::StaticClass()));
		InvalidJob->JobPreset = InvalidPreset;
		InvalidJob->LastCheckedPluginVersion = TEXT("1.2.0");
		InvalidJob->JobTemplateOverrides.Parameters = { Parameter(TEXT("Saved"), TEXT("artist-value")) };
	}
	auto* ValidJob = Cast<UMoviePipelineDeadlineCloudExecutorJob>(MixedQueue->AllocateNewJob(UMoviePipelineDeadlineCloudExecutorJob::StaticClass()));
	ValidJob->JobPreset = EmptyPreset;
	ValidJob->JobTemplateOverrides.Parameters.Reset();
	AddExpectedError(TEXT("KeyError: 'name'"), EAutomationExpectedErrorFlags::Contains, 1);
	AddExpectedError(TEXT("PythonYamlLibraryImplementation.OpenJobFile"), EAutomationExpectedErrorFlags::Contains, 1);
	TestFalse(TEXT("Invalid jobs leave part of the check pending"), UMoviePipelineDeadlineCloudExecutorJob::CheckForTemplateUpdates(MixedQueue, TEXT("1.3.0"), true));
	TestEqual(TEXT("Invalid jobs do not prevent checking a valid job"), ValidJob->LastCheckedPluginVersion, FString(TEXT("1.3.0")));
	for (int32 Index = 0; Index < 3; ++Index)
	{
		auto* InvalidJob = Cast<UMoviePipelineDeadlineCloudExecutorJob>(MixedQueue->GetJobs()[Index]);
		TestEqual(TEXT("Skipped job keeps its version marker"), InvalidJob->LastCheckedPluginVersion, FString(TEXT("1.2.0")));
		TestEqual(TEXT("Skipped job keeps its saved value"), InvalidJob->JobTemplateOverrides.Parameters[0].Value, FString(TEXT("artist-value")));
	}
	IFileManager::Get().Delete(*BrokenPreset->PathToTemplate.FilePath);
	if (FApp::IsUnattended())
	{
		FFileHelper::SaveStringToFile(
			TEXT("parameterDefinitions:\n- name: NewParameter\n  type: STRING\n  default: new-default\n"),
			*EmptyPreset->PathToTemplate.FilePath);
		EmptyPreset->ParameterDefinition.Parameters = { Parameter(TEXT("Saved"), TEXT("preset-value")) };
		DisabledJob->JobTemplateOverrides.Parameters = { Parameter(TEXT("Saved"), TEXT("artist-value")) };
		DisabledJob->LastCheckedPluginVersion = TEXT("1.2.0");
		TestFalse(TEXT("Unattended changed-template check leaves update pending"),
			UMoviePipelineDeadlineCloudExecutorJob::CheckForTemplateUpdates(DisabledQueue, TEXT("1.3.0"), true));
		TestEqual(TEXT("Unattended check preserves job parameter count"), DisabledJob->JobTemplateOverrides.Parameters.Num(), 1);
		TestEqual(TEXT("Unattended check preserves job parameter name"), DisabledJob->JobTemplateOverrides.Parameters[0].Name, FString(TEXT("Saved")));
		TestEqual(TEXT("Unattended check preserves saved value"), DisabledJob->JobTemplateOverrides.Parameters[0].Value, FString(TEXT("artist-value")));
		TestEqual(TEXT("Unattended check preserves preset parameter count"), EmptyPreset->ParameterDefinition.Parameters.Num(), 1);
		TestEqual(TEXT("Unattended check preserves preset parameter name"), EmptyPreset->ParameterDefinition.Parameters[0].Name, FString(TEXT("Saved")));
		TestEqual(TEXT("Unattended check preserves preset value"), EmptyPreset->ParameterDefinition.Parameters[0].Value, FString(TEXT("preset-value")));
		TestEqual(TEXT("Unattended check preserves version marker"), DisabledJob->LastCheckedPluginVersion, FString(TEXT("1.2.0")));
	}
	else
	{
		AddWarning(TEXT("Run with -unattended to cover changed-template checks without a modal."));
	}
	IFileManager::Get().Delete(*EmptyPreset->PathToTemplate.FilePath);
	return true;
}
