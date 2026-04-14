// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/DeadlineCloudJobBundleLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"


UDeadlineCloudJob::UDeadlineCloudJob()
{
    HiddenVarsManager.OnGetAllNames.BindLambda([this]()
        {
            TSet<FName> Names;
            for (const auto& P : ParameterDefinition.Parameters)
            {
                Names.Add(FName(*P.Name));
            }
            return Names;
        });

    HiddenVarsManager.OnGetDefaultHidden.BindLambda([this]()
        {
            TSet<FName> Def;
            for (const auto& P : ParameterDefinition.Parameters)
            {
                if (P.UserInterfaceControl == EUserInterfaceControl::HIDDEN)
                {
                    Def.Add(FName(*P.Name));
                }
            }
            return Def;
        });

    HiddenVarsManager.OnChanged.BindLambda([this]()
        {
            Modify();
            MarkPackageDirty();
            ParameterHiddenEvent();
        });
}

void UDeadlineCloudJob::OpenJobFile(const FString& Path)
{
    if (auto Library = UPythonYamlLibrary::Get())
    {
        ParameterDefinition.Parameters = Library->OpenJobFile(Path);
        GetHiddenManager().ResetToDefault();
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonYamlLibrary"));
    }
}

void UDeadlineCloudJob::ReadName(const FString& Path)
{
    if (auto Library = UPythonYamlLibrary::Get())
    {
        Name = Library->ReadName(Path);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonYamlLibrary"));
    }
}

FString UDeadlineCloudJob::GetDefaultParameterValue(const FString& ParameterName)
{
    if (auto Library = UPythonYamlLibrary::Get())
    {
        TArray<FParameterDefinition> DefaultParameters = Library->OpenJobFile(PathToTemplate.FilePath);
        for (FParameterDefinition& Parameter : DefaultParameters)
        {
            if (Parameter.Name == ParameterName)
            {
                return Parameter.Value;
            }
        }
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonYamlLibrary"));
    }
    return "";
}


void UDeadlineCloudJob::FixConsistencyForHiddenParameters()
{
    GetHiddenManager().PruneUnknown();
}

TArray<FParameterDefinition> UDeadlineCloudJob::GetJobParameters()
{
    return ParameterDefinition.Parameters;
}

void UDeadlineCloudJob::SetJobParameters(TArray<FParameterDefinition> InParameters)
{
    ParameterDefinition.Parameters = InParameters;
}

void UDeadlineCloudJob::FixJobParametersConsistency(UDeadlineCloudJob* Job)
{
    if (auto Library = UPythonParametersConsistencyChecker::Get())
    {
        Library->FixJobParametersConsistency(Job);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonParametersConsistencyChecker"));
    }
}


TArray<FStepTaskParameterDefinition> UDeadlineCloudJob::GetAllStepParameters() const
{
    TArray<FStepTaskParameterDefinition> result;
    UDeadlineCloudStep* StepAsset;
    StepAsset = Steps.IsValidIndex(0) ? Steps[0] : nullptr;

    if (StepAsset)
    {
        result = StepAsset->GetStepParameters();
    }
    return result;
}

TArray<FParameterDefinition> UDeadlineCloudJob::GetParametersDataToOverride() const
{
    TArray<FParameterDefinition> Result;
	for (const FParameterDefinition& Param : ParameterDefinition.Parameters)
    {
        if (!GetHiddenManager().Contains(FName(*Param.Name)))
        {
			Result.Add(Param);
		}
	}

	return Result;
}

void UDeadlineCloudJob::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
    Super::PostEditChangeProperty(PropertyChangedEvent);
    if (PropertyChangedEvent.Property != nullptr) {

        FName PropertyName = PropertyChangedEvent.Property->GetFName();
        if (PropertyName == "FilePath")
        {
            OpenJobFile(PathToTemplate.FilePath);
            TriggerChange();
        }
    }
}


FParametersConsistencyCheckResult UDeadlineCloudJob::CheckJobParametersConsistency(const UDeadlineCloudJob* Job)
{
    if (auto Library = UPythonParametersConsistencyChecker::Get())
    {
        return Library->CheckJobParametersConsistency(Job);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get PythonParametersConsistencyChecker"));
    }
    return FParametersConsistencyCheckResult();
}

TArray<FString> UDeadlineCloudJob::GetCpuArchitectures()
{
    if (auto Library = UDeadlineCloudJobBundleLibrary::Get())
    {
        return Library->GetCpuArchitectures();
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
    }
    return {};
}

TArray<FString> UDeadlineCloudJob::GetOperatingSystems()
{
    if (auto Library = UDeadlineCloudJobBundleLibrary::Get())
    {
        return Library->GetOperatingSystems();
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
    }
    return {};
}

TArray<FString> UDeadlineCloudJob::GetJobInitialStateOptions()
{
    if (auto Library = UDeadlineCloudJobBundleLibrary::Get())
    {
        return Library->GetJobInitialStateOptions();
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
    }
    return {};
}