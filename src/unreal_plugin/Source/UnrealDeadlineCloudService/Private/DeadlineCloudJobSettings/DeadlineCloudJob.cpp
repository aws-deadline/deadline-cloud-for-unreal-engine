// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/DeadlineCloudJobBundleLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"


UDeadlineCloudJob::UDeadlineCloudJob()
{
}

void UDeadlineCloudJob::OpenJobFile(const FString& Path)
{
    ParameterDefinition.Parameters = UPythonYamlLibrary::Get()->OpenJobFile(Path);
}

void UDeadlineCloudJob::ReadName(const FString& Path)
{
    Name = UPythonYamlLibrary::Get()->ReadName(Path);
}

FString UDeadlineCloudJob::GetDefaultParameterValue(const FString& ParameterName)
{
    TArray<FParameterDefinition> DefaultParameters = UPythonYamlLibrary::Get()->OpenJobFile(PathToTemplate.FilePath);
    for (FParameterDefinition& Parameter : DefaultParameters)
    {
        if (Parameter.Name == ParameterName)
        {
            return Parameter.Value;
        }
    }

    return "";
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
    UPythonParametersConsistencyChecker::Get()->FixJobParametersConsistency(Job);
}


TArray<FStepTaskParameterDefinition> UDeadlineCloudJob::GetTaskChunkSizeFromRenderStep() const
{
    TArray<FStepTaskParameterDefinition> result;
    UDeadlineCloudRenderStep* StepAsset;
    for (auto step : Steps) {
        StepAsset = Cast<UDeadlineCloudRenderStep>(step);
        if (StepAsset)
        {
            for (auto parameter : StepAsset->TaskParameterDefinitions.Parameters)
            {
                if (parameter.Name == "ChunkSize")
                {
                    result.Add(parameter);

                }
            }
            
        }
       
    }
    return result;
}


FParametersConsistencyCheckResult UDeadlineCloudJob::CheckJobParametersConsistency(UDeadlineCloudJob* Job)
{
    return UPythonParametersConsistencyChecker::Get()->CheckJobParametersConsistency(Job);
}

TArray<FString> UDeadlineCloudJob::GetCpuArchitectures()
{
    return UDeadlineCloudJobBundleLibrary::Get()->GetCpuArchitectures();
}

TArray<FString> UDeadlineCloudJob::GetOperatingSystems()
{
    return UDeadlineCloudJobBundleLibrary::Get()->GetOperatingSystems();
}

TArray<FString> UDeadlineCloudJob::GetJobInitialStateOptions()
{
    return UDeadlineCloudJobBundleLibrary::Get()->GetJobInitialStateOptions();
}
