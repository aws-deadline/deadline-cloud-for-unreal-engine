// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.


#include "PythonAPILibraries/DeadlineCloudPreGuiHookLibrary.h"

#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudInputValidationHelper.h"
#include "Framework/Notifications/NotificationManager.h"
#include "Widgets/Notifications/SNotificationList.h"

namespace
{
	// deadline:targetTaskRunStatus allowed values, matching the panel dropdown (GetJobInitialStateOptions)
	// and the Python JobSharedSettings allowedValues ["READY", "SUSPENDED"] (unreal_open_job_shared_settings.py).
	bool IsAllowedInitialState(const FString& Value)
	{
		// FString::operator== is case-INSENSITIVE in UE, but deadline:targetTaskRunStatus is
		// case-sensitive on the openjd side (allowedValues ["READY","SUSPENDED"], see
		// unreal_open_job_shared_settings.py). Compare case-sensitively so a lowercase hook typo
		// (e.g. "ready") is rejected + surfaced here rather than failing at submission.
		return Value.Equals(TEXT("READY"), ESearchCase::CaseSensitive)
			|| Value.Equals(TEXT("SUSPENDED"), ESearchCase::CaseSensitive);
	}

	// Whether a hook-supplied string parses as the parameter's declared OpenJD type. Non-numeric types
	// (STRING/PATH/...) accept anything; INT/FLOAT must actually parse so a typo in a hook value fails at
	// hook time (visibly) rather than silently at openjd parse / submission.
	bool ValueParsesAsType(const FString& Value, EValueType Type)
	{
		switch (Type)
		{
		case EValueType::INT:
		{
			if (Value.IsEmpty())
			{
				return false;
			}
			int32 Start = (Value[0] == TEXT('-') || Value[0] == TEXT('+')) ? 1 : 0;
			if (Start >= Value.Len())
			{
				return false;
			}
			for (int32 i = Start; i < Value.Len(); ++i)
			{
				if (!FChar::IsDigit(Value[i]))
				{
					return false;
				}
			}
			return true;
		}
		case EValueType::FLOAT:
		{
			// Not FString::IsNumeric(): it rejects exponent form (e.g. "1e-05", which is how Python
			// str() renders small/large floats) while accepting "." / "1.". LexTryParseString<double>
			// matches openjd's numeric parsing (exponent form is valid there).
			double Parsed = 0.0;
			return !Value.IsEmpty() && LexTryParseString(Parsed, *Value);
		}
		default:
			return true;
		}
	}
}

void UDeadlineCloudPreGuiHookLibrary::ApplyOutputToSharedSettings(
	FDeadlineCloudJobSharedSettingsStruct& Shared,
	const FDeadlineCloudPreGuiHookOutput& Output,
	TArray<FString>& OutUnappliedKeys)
{
	// Only fields the hook actually set (bHas* flags) overwrite the settings, so an empty/partial hook
	// output leaves everything else untouched. Each value is validated against the same rules the panel
	// widgets enforce; a value that fails is skipped and recorded in OutUnappliedKeys.
	if (Output.bHasName)
	{
		// JobSharedSettings.Name is declared ValidationType=JobName (DeadlineCloudJob.h) ->
		// CreateLengthAndIdentifierValidator(1, 64): length 1..64 AND IsValidIdentifier (first char
		// alpha or '_', remaining alnum or '_'). Validate against the same rule so a hook name the panel
		// itself would refuse (empty, spaces, hyphens, >64 chars) is skipped + surfaced here rather than
		// written straight through to fail at submission — matching the description / initial-state /
		// parameter-type checks.
		const FString Name = Output.Name.TrimStartAndEnd();
		FText NameError;
		if (FDeadlineCloudInputValidationHelper::IsValidLength(Name, 1, 64, NameError)
			&& FDeadlineCloudInputValidationHelper::IsValidIdentifier(Name, NameError))
		{
			Shared.Name = Name;
		}
		else
		{
			UE_LOG(LogTemp, Warning,
				TEXT("Pre-GUI hook: name '%s' failed validation (%s); skipping."), *Name, *NameError.ToString());
			OutUnappliedKeys.Add(TEXT("name"));
		}
	}
	if (Output.bHasDescription)
	{
		// Validate like the panel's JobDescription widget (length 0..2048, no control chars except
		// \n\r\t — see DeadlineCloudInputValidationHelper); a value that fails is skipped + surfaced
		// rather than written straight through to fail at submission.
		FText DescError;
		static const TSet<TCHAR> AllowedControl = { TEXT('\n'), TEXT('\r'), TEXT('\t') };
		if (FDeadlineCloudInputValidationHelper::IsValidLength(Output.Description, 0, 2048, DescError)
			&& FDeadlineCloudInputValidationHelper::ContainsNoControlCharacters(Output.Description, DescError, AllowedControl))
		{
			Shared.Description = Output.Description;
		}
		else
		{
			UE_LOG(LogTemp, Warning,
				TEXT("Pre-GUI hook: description failed validation (%s); skipping."), *DescError.ToString());
			OutUnappliedKeys.Add(TEXT("description"));
		}
	}
	if (Output.bHasPriority)
	{
		// Panel SpinBox clamps to [0, 100] (ClampMin/ClampMax); mirror that rather than reject.
		Shared.Priority = FMath::Clamp(Output.Priority, 0, 100);
	}
	if (Output.bHasInitialState)
	{
		if (IsAllowedInitialState(Output.InitialState))
		{
			Shared.InitialState = Output.InitialState;
		}
		else
		{
			// Free-form string here, but only READY/SUSPENDED are valid; an out-of-range value would show
			// as an invalid dropdown entry and fail at submission, so skip + surface it instead.
			UE_LOG(LogTemp, Warning,
				TEXT("Pre-GUI hook: ignoring invalid InitialState '%s' (expected READY or SUSPENDED)."),
				*Output.InitialState);
			OutUnappliedKeys.Add(TEXT("deadline:targetTaskRunStatus"));
		}
	}
	if (Output.bHasMaxFailedTasksCount)
	{
		// Panel SpinBox clamps to >= 0 (ClampMin=0).
		Shared.MaximumFailedTasksCount = FMath::Max(0, Output.MaximumFailedTasksCount);
	}
	if (Output.bHasMaxRetriesPerTask)
	{
		Shared.MaximumRetriesPerTask = FMath::Max(0, Output.MaximumRetriesPerTask);
	}
}

