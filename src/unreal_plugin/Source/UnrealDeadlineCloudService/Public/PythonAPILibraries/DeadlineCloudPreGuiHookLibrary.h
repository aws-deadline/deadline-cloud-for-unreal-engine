// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "PythonAPILibrary.h"
#include "PythonYamlLibrary.h"
#include "UObject/Object.h"
#include "DeadlineCloudPreGuiHookLibrary.generated.h"

class UDeadlineCloudJob;
// Referenced only by reference in ApplyOutputToSharedSettings below; the full definition
// (DeadlineCloudJobSettings/DeadlineCloudJob.h) is included in the .cpp.
struct FDeadlineCloudJobSharedSettingsStruct;

/**
 * Merged output of a pre-GUI hook run, returned from Python to C++.
 *
 * Each scalar field is paired with a bHas* flag so the C++ side only overwrites a
 * Job Shared Settings field when the hook actually set it (a hook may emit only some keys).
 * See DeadlineCloudPreGuiHookLibraryImplementation.run_pre_gui_hooks in
 * Content/Python/pre_gui_hook_library.py.
 */
USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudPreGuiHookOutput
{
	GENERATED_BODY()

	/** Whether any pre-GUI hook actually ran and produced output. False => no hooks / declined / API unavailable => the caller must treat this as a no-op. */
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	bool bRan = false;

	/** Job name (deadline-cloud "name"). Applied to JobSharedSettings.Name when bHasName. */
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	bool bHasName = false;
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	FString Name;

	/** Job description (deadline-cloud "description"). */
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	bool bHasDescription = false;
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	FString Description;

	/** deadline:priority */
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	bool bHasPriority = false;
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	int32 Priority = 50;

	/** deadline:targetTaskRunStatus */
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	bool bHasInitialState = false;
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	FString InitialState;

	/** deadline:maxFailedTasksCount */
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	bool bHasMaxFailedTasksCount = false;
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	int32 MaximumFailedTasksCount = 0;

	/** deadline:maxRetriesPerTask */
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	bool bHasMaxRetriesPerTask = false;
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	int32 MaximumRetriesPerTask = 2;

	/** Template parameters the hook set (name -> value); applied onto the job's ParameterDefinition in place. */
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	TArray<FParameterDefinition> Parameters;

	/** Hook parameter names that matched neither a template parameter nor a shared setting; surfaced to the user as a warning. */
	UPROPERTY(BlueprintReadWrite, Category = "Deadline Cloud")
	TArray<FString> UnappliedKeys;
};

/**
 * Deadline Cloud "pre-GUI hook" function library. Intended to be implemented in Python:
 * Content/Python/pre_gui_hook_library.py -> DeadlineCloudPreGuiHookLibraryImplementation.
 *
 * The C++ Details customization (FDeadlineCloudJobDetails) calls RunPreGuiHooks once per
 * UDeadlineCloudJob instance, before the panel field widgets are populated, so studios can
 * pre-populate Job Shared Settings from DEADLINE_HOOKS_DIR pre-GUI hooks.
 */
UCLASS()
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudPreGuiHookLibrary
	: public UObject, public TPythonAPILibraryBase<UDeadlineCloudPreGuiHookLibrary>
{
	GENERATED_BODY()

public:
	/**
	 * Run environment-sourced pre-GUI hooks and return their merged output.
	 * Confirmation (gated by settings.auto_accept) is handled inside the Python implementation.
	 * The current job state is passed into the hook context so hooks can *adjust* (not just set) it
	 * — matching the other DCCs, where a hook can read the current priority/parameters (e.g. "cap
	 * priority at 60", "if OutputPath is under /scratch, SUSPEND").
	 * @param JobName Current job name, passed to hooks as the initial jobName in the hook context.
	 * @param Priority Current job priority, passed to hooks as the initial priority in the context.
	 * @param CurrentParameters Current job template parameters (name/value/type), passed to hooks as
	 *        the initial parameters dict in the context.
	 * @return Merged pre-GUI output; bRan=false means no-op (no hooks / declined / unavailable).
	 */
	UFUNCTION(BlueprintImplementableEvent)
	FDeadlineCloudPreGuiHookOutput RunPreGuiHooks(
		const FString& JobName,
		int32 Priority,
		const TArray<FParameterDefinition>& CurrentParameters);

	/**
	 * Apply merged pre-GUI hook output onto a job's Job Shared Settings + parameter definitions.
	 * Only fields the hook actually set (bHas* flags) overwrite the job; if Output.bRan is false
	 * this is a no-op. Static (no Python impl needed) so the C++ Details customization and the
	 * automation spec share one code path. Thin wrapper over ApplyOutputToSharedSettings +
	 * ApplyOutputToParameters for the UDeadlineCloudJob data-asset panel path.
	 * @return the keys the hook set that were not applied (unmappable or failed validation), so the
	 *         caller can surface them to the artist. Empty when everything applied (or Output.bRan false).
	 */
	static TArray<FString> ApplyOutputToJob(UDeadlineCloudJob* Job, const FDeadlineCloudPreGuiHookOutput& Output);

	/**
	 * Apply the hook's shared-setting fields onto a FDeadlineCloudJobSharedSettingsStruct, validating
	 * each against the same rules the panel widgets enforce (Name = JobName rule: length 1..64 +
	 * IsValidIdentifier; Description length 0..2048 + no control chars; Priority clamped to [0,100];
	 * counts >= 0; InitialState restricted to READY/SUSPENDED). A value that fails validation is skipped
	 * and its key appended to OutUnappliedKeys instead of being written (so a malformed hook degrades visibly
	 * at hook time rather than at submission). Shared by the data-asset job and the MRQ executor job's
	 * PresetOverrides, so both submission surfaces enforce identical protection.
	 */
	static void ApplyOutputToSharedSettings(
		FDeadlineCloudJobSharedSettingsStruct& Shared,
		const FDeadlineCloudPreGuiHookOutput& Output,
		TArray<FString>& OutUnappliedKeys);

	/**
	 * Apply the hook's template parameters onto ParameterDefinitions in place, matching by name.
	 * A hook value that does not parse as the parameter's declared EValueType (e.g. "wide" for an INT)
	 * is skipped and its name appended to OutUnappliedKeys rather than baked onto the job to fail later
	 * at submission. Names with no matching parameter are ignored. (Submitter-managed parameters such
	 * as ProjectFilePath / ExtraCmdArgs / Perforce settings are filtered out on the Python side, in
	 * pre_gui_hook_library._build_output, so they never reach here.)
	 */
	static void ApplyOutputToParameters(
		TArray<FParameterDefinition>& Parameters,
		const FDeadlineCloudPreGuiHookOutput& Output,
		TArray<FString>& OutUnappliedKeys);

	/**
	 * Surface pre-GUI hook keys that could not be applied (unmappable / failed validation / no matching
	 * parameter) as a transient editor Slate notification, so a hook that set something which silently
	 * did not take effect is visible to the artist rather than only logged. Defined once here and called
	 * from both panel sites (data-asset + MRQ) — a single definition avoids duplicate anonymous-namespace
	 * copies, which collide as a redefinition when UE's unity build concatenates the two .cpp files.
	 */
	static void NotifyUnappliedKeys(const TArray<FString>& UnappliedKeys);
};
