#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJob.generated.h"



UCLASS(BlueprintType, Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudJob : public UObject
{
	GENERATED_BODY()
public:

	UDeadlineCloudJob();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	/** Read path */
	UFUNCTION()
	TArray <FParameterDefinition> OpenJobFile(const FString& Path);

};

//for test only
UCLASS(BlueprintType, Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API ADeadlineTest : public AActor
{
	GENERATED_BODY()
public:

	ADeadlineTest() {};

};