void UDeadlineCloudPreGuiHookLibrary::ApplyOutputToParameters(
	TArray<FParameterDefinition>& Parameters,
	const FDeadlineCloudPreGuiHookOutput& Output,
	TArray<FString>& OutUnappliedKeys)
{
	if (Output.Parameters.Num() == 0)
	{
		return;
	}

	// Apply hook-supplied template parameters onto the existing parameter definitions in place, matching
	// by name. Names with no matching parameter are ignored (same as the submitter). A value that does not
	// parse as the parameter's declared type is skipped + recorded rather than written unparseable.
	for (const FParameterDefinition& HookParam : Output.Parameters)
	{
		bool bMatchedByName = false;
		for (FParameterDefinition& JobParam : Parameters)
		{
			// Case-SENSITIVE (FString::operator== is not): match the Python submitter's exact-name
			// matching so a hook key "outputpath" does not clobber template parameter "OutputPath".
			if (JobParam.Name.Equals(HookParam.Name, ESearchCase::CaseSensitive))
			{
				bMatchedByName = true;
				if (ValueParsesAsType(HookParam.Value, JobParam.Type))
				{
					JobParam.Value = HookParam.Value;
				}
				else
				{
					UE_LOG(LogTemp, Warning,
						TEXT("Pre-GUI hook: parameter '%s' value '%s' does not parse as its declared type; skipping."),
						*HookParam.Name, *HookParam.Value);
					OutUnappliedKeys.Add(HookParam.Name);
				}
				break;
			}
		}
		if (!bMatchedByName)
		{
			// A hook parameter that matches no job template parameter cannot be applied. Surface it
			// (rather than dropping it silently) so a hook that set something with no effect is
			// visible to the artist — the exact case the UnappliedKeys notification exists for.
			UE_LOG(LogTemp, Warning,
				TEXT("Pre-GUI hook: parameter '%s' matches no job template parameter; skipping."),
				*HookParam.Name);
			OutUnappliedKeys.Add(HookParam.Name);
		}
	}
}

TArray<FString> UDeadlineCloudPreGuiHookLibrary::ApplyOutputToJob(
	UDeadlineCloudJob* Job, const FDeadlineCloudPreGuiHookOutput& Output)
{
	if (!Job || !Output.bRan)
	{
		return TArray<FString>();
	}

	// Start from the keys the Python side already couldn't map onto a field (Output.UnappliedKeys), then
	// let the apply helpers append any values they reject during validation, so the caller can surface the
	// full set to the artist.
	TArray<FString> Unapplied = Output.UnappliedKeys;

	ApplyOutputToSharedSettings(Job->JobPresetStruct.JobSharedSettings, Output, Unapplied);

	if (Output.Parameters.Num() > 0)
	{
		TArray<FParameterDefinition> JobParams = Job->GetJobParameters();
		ApplyOutputToParameters(JobParams, Output, Unapplied);
		Job->SetJobParameters(JobParams);
	}

	return Unapplied;
}

void UDeadlineCloudPreGuiHookLibrary::NotifyUnappliedKeys(const TArray<FString>& UnappliedKeys)
{
	if (UnappliedKeys.Num() == 0)
	{
		return;
	}
	const FString Joined = FString::Join(UnappliedKeys, TEXT(", "));
	FNotificationInfo Info(FText::FromString(FString::Printf(
		TEXT("Deadline Cloud pre-GUI hook: %d value(s) not applied (no matching field or failed validation): %s"),
		UnappliedKeys.Num(), *Joined)));
	Info.ExpireDuration = 8.0f;
	FSlateNotificationManager::Get().AddNotification(Info);
}
