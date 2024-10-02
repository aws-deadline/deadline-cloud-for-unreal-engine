#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudEnvironment.generated.h"



UCLASS(BlueprintType)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudEnvironment : public UObject
{
	GENERATED_BODY()
public:

	UDeadlineCloudEnvironment();
	//Config,
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FEnvironmentStruct EnvironmentStructure;

	/** Read path */
	UFUNCTION()
	TArray <FEnvironmentStruct> OpenEnvFile(const FString& Path);
};