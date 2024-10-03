#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"

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
