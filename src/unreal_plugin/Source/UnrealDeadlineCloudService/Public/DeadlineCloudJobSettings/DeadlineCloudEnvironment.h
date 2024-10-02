#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudEnvironment.generated.h"



UCLASS(BlueprintType, Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudEnvironment : public UDataAsset
{
	GENERATED_BODY()
public:

	UDeadlineCloudEnvironment();
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FString Name; 

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FEnvironmentStruct EnvironmentStructure;

	/** Read path */
	UFUNCTION()
	TArray <FEnvironmentStruct> OpenEnvFile(const FString& Path);
};