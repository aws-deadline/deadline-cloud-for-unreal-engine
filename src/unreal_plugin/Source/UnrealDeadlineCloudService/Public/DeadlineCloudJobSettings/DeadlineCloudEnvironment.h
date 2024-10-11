#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudEnvironment.generated.h"



UCLASS(BlueprintType, Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudEnvironment : public UDataAsset
{
	GENERATED_BODY()
public:

	UDeadlineCloudEnvironment();
	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "Parameters")
	FString Name; 

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	TMap<FString, FString> Variables;

	/** Read path */
	UFUNCTION()
	void OpenEnvFile(const FString& Path);

	UFUNCTION()
	void CheckEnvironmentVariablesConsistency( UDeadlineCloudEnvironment* Self) ;

	//TArray <FEnvironmentStruct> OpenEnvFile(const FString& Path);

	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
};