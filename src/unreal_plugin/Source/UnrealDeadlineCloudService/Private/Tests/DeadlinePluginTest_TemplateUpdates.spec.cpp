// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "Misc/AutomationTest.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "Serialization/ObjectReader.h"
#include "Serialization/ObjectWriter.h"
#include "UObject/Package.h"
#include "Misc/FileHelper.h"
#include "Misc/App.h"
#include "Misc/EngineVersion.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

namespace
{
	using FMrqJob = UMoviePipelineDeadlineCloudExecutorJob;

	const TCHAR* KeptAndRemovedParameters = TEXT("parameterDefinitions:\n")
		TEXT("- name: Kept\n  type: STRING\n  default: template-default\n")
		TEXT("- name: Removed\n  type: STRING\n  default: old\n");

	FParameterDefinition MakeParameter(const FString& Name, const FString& Value, EValueType Type = EValueType::STRING)
	{
		FParameterDefinition Result;
		Result.Name = Name;
		Result.Value = Value;
		Result.Type = Type;
		return Result;
	}

	const FParameterDefinition* FindParameter(const TArray<FParameterDefinition>& Parameters, const FString& Name)
	{
		return Parameters.FindByPredicate([&](const FParameterDefinition& P) { return P.Name == Name; });
	}

	FMrqJob* AddJob(UMoviePipelineQueue* Queue, UDeadlineCloudRenderJob* Preset)
	{
		auto* Job = Cast<FMrqJob>(Queue->AllocateNewJob(FMrqJob::StaticClass()));
		Job->JobPreset = Preset;
		Job->JobTemplateOverrides.Parameters.Reset();
		return Job;
	}

	UMoviePipelineQueue* NewPackagedQueue()
	{
		auto* Package = CreatePackage(*FString::Printf(TEXT("/Temp/DeadlineTemplateUpdate_%s"), *FGuid::NewGuid().ToString()));
		return NewObject<UMoviePipelineQueue>(Package);
	}

	FString JobTemplate(const FString& ParameterDefinitions = FString())
	{
		return TEXT("specificationVersion: jobtemplate-2023-09\nname: TemplateUpdates\n") + ParameterDefinitions
			+ TEXT("steps:\n- name: Test\n  script:\n    actions:\n      onRun:\n        command: echo\n        args: [test]\n");
	}
}

BEGIN_DEFINE_SPEC(FDeadlineCloudTemplateUpdatesSpec, "DeadlineCloud.Offline.MRQ.TemplateUpdates",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

	UMoviePipelineQueue* Queue = nullptr;
	UDeadlineCloudRenderJob* Preset = nullptr;
	TArray<FParameterDefinition> Current;
	TArray<FString> TemplateFiles;

	FString TempTemplatePath()
	{
		return TemplateFiles.Add_GetRef(FPaths::CreateTempFilename(
			*FPaths::ProjectSavedDir(), TEXT("DeadlineTemplateUpdates"), TEXT(".yml")));
	}

	FString WriteTemplate(const FString& Contents)
	{
		const FString Path = TempTemplatePath();
		FFileHelper::SaveStringToFile(Contents, *Path);
		return Path;
	}

	TArray<FParameterDefinition> ReadTemplate(const FString& Path)
	{
		auto* Library = UPythonYamlLibrary::Get();
		if (!TestNotNull(TEXT("Python YAML library"), Library))
		{
			return {};
		}
		FJobTemplateReadResult Result = Library->ReadJobFile(Path);
		TestTrue(TEXT("Template is readable"), Result.bSucceeded);
		return MoveTemp(Result.Parameters);
	}

	// Saved job that matches its template after a completed 1.2.0 check.
	FMrqJob* AddCheckedJob(UMoviePipelineQueue* InQueue, UDeadlineCloudRenderJob* InPreset)
	{
		auto* Job = AddJob(InQueue, InPreset);
		Job->ReconcileJobTemplateParameters(ReadTemplate(InPreset->PathToTemplate.FilePath), true);
		Job->LastCheckedPluginVersion = TEXT("1.2.0");
		return Job;
	}

	FMrqJob* AddSavedJob(int32 Index)
	{
		auto* Job = AddJob(Queue, Preset);
		Job->JobTemplateOverrides.Parameters = {
			MakeParameter(TEXT("CondaChannels"), FString::Printf(TEXT("artist-%d"), Index)),
			MakeParameter(TEXT("Removed"), TEXT("old")),
			MakeParameter(TEXT("ChangedType"), TEXT("saved-string"))
		};
		return Job;
	}

	void TestParameterValue(const TCHAR* What, const TArray<FParameterDefinition>& Parameters, const FString& Name, const FString& Expected)
	{
		if (const auto* Parameter = FindParameter(Parameters, Name); TestNotNull(What, Parameter))
		{
			TestEqual(What, Parameter->Value, Expected);
		}
	}

	void TestSingleParameter(const TCHAR* What, const TArray<FParameterDefinition>& Parameters, const FString& Name, const FString& Expected)
	{
		if (TestEqual(What, Parameters.Num(), 1))
		{
			TestEqual(What, Parameters[0].Name, Name);
			TestEqual(What, Parameters[0].Value, Expected);
		}
	}

END_DEFINE_SPEC(FDeadlineCloudTemplateUpdatesSpec)

void FDeadlineCloudTemplateUpdatesSpec::Define()
{
	BeforeEach([this]()
	{
		TemplateFiles.Reset();
		Queue = NewObject<UMoviePipelineQueue>();
		Preset = NewObject<UDeadlineCloudRenderJob>();
		Preset->ParameterDefinition.Parameters = {
			MakeParameter(TEXT("CondaChannels"), TEXT("studio-channel")),
			MakeParameter(TEXT("Removed"), TEXT("old")),
			MakeParameter(TEXT("ChangedType"), TEXT("invalid-integer")),
			MakeParameter(TEXT("HiddenByArtist"), TEXT("private"))
		};
		Preset->GetHiddenManager().Add(TEXT("HiddenByArtist"));
		Current = {
			MakeParameter(TEXT("CondaChannels"), TEXT("new-default")),
			MakeParameter(TEXT("IgnorePlugins"), TEXT("false")),
			MakeParameter(TEXT("ChangedType"), TEXT("1"), EValueType::INT),
			MakeParameter(TEXT("HiddenByArtist"), TEXT("default")),
			MakeParameter(TEXT("Internal"), TEXT("internal-default"))
		};
		Current[1].UserInterfaceControl = EUserInterfaceControl::DROPDOWN_LIST;
		Current.Last().UserInterfaceControl = EUserInterfaceControl::HIDDEN;
	});

	AfterEach([this]()
	{
		for (const FString& Path : TemplateFiles)
		{
			IFileManager::Get().Delete(*Path, false, true, true);
		}
		TemplateFiles.Reset();
		Current.Reset();
		if (Preset)
		{
			Preset->GetHiddenManager().OnChanged.Unbind();
		}
		Queue = nullptr;
		Preset = nullptr;
	});

	Describe("Reconcile", [this]()
	{
		It("updates 100 jobs sharing a preset and refreshes the preset once", [this]()
		{
			auto Notifications = MakeShared<int32>(0);
			Preset->GetHiddenManager().OnChanged.BindLambda([Notifications]() { ++*Notifications; });
			for (int32 Index = 0; Index < 100; ++Index)
			{
				auto* Job = AddSavedJob(Index);
				Job->PresetOverrides.JobSharedSettings.Priority = 73;
				TestTrue(TEXT("Detect stale definitions"), Job->ReconcileJobTemplateParameters(Current, false));
				TestNotNull(TEXT("Preview preserves old overrides"), FindParameter(Job->JobTemplateOverrides.Parameters, TEXT("Removed")));
				TestTrue(TEXT("Apply update"), Job->ReconcileJobTemplateParameters(Current, true));
				const auto& Parameters = Job->JobTemplateOverrides.Parameters;
				TestEqual(TEXT("Obsolete and hidden parameters excluded"), Parameters.Num(), 3);
				TestNull(TEXT("Removed parameter discarded"), FindParameter(Parameters, TEXT("Removed")));
				TestNull(TEXT("Artist-hidden parameter excluded"), FindParameter(Parameters, TEXT("HiddenByArtist")));
				TestNull(TEXT("Template-hidden parameter excluded"), FindParameter(Parameters, TEXT("Internal")));
				TestParameterValue(TEXT("Keep each job's value"), Parameters, TEXT("CondaChannels"), FString::Printf(TEXT("artist-%d"), Index));
				TestParameterValue(TEXT("New parameter default"), Parameters, TEXT("IgnorePlugins"), TEXT("false"));
				if (const auto* Added = FindParameter(Parameters, TEXT("IgnorePlugins")))
				{
					TestEqual(TEXT("New parameter UI"), Added->UserInterfaceControl, EUserInterfaceControl::DROPDOWN_LIST);
				}
				TestParameterValue(TEXT("Changed type uses new default"), Parameters, TEXT("ChangedType"), TEXT("1"));
				TestEqual(TEXT("Shared settings preserved"), Job->PresetOverrides.JobSharedSettings.Priority, 73);
				TestFalse(TEXT("Update is idempotent"), Job->ReconcileJobTemplateParameters(Current, false));
			}
			TestParameterValue(TEXT("Shared preset keeps its value"), Preset->ParameterDefinition.Parameters, TEXT("CondaChannels"), TEXT("studio-channel"));
			TestEqual(TEXT("Shared preset definitions updated"), Preset->ParameterDefinition.Parameters.Num(), 5);
			TestEqual(TEXT("Shared preset is refreshed once"), *Notifications, 1);
		});

		It("keeps saved values for unchanged and default-only definitions", [this]()
		{
			auto* Job = AddSavedJob(0);
			Job->ReconcileJobTemplateParameters(Current, true);
			TestFalse(TEXT("Unchanged definitions need no update"), Job->ReconcileJobTemplateParameters(Current, false));
			Current[0].Value = TEXT("another-default");
			TestFalse(TEXT("Default-only changes do not trigger migration"), Job->ReconcileJobTemplateParameters(Current, false));
			TestFalse(TEXT("Default-only apply is a no-op"), Job->ReconcileJobTemplateParameters(Current, true));
			TestParameterValue(TEXT("Job value kept"), Job->JobTemplateOverrides.Parameters, TEXT("CondaChannels"), TEXT("artist-0"));
			TestParameterValue(TEXT("Preset value kept"), Preset->ParameterDefinition.Parameters, TEXT("CondaChannels"), TEXT("studio-channel"));
		});

		It("updates UI metadata and keeps matching values", [this]()
		{
			auto* Job = AddSavedJob(0);
			Job->ReconcileJobTemplateParameters(Current, true);
			Current[0].UserInterfaceControl = EUserInterfaceControl::MULTILINE_EDIT;
			TestTrue(TEXT("UI control changes trigger migration"), Job->ReconcileJobTemplateParameters(Current, false));
			TestTrue(TEXT("Apply UI control change"), Job->ReconcileJobTemplateParameters(Current, true));
			if (const auto* Updated = FindParameter(Job->JobTemplateOverrides.Parameters, TEXT("CondaChannels"));
				TestNotNull(TEXT("Updated parameter kept"), Updated))
			{
				TestEqual(TEXT("New UI control applied"), Updated->UserInterfaceControl, EUserInterfaceControl::MULTILINE_EDIT);
				TestEqual(TEXT("Matching value kept"), Updated->Value, FString(TEXT("artist-0")));
			}
		});

		It("makes previously internal parameters editable and keeps artist visibility", [this]()
		{
			auto* Job = AddSavedJob(0);
			Job->ReconcileJobTemplateParameters(Current, true);
			TestTrue(TEXT("Template-hidden parameter starts hidden"), Preset->GetHiddenManager().Contains(TEXT("Internal")));
			Current.Last().UserInterfaceControl = EUserInterfaceControl::LINE_EDIT;
			TestTrue(TEXT("Visibility change applied"), Job->ReconcileJobTemplateParameters(Current, true));
			TestEqual(TEXT("Previously internal parameter becomes editable"), Job->JobTemplateOverrides.Parameters.Num(), 4);
			TestNotNull(TEXT("Internal parameter is overridable"), FindParameter(Job->JobTemplateOverrides.Parameters, TEXT("Internal")));
			TestFalse(TEXT("Old template visibility cleared"), Preset->GetHiddenManager().Contains(TEXT("Internal")));
			TestTrue(TEXT("Artist visibility retained"), Preset->GetHiddenManager().Contains(TEXT("HiddenByArtist")));
		});

		It("keeps artist-unhidden template parameters editable", [this]()
		{
			auto* Job = AddSavedJob(0);
			Job->ReconcileJobTemplateParameters(Current, true);
			auto Unhidden = MakeParameter(TEXT("ArtistUnhidden"), TEXT("default"));
			Unhidden.UserInterfaceControl = EUserInterfaceControl::HIDDEN;
			Current.Add(Unhidden);
			Preset->ParameterDefinition.Parameters.Add(Unhidden);
			Unhidden.Value = TEXT("artist-value");
			Job->JobTemplateOverrides.Parameters.Add(Unhidden);
			TestFalse(TEXT("Artist-unhidden parameter stays editable"), Job->ReconcileJobTemplateParameters(Current, false));
			Current[0].UserInterfaceControl = EUserInterfaceControl::MULTILINE_EDIT;
			TestTrue(TEXT("Unrelated change applied"), Job->ReconcileJobTemplateParameters(Current, true));
			TestFalse(TEXT("Artist-unhidden parameter not re-hidden"), Preset->GetHiddenManager().Contains(TEXT("ArtistUnhidden")));
			TestParameterValue(TEXT("Artist-unhidden value retained"), Job->JobTemplateOverrides.Parameters, TEXT("ArtistUnhidden"), TEXT("artist-value"));
		});

		struct FCondaCase
		{
			const TCHAR* Description;
			bool bSavedInPreset;
			EValueType SavedType;
			bool bKeepsSavedValues;
		};
		for (const FCondaCase& Case : {
			FCondaCase{ TEXT("normalizes Conda defaults for added parameters"), false, EValueType::STRING, false },
			FCondaCase{ TEXT("normalizes Conda defaults for retyped parameters"), true, EValueType::INT, false },
			FCondaCase{ TEXT("keeps saved Conda values for matching parameters"), true, EValueType::STRING, true } })
		{
			It(Case.Description, [this, Case]()
			{
				auto* CondaPreset = NewObject<UDeadlineCloudRenderJob>();
				auto* CondaJob = AddJob(Queue, CondaPreset);
				const TArray<FParameterDefinition> CondaDefaults = {
					MakeParameter(TEXT("CondaPackages"), TEXT("unrealengine=0.0")),
					MakeParameter(TEXT("CondaChannels"), TEXT("template-channel"))
				};
				if (Case.bSavedInPreset)
				{
					CondaPreset->ParameterDefinition.Parameters = {
						MakeParameter(TEXT("CondaPackages"), TEXT("unrealengine=9.9"), Case.SavedType),
						MakeParameter(TEXT("CondaChannels"), TEXT("artist-channel"), Case.SavedType)
					};
				}
				CondaJob->JobTemplateOverrides.Parameters = CondaPreset->ParameterDefinition.Parameters;
				CondaJob->JobTemplateOverrides.Parameters.Add(MakeParameter(TEXT("Removed"), TEXT("old")));
				const int32 SavedCount = CondaJob->JobTemplateOverrides.Parameters.Num();
				TestTrue(TEXT("Preview detects Conda definition changes"), CondaJob->ReconcileJobTemplateParameters(CondaDefaults, false));
				TestEqual(TEXT("Preview preserves saved parameters"), CondaJob->JobTemplateOverrides.Parameters.Num(), SavedCount);
				TestTrue(TEXT("Apply Conda definition update"), CondaJob->ReconcileJobTemplateParameters(CondaDefaults, true));

				const auto& Parameters = CondaJob->JobTemplateOverrides.Parameters;
				TestEqual(TEXT("Removed parameter discarded"), Parameters.Num(), 2);
				const FString EnginePackage = FString::Printf(TEXT("unrealengine=%d.%d"),
					FEngineVersion::Current().GetMajor(), FEngineVersion::Current().GetMinor());
				if (const auto* Packages = FindParameter(Parameters, TEXT("CondaPackages")); TestNotNull(TEXT("CondaPackages kept"), Packages))
				{
					TestTrue(TEXT("New/retyped engine defaults normalize; matching values stay saved"),
						Packages->Value.Contains(Case.bKeepsSavedValues ? FString(TEXT("unrealengine=9.9")) : EnginePackage));
				}
				const FString ChannelOverride = FPlatformMisc::GetEnvironmentVariable(TEXT("DEADLINE_CONDA_CHANNELS"));
				TestParameterValue(TEXT("New/retyped channels inherit the override; matching values stay saved"), Parameters, TEXT("CondaChannels"),
					Case.bKeepsSavedValues ? FString(TEXT("artist-channel"))
					: ChannelOverride.IsEmpty() ? FString(TEXT("template-channel")) : ChannelOverride);
				TestFalse(TEXT("Conda update is idempotent"), CondaJob->ReconcileJobTemplateParameters(CondaDefaults, false));
			});
		}
	});

	Describe("VersionMarker", [this]()
	{
		It("is re-armed when a preset is reloaded", [this]()
		{
			auto* Job = AddJob(Queue, Preset);
			Job->LastCheckedPluginVersion = TEXT("1.2.0");
			Job->bTemplateUpdatePrompted = true;
			Job->ReloadDataFromJobPreset();
			TestTrue(TEXT("Reloading a preset re-arms the version check"), Job->LastCheckedPluginVersion.IsEmpty());
			TestFalse(TEXT("Reloading a preset re-arms the prompt"), Job->bTemplateUpdatePrompted);
		});

		It("survives serialization", [this]()
		{
			auto* Job = AddJob(Queue, Preset);
			Job->LastCheckedPluginVersion = TEXT("1.2.0");
			TArray<uint8> Saved;
			FObjectWriter Writer(Job, Saved);
			auto* Restored = NewObject<FMrqJob>(Queue);
			FObjectReader Reader(Restored, Saved);
			TestEqual(TEXT("Version marker survives serialization"), Restored->LastCheckedPluginVersion, FString(TEXT("1.2.0")));
		});
	});

	Describe("ReadJobFile", [this]()
	{
		It("reports template read results explicitly", [this]()
		{
			auto* Library = UPythonYamlLibrary::Get();
			if (!TestNotNull(TEXT("Python YAML library"), Library))
			{
				return;
			}
			const auto Broken = Library->ReadJobFile(WriteTemplate(TEXT("parameterDefinitions:\n- {}\n")));
			TestFalse(TEXT("Invalid template read fails"), Broken.bSucceeded);
			TestEqual(TEXT("Failed read has no parameters"), Broken.Parameters.Num(), 0);
			const auto Empty = Library->ReadJobFile(WriteTemplate(JobTemplate()));
			TestTrue(TEXT("Template without parameters reads successfully"), Empty.bSucceeded);
			TestEqual(TEXT("Template without parameters has none"), Empty.Parameters.Num(), 0);
		});
	});

	Describe("CheckForTemplateUpdates", [this]()
	{
		It("skips unchanged same-version jobs without dirtying the queue", [this]()
		{
			auto* PackagedQueue = NewPackagedQueue();
			auto* TemplatePreset = NewObject<UDeadlineCloudRenderJob>();
			TemplatePreset->PathToTemplate.FilePath = WriteTemplate(JobTemplate(KeptAndRemovedParameters));
			auto* First = AddCheckedJob(PackagedQueue, TemplatePreset);
			auto* Second = AddCheckedJob(PackagedQueue, TemplatePreset);
			PackagedQueue->SetIsDirty(false);
			PackagedQueue->GetPackage()->SetDirtyFlag(false);
			TestTrue(TEXT("Same version skips the unchanged queue"), FMrqJob::CheckForTemplateUpdates(PackagedQueue, TEXT("1.2.0")));
			TestFalse(TEXT("Skipped check does not require saving the package"), PackagedQueue->GetPackage()->IsDirty());
			TestFalse(TEXT("Skipped check leaves the working queue clean"), PackagedQueue->IsDirty());
			for (auto* Job : { First, Second })
			{
				TestEqual(TEXT("Skipped job keeps its marker"), Job->LastCheckedPluginVersion, FString(TEXT("1.2.0")));
			}
		});

		It("detects same-version template definition edits", [this]()
		{
			auto* EditedPreset = NewObject<UDeadlineCloudRenderJob>();
			const FString Path = WriteTemplate(JobTemplate(KeptAndRemovedParameters));
			EditedPreset->PathToTemplate.FilePath = Path;
			auto* Job = AddCheckedJob(Queue, EditedPreset);
			for (auto& Parameter : Job->JobTemplateOverrides.Parameters)
			{
				if (Parameter.Name == TEXT("Kept"))
				{
					Parameter.Value = TEXT("artist-value");
				}
			}
			TestTrue(TEXT("Unchanged same-version queue passes"), FMrqJob::CheckForTemplateUpdates(Queue, TEXT("1.2.0")));

			// Studio edits the YAML without a plugin upgrade.
			FFileHelper::SaveStringToFile(JobTemplate(TEXT("parameterDefinitions:\n")
				TEXT("- name: Kept\n  type: STRING\n  default: new-default\n")
				TEXT("- name: Added\n  type: INT\n  default: 7\n")), *Path);
			const auto Edited = ReadTemplate(Path);
			TestTrue(TEXT("Preview detects the edited definitions"), Job->ReconcileJobTemplateParameters(Edited, false));
			if (FApp::IsUnattended())
			{
				TestFalse(TEXT("Same-version edit is not skipped"), FMrqJob::CheckForTemplateUpdates(Queue, TEXT("1.2.0")));
				TestFalse(TEXT("Same-version edit blocks unattended submission"), FMrqJob::CheckForTemplateUpdates(Queue, TEXT("1.2.0"), true));
				const auto& Saved = Job->JobTemplateOverrides.Parameters;
				TestEqual(TEXT("Pending update preserves job parameter count"), Saved.Num(), 2);
				TestParameterValue(TEXT("Pending update preserves saved value"), Saved, TEXT("Kept"), TEXT("artist-value"));
				TestNotNull(TEXT("Pending update preserves removed job parameter"), FindParameter(Saved, TEXT("Removed")));
				TestNotNull(TEXT("Pending update preserves removed preset parameter"), FindParameter(EditedPreset->ParameterDefinition.Parameters, TEXT("Removed")));
				TestNull(TEXT("Pending update adds no preset parameter"), FindParameter(EditedPreset->ParameterDefinition.Parameters, TEXT("Added")));
				TestEqual(TEXT("Pending update preserves marker"), Job->LastCheckedPluginVersion, FString(TEXT("1.2.0")));
			}
			else
			{
				AddWarning(TEXT("Run with -unattended to cover same-version checks without a modal."));
			}

			// Direct apply is what the Yes answer performs.
			TestTrue(TEXT("Direct apply refreshes the job"), Job->ReconcileJobTemplateParameters(Edited, true));
			const auto& Refreshed = Job->JobTemplateOverrides.Parameters;
			TestEqual(TEXT("Refreshed job matches the edited template"), Refreshed.Num(), 2);
			TestParameterValue(TEXT("Refreshed job keeps matching value"), Refreshed, TEXT("Kept"), TEXT("artist-value"));
			TestParameterValue(TEXT("Refreshed job gets the added default"), Refreshed, TEXT("Added"), TEXT("7"));
			TestNull(TEXT("Refreshed job drops the removed parameter"), FindParameter(Refreshed, TEXT("Removed")));
			const auto& PresetParameters = EditedPreset->ParameterDefinition.Parameters;
			TestParameterValue(TEXT("Refreshed preset keeps matching value"), PresetParameters, TEXT("Kept"), TEXT("template-default"));
			TestNotNull(TEXT("Refreshed preset gets the added parameter"), FindParameter(PresetParameters, TEXT("Added")));
			TestNull(TEXT("Refreshed preset drops the removed parameter"), FindParameter(PresetParameters, TEXT("Removed")));
			TestTrue(TEXT("Refreshed same-version queue passes"), FMrqJob::CheckForTemplateUpdates(Queue, TEXT("1.2.0")));
		});

		It("leaves migration pending when the template is unavailable", [this]()
		{
			auto* Job = AddSavedJob(0);
			Preset->PathToTemplate.FilePath = TempTemplatePath();
			Job->LastCheckedPluginVersion = TEXT("1.2.0");
			TestFalse(TEXT("Same-version check reads the unavailable template"), FMrqJob::CheckForTemplateUpdates(Queue, TEXT("1.2.0")));
			TestFalse(TEXT("Unavailable template leaves migration pending"), FMrqJob::CheckForTemplateUpdates(Queue, TEXT("1.3.0")));
			TestEqual(TEXT("Failed check preserves marker"), Job->LastCheckedPluginVersion, FString(TEXT("1.2.0")));
			TestParameterValue(TEXT("Failed check preserves saved value"), Job->JobTemplateOverrides.Parameters, TEXT("CondaChannels"), TEXT("artist-0"));
		});

		It("ignores disabled jobs during submission", [this]()
		{
			auto* DisabledQueue = NewPackagedQueue();
			Preset->PathToTemplate.FilePath = TempTemplatePath();
			auto* DisabledJob = AddJob(DisabledQueue, Preset);
			DisabledJob->SetIsEnabled(false);
			TestTrue(TEXT("Disabled missing template does not block submission"),
				FMrqJob::CheckForTemplateUpdates(DisabledQueue, TEXT("1.3.0"), true));
		});

		It("records a version-only check without dirtying the package", [this]()
		{
			auto* PackagedQueue = NewPackagedQueue();
			auto* EmptyPreset = NewObject<UDeadlineCloudRenderJob>();
			EmptyPreset->PathToTemplate.FilePath = WriteTemplate(JobTemplate());
			auto* Job = AddJob(PackagedQueue, EmptyPreset);
			PackagedQueue->SetIsDirty(false);
			PackagedQueue->GetPackage()->SetDirtyFlag(false);
			TestTrue(TEXT("Valid template without parameters can submit"),
				FMrqJob::CheckForTemplateUpdates(PackagedQueue, TEXT("1.3.0"), true));
			TestFalse(TEXT("Version-only check does not require saving the package"), PackagedQueue->GetPackage()->IsDirty());
			TestEqual(TEXT("Version-only check records the current version"), Job->LastCheckedPluginVersion, FString(TEXT("1.3.0")));
			TestTrue(TEXT("Version marker makes the working queue dirty"), PackagedQueue->IsDirty());
		});

		It("checks valid jobs when other jobs are invalid", [this]()
		{
			auto* MissingPreset = NewObject<UDeadlineCloudRenderJob>();
			MissingPreset->PathToTemplate.FilePath = TempTemplatePath();
			auto* BrokenPreset = NewObject<UDeadlineCloudRenderJob>();
			BrokenPreset->PathToTemplate.FilePath = WriteTemplate(TEXT("parameterDefinitions:\n- {}\n"));
			auto* EmptyPreset = NewObject<UDeadlineCloudRenderJob>();
			EmptyPreset->PathToTemplate.FilePath = WriteTemplate(JobTemplate());
			TArray<FMrqJob*> InvalidJobs;
			for (auto* InvalidPreset : TArray<UDeadlineCloudRenderJob*>{ nullptr, MissingPreset, BrokenPreset })
			{
				auto* InvalidJob = AddJob(Queue, InvalidPreset);
				InvalidJob->LastCheckedPluginVersion = TEXT("1.2.0");
				InvalidJob->JobTemplateOverrides.Parameters = { MakeParameter(TEXT("Saved"), TEXT("artist-value")) };
				InvalidJobs.Add(InvalidJob);
			}
			auto* ValidJob = AddJob(Queue, EmptyPreset);
			TestFalse(TEXT("Invalid jobs leave part of the check pending"), FMrqJob::CheckForTemplateUpdates(Queue, TEXT("1.3.0"), true));
			TestEqual(TEXT("Invalid jobs do not prevent checking a valid job"), ValidJob->LastCheckedPluginVersion, FString(TEXT("1.3.0")));
			for (auto* InvalidJob : InvalidJobs)
			{
				TestEqual(TEXT("Skipped job keeps its version marker"), InvalidJob->LastCheckedPluginVersion, FString(TEXT("1.2.0")));
				TestSingleParameter(TEXT("Skipped job keeps its saved value"), InvalidJob->JobTemplateOverrides.Parameters, TEXT("Saved"), TEXT("artist-value"));
			}
		});

		It("leaves changed templates pending when unattended", [this]()
		{
			if (!FApp::IsUnattended())
			{
				AddWarning(TEXT("Run with -unattended to cover changed-template checks without a modal."));
				return;
			}
			auto* ChangedPreset = NewObject<UDeadlineCloudRenderJob>();
			ChangedPreset->PathToTemplate.FilePath = WriteTemplate(JobTemplate(
				TEXT("parameterDefinitions:\n- name: NewParameter\n  type: STRING\n  default: new-default\n")));
			ChangedPreset->ParameterDefinition.Parameters = { MakeParameter(TEXT("Saved"), TEXT("preset-value")) };
			auto* Job = AddJob(Queue, ChangedPreset);
			Job->JobTemplateOverrides.Parameters = { MakeParameter(TEXT("Saved"), TEXT("artist-value")) };
			Job->LastCheckedPluginVersion = TEXT("1.2.0");
			TestFalse(TEXT("Unattended changed-template check leaves update pending"),
				FMrqJob::CheckForTemplateUpdates(Queue, TEXT("1.3.0"), true));
			TestSingleParameter(TEXT("Unattended check preserves job parameters"), Job->JobTemplateOverrides.Parameters, TEXT("Saved"), TEXT("artist-value"));
			TestSingleParameter(TEXT("Unattended check preserves preset parameters"), ChangedPreset->ParameterDefinition.Parameters, TEXT("Saved"), TEXT("preset-value"));
			TestEqual(TEXT("Unattended check preserves version marker"), Job->LastCheckedPluginVersion, FString(TEXT("1.2.0")));
		});
	});
}
