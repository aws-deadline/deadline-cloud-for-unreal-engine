#include "DeadlineCloudJobSettings/DeadlineCloudJobDataAsset.h"

#include "PythonAPILibraries/DeadlineCloudJobBundleLibrary.h"

UDeadlineCloudJobPreset::UDeadlineCloudJobPreset()
{
}

TArray<FString> UDeadlineCloudJobPreset::GetCpuArchitectures()
{
	return UDeadlineCloudJobBundleLibrary::Get()->GetCpuArchitectures();
}

TArray<FString> UDeadlineCloudJobPreset::GetOperatingSystems()
{
	return UDeadlineCloudJobBundleLibrary::Get()->GetOperatingSystems();
}

TArray<FString> UDeadlineCloudJobPreset::GetJobInitialStateOptions()
{
	return UDeadlineCloudJobBundleLibrary::Get()->GetJobInitialStateOptions();
}
