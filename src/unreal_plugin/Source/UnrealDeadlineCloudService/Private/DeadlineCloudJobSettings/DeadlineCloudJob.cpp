#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"


UDeadlineCloudJob::UDeadlineCloudJob()
{
}


void UDeadlineCloudJob::OpenJobFile(const FString& Path)
{
	JobParameters = UPythonYamlLibrary::Get()->OpenJobFile(Path);
}

void UDeadlineCloudJob::ReadName(const FString& Path)
{
	Name = UPythonYamlLibrary::Get()->ReadName(Path);
}

TArray<FParameterDefinition> UDeadlineCloudJob::GetJobParameters()
{
	return JobParameters;
}


FParametersConsistencyCheckResult UDeadlineCloudJob::CheckJobParametersConsistency(UDeadlineCloudJob* Self)
{
	FParametersConsistencyCheckResult result = UPythonParametersConsistencyChecker::Get()->CheckJobParametersConsistency(Self);
	return result;
}

void UDeadlineCloudJob::SetJobParameters(TArray<FParameterDefinition> InJobParameters)
{
    JobParameters = InJobParameters;
}