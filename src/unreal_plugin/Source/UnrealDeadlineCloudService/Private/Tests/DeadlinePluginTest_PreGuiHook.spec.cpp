// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "Misc/AutomationTest.h"
#include "CoreMinimal.h"
#include "UObject/UObjectGlobals.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/DeadlineCloudPreGuiHookLibrary.h"


BEGIN_DEFINE_SPEC(FDeadlinePluginPreGuiHookSpec, "DeadlineCloud.Offline",
    EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext);

UDeadlineCloudJob* CreatedJobDataAsset;

END_DEFINE_SPEC(FDeadlinePluginPreGuiHookSpec);

void FDeadlinePluginPreGuiHookSpec::Define()
{
    // These specs exercise UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob directly — the pure
    // C++ mapping that the Details-panel customization runs after the Python BIE returns a merged
    // hook output. The Python RunPreGuiHooks BIE (which needs a live interpreter + hook scripts)
    // is out of scope here; deadline-cloud owns hook execution and the Python impl is unit-tested
    // separately. The design's D1 apply-once guard (bPreGuiHooksApplied) is a plain bool on the
    // job, so it is validated here too.
    Describe("FPreGuiHookApplyOutput", [this]()
        {
            BeforeEach([this]()
                {
                    CreatedJobDataAsset = NewObject<UDeadlineCloudJob>();
                });
            AfterEach([this]()
                {
                    CreatedJobDataAsset = nullptr;
                });

            It("does nothing when the hook did not run (bRan=false)", [this]()
                {
                    FDeadlineCloudJobSharedSettingsStruct& Shared =
                        CreatedJobDataAsset->JobPresetStruct.JobSharedSettings;
                    const FString OriginalName = Shared.Name;
                    const int32 OriginalPriority = Shared.Priority;

                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = false;
                    // Even with fields flagged as present, bRan=false must be a no-op.
                    Output.bHasName = true;
                    Output.Name = TEXT("ShouldNotApply");
                    Output.bHasPriority = true;
                    Output.Priority = 99;

                    UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);

                    TestEqual("Name unchanged when hook did not run", Shared.Name, OriginalName);
                    TestEqual("Priority unchanged when hook did not run", Shared.Priority, OriginalPriority);
                });

            It("applies only the shared-setting fields the hook actually set", [this]()
                {
                    FDeadlineCloudJobSharedSettingsStruct& Shared =
                        CreatedJobDataAsset->JobPresetStruct.JobSharedSettings;
                    const FString OriginalDescription = Shared.Description;
                    const int32 OriginalMaxRetries = Shared.MaximumRetriesPerTask;

                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = true;
                    Output.bHasName = true;
                    Output.Name = TEXT("HookedName");
                    Output.bHasPriority = true;
                    Output.Priority = 88;
                    Output.bHasInitialState = true;
                    Output.InitialState = TEXT("SUSPENDED");
                    Output.bHasMaxFailedTasksCount = true;
                    Output.MaximumFailedTasksCount = 7;
                    // Description + MaximumRetriesPerTask intentionally left unset (bHas* = false).

                    UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);

                    TestEqual("Name applied", Shared.Name, FString(TEXT("HookedName")));
                    TestEqual("Priority applied", Shared.Priority, 88);
                    TestEqual("InitialState applied", Shared.InitialState, FString(TEXT("SUSPENDED")));
                    TestEqual("MaximumFailedTasksCount applied", Shared.MaximumFailedTasksCount, 7);
                    // Fields the hook did not set must be preserved.
                    TestEqual("Description preserved", Shared.Description, OriginalDescription);
                    TestEqual("MaximumRetriesPerTask preserved", Shared.MaximumRetriesPerTask, OriginalMaxRetries);
                });

            It("applies hook template parameters onto matching definitions by name", [this]()
                {
                    // Seed two parameters on the job.
                    TArray<FParameterDefinition> Params;
                    FParameterDefinition ParamA;
                    ParamA.Name = TEXT("OutputPath");
                    ParamA.Type = EValueType::STRING;
                    ParamA.Value = TEXT("/original/path");
                    Params.Add(ParamA);
                    FParameterDefinition ParamB;
                    ParamB.Name = TEXT("FrameRange");
                    ParamB.Type = EValueType::STRING;
                    ParamB.Value = TEXT("1-10");
                    Params.Add(ParamB);
                    CreatedJobDataAsset->SetJobParameters(Params);

                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = true;
                    // One matching (OutputPath) and one non-matching (Nonexistent) hook param.
                    FParameterDefinition HookMatch;
                    HookMatch.Name = TEXT("OutputPath");
                    HookMatch.Type = EValueType::STRING;
                    HookMatch.Value = TEXT("/hooked/path");
                    Output.Parameters.Add(HookMatch);
                    FParameterDefinition HookMiss;
                    HookMiss.Name = TEXT("Nonexistent");
                    HookMiss.Type = EValueType::STRING;
                    HookMiss.Value = TEXT("ignored");
                    Output.Parameters.Add(HookMiss);

                    UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);

                    const TArray<FParameterDefinition> Result = CreatedJobDataAsset->GetJobParameters();
                    TestEqual("Parameter count unchanged (no params added)", Result.Num(), 2);

                    FString OutputPathValue;
                    FString FrameRangeValue;
                    for (const FParameterDefinition& P : Result)
                    {
                        if (P.Name == TEXT("OutputPath")) { OutputPathValue = P.Value; }
                        else if (P.Name == TEXT("FrameRange")) { FrameRangeValue = P.Value; }
                    }
                    TestEqual("Matching parameter overwritten", OutputPathValue, FString(TEXT("/hooked/path")));
                    TestEqual("Non-matching parameter untouched", FrameRangeValue, FString(TEXT("1-10")));
                });

            It("is safe to call with a null job", [this]()
                {
                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = true;
                    Output.bHasName = true;
                    Output.Name = TEXT("Whatever");

                    // Must not crash / dereference null.
                    UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(nullptr, Output);
                    TestTrue("Null job handled without crashing", true);
                });

            It("guards apply-once via bPreGuiHooksApplied (D1)", [this]()
                {
                    // The Details customization only runs hooks when bPreGuiHooksApplied is false,
                    // then latches it true so artist edits on later panel rebuilds are preserved.
                    TestFalse("Guard starts false on a fresh job", CreatedJobDataAsset->bPreGuiHooksApplied);

                    // Simulate the first CustomizeDetails pass.
                    if (!CreatedJobDataAsset->bPreGuiHooksApplied)
                    {
                        CreatedJobDataAsset->bPreGuiHooksApplied = true;
                        FDeadlineCloudPreGuiHookOutput Output;
                        Output.bRan = true;
                        Output.bHasName = true;
                        Output.Name = TEXT("FirstPass");
                        UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);
                    }
                    TestEqual("First pass applied the hook name",
                        CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Name, FString(TEXT("FirstPass")));

                    // Simulate an artist edit followed by another CustomizeDetails pass — the guard
                    // must prevent a second hook application from clobbering the edit.
                    CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Name = TEXT("ArtistEdit");
                    if (!CreatedJobDataAsset->bPreGuiHooksApplied)
                    {
                        FDeadlineCloudPreGuiHookOutput Output;
                        Output.bRan = true;
                        Output.bHasName = true;
                        Output.Name = TEXT("SecondPass");
                        UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);
                    }
                    TestEqual("Artist edit preserved on rebuild (hook did not re-apply)",
                        CreatedJobDataAsset->JobPresetStruct.JobSharedSettings.Name, FString(TEXT("ArtistEdit")));
                });

            It("clamps priority to [0,100] and counts to >= 0 (matches panel ClampMin/Max)", [this]()
                {
                    FDeadlineCloudJobSharedSettingsStruct& Shared =
                        CreatedJobDataAsset->JobPresetStruct.JobSharedSettings;
                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = true;
                    Output.bHasPriority = true;
                    Output.Priority = 250; // over ClampMax
                    Output.bHasMaxFailedTasksCount = true;
                    Output.MaximumFailedTasksCount = -5; // under ClampMin

                    UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);

                    TestEqual("Priority clamped to 100", Shared.Priority, 100);
                    TestEqual("MaximumFailedTasksCount clamped to 0", Shared.MaximumFailedTasksCount, 0);
                });

            It("skips an invalid InitialState and reports it as unapplied", [this]()
                {
                    FDeadlineCloudJobSharedSettingsStruct& Shared =
                        CreatedJobDataAsset->JobPresetStruct.JobSharedSettings;
                    const FString OriginalState = Shared.InitialState;

                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = true;
                    Output.bHasInitialState = true;
                    Output.InitialState = TEXT("PAUSED"); // not READY/SUSPENDED

                    const TArray<FString> Unapplied =
                        UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);

                    TestEqual("InitialState unchanged when invalid", Shared.InitialState, OriginalState);
                    TestTrue("Invalid InitialState reported as unapplied",
                        Unapplied.Contains(TEXT("deadline:targetTaskRunStatus")));
                });

            It("skips a Name that fails the JobName rule (identifier) and reports it as unapplied", [this]()
                {
                    FDeadlineCloudJobSharedSettingsStruct& Shared =
                        CreatedJobDataAsset->JobPresetStruct.JobSharedSettings;
                    const FString OriginalName = Shared.Name;

                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = true;
                    Output.bHasName = true;
                    // Spaces are not valid in a JobName (ValidationType=JobName -> IsValidIdentifier); the
                    // panel would refuse this, so the hook value must be skipped + surfaced, not written.
                    Output.Name = TEXT("My Shot 01");

                    const TArray<FString> Unapplied =
                        UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);

                    TestEqual("Name unchanged when it fails the JobName rule", Shared.Name, OriginalName);
                    TestTrue("Invalid Name reported as unapplied", Unapplied.Contains(TEXT("name")));
                });

            It("skips a parameter value that does not parse as its declared type", [this]()
                {
                    TArray<FParameterDefinition> Params;
                    FParameterDefinition IntParam;
                    IntParam.Name = TEXT("OutputWidth");
                    IntParam.Type = EValueType::INT;
                    IntParam.Value = TEXT("1920");
                    Params.Add(IntParam);
                    CreatedJobDataAsset->SetJobParameters(Params);

                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = true;
                    FParameterDefinition BadValue;
                    BadValue.Name = TEXT("OutputWidth");
                    BadValue.Type = EValueType::INT;
                    BadValue.Value = TEXT("wide"); // not an integer
                    Output.Parameters.Add(BadValue);

                    const TArray<FString> Unapplied =
                        UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);

                    FString ResultValue;
                    for (const FParameterDefinition& P : CreatedJobDataAsset->GetJobParameters())
                    {
                        if (P.Name == TEXT("OutputWidth")) { ResultValue = P.Value; }
                    }
                    TestEqual("Unparseable INT value not written", ResultValue, FString(TEXT("1920")));
                    TestTrue("Bad-type parameter reported as unapplied", Unapplied.Contains(TEXT("OutputWidth")));
                });

            It("surfaces Python-provided UnappliedKeys back to the caller", [this]()
                {
                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = true;
                    Output.UnappliedKeys.Add(TEXT("deadline:unknownThing"));

                    const TArray<FString> Unapplied =
                        UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);

                    TestTrue("Python unapplied key passed through",
                        Unapplied.Contains(TEXT("deadline:unknownThing")));
                });

            It("reports a hook template parameter matching no job parameter as unapplied", [this]()
                {
                    TArray<FParameterDefinition> Params;
                    FParameterDefinition ParamA;
                    ParamA.Name = TEXT("OutputPath");
                    ParamA.Type = EValueType::STRING;
                    ParamA.Value = TEXT("/original/path");
                    Params.Add(ParamA);
                    CreatedJobDataAsset->SetJobParameters(Params);

                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = true;
                    FParameterDefinition HookMiss;
                    HookMiss.Name = TEXT("Nonexistent");
                    HookMiss.Type = EValueType::STRING;
                    HookMiss.Value = TEXT("ignored");
                    Output.Parameters.Add(HookMiss);

                    const TArray<FString> Unapplied =
                        UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);

                    TestEqual("No parameter added for the unmatched name",
                        CreatedJobDataAsset->GetJobParameters().Num(), 1);
                    TestTrue("Unmatched hook parameter reported as unapplied",
                        Unapplied.Contains(TEXT("Nonexistent")));
                });

            It("rejects a lowercase InitialState (case-sensitive) and reports it unapplied", [this]()
                {
                    FDeadlineCloudJobSharedSettingsStruct& Shared =
                        CreatedJobDataAsset->JobPresetStruct.JobSharedSettings;
                    const FString OriginalState = Shared.InitialState;

                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = true;
                    Output.bHasInitialState = true;
                    Output.InitialState = TEXT("ready"); // real word, wrong case (openjd is case-sensitive)

                    const TArray<FString> Unapplied =
                        UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);

                    TestEqual("Lowercase InitialState not written", Shared.InitialState, OriginalState);
                    TestTrue("Lowercase InitialState reported as unapplied",
                        Unapplied.Contains(TEXT("deadline:targetTaskRunStatus")));
                });

            It("matches template parameter names case-sensitively", [this]()
                {
                    TArray<FParameterDefinition> Params;
                    FParameterDefinition ParamA;
                    ParamA.Name = TEXT("OutputPath");
                    ParamA.Type = EValueType::STRING;
                    ParamA.Value = TEXT("/original");
                    Params.Add(ParamA);
                    CreatedJobDataAsset->SetJobParameters(Params);

                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = true;
                    FParameterDefinition HookWrongCase;
                    HookWrongCase.Name = TEXT("outputpath"); // wrong case, must NOT match OutputPath
                    HookWrongCase.Type = EValueType::STRING;
                    HookWrongCase.Value = TEXT("/hooked");
                    Output.Parameters.Add(HookWrongCase);

                    const TArray<FString> Unapplied =
                        UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);

                    FString OutputPathValue;
                    for (const FParameterDefinition& P : CreatedJobDataAsset->GetJobParameters())
                    {
                        if (P.Name == TEXT("OutputPath")) { OutputPathValue = P.Value; }
                    }
                    TestEqual("Case-mismatched name did not overwrite", OutputPathValue, FString(TEXT("/original")));
                    TestTrue("Case-mismatched hook name reported as unapplied",
                        Unapplied.Contains(TEXT("outputpath")));
                });

            It("accepts a FLOAT parameter in exponent form (e.g. 1e-05)", [this]()
                {
                    TArray<FParameterDefinition> Params;
                    FParameterDefinition FloatParam;
                    FloatParam.Name = TEXT("Threshold");
                    FloatParam.Type = EValueType::FLOAT;
                    FloatParam.Value = TEXT("0.5");
                    Params.Add(FloatParam);
                    CreatedJobDataAsset->SetJobParameters(Params);

                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = true;
                    FParameterDefinition HookFloat;
                    HookFloat.Name = TEXT("Threshold");
                    HookFloat.Type = EValueType::FLOAT;
                    HookFloat.Value = TEXT("1e-05"); // Python str(0.00001)
                    Output.Parameters.Add(HookFloat);

                    const TArray<FString> Unapplied =
                        UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);

                    FString ResultValue;
                    for (const FParameterDefinition& P : CreatedJobDataAsset->GetJobParameters())
                    {
                        if (P.Name == TEXT("Threshold")) { ResultValue = P.Value; }
                    }
                    TestEqual("Exponent-form FLOAT applied", ResultValue, FString(TEXT("1e-05")));
                    TestFalse("Exponent-form FLOAT not reported unapplied",
                        Unapplied.Contains(TEXT("Threshold")));
                });

            It("skips an over-length description (panel rule) and reports it unapplied", [this]()
                {
                    FDeadlineCloudJobSharedSettingsStruct& Shared =
                        CreatedJobDataAsset->JobPresetStruct.JobSharedSettings;
                    const FString OriginalDesc = Shared.Description;

                    FDeadlineCloudPreGuiHookOutput Output;
                    Output.bRan = true;
                    Output.bHasDescription = true;
                    Output.Description = FString::ChrN(3000, TEXT('x')); // > 2048 chars (panel-invalid)

                    const TArray<FString> Unapplied =
                        UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(CreatedJobDataAsset, Output);

                    TestEqual("Over-length description not written", Shared.Description, OriginalDesc);
                    TestTrue("Over-length description reported as unapplied",
                        Unapplied.Contains(TEXT("description")));
                });
        });
}
