#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudEnvironment.h"
#include "DeadlineCloudStep.generated.h"



UCLASS(BlueprintType, Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudStep : public UPrimaryDataAsset
{
	GENERATED_BODY()
public:

	UDeadlineCloudStep();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FString depends_on;

	UPROPERTY( EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	UDeadlineCloudEnvironment* Environment;

	/** Read path */
	UFUNCTION()
	TArray <FStepParameterSpace> OpenStepFile(const FString& Path);
};