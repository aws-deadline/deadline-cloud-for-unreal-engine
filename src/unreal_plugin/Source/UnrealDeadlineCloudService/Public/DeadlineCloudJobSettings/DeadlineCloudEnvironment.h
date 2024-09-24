#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudEnvironment.generated.h"



UCLASS(BlueprintType, Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudEnvironment : public UPrimaryDataAsset
{
	GENERATED_BODY()
public:

	UDeadlineCloudEnvironment();
	//Config,
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	/** Read path */
	UFUNCTION()
	TArray <FEnvironmentParameterDefinition> OpenEnvFile(const FString& Path);
};