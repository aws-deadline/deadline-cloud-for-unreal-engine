#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudStep.generated.h"



UCLASS(BlueprintType, Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudStep : public UPrimaryDataAsset
{
	GENERATED_BODY()
public:

	UDeadlineCloudStep();
	//Config,
	UPROPERTY( EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	/** Read path */
	UFUNCTION()
	TArray <FStepParameterSpace> OpenStepFile(const FString& Path);
};