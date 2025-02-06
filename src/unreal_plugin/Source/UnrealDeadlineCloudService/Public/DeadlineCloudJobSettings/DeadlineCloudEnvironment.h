// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudEnvironment.generated.h"

USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudEnvironmentVariablesMap
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
    TMap<FString, FString> Variables;
};

USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudEnvironmentOverride
{
    GENERATED_BODY()

    UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "Parameters")
	FString Name;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FDeadlineCloudEnvironmentVariablesMap Variables;
};

UCLASS(BlueprintType, Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudEnvironment : public UDataAsset
{
	GENERATED_BODY()
public:

	UDeadlineCloudEnvironment();

	FSimpleDelegate OnPathChanged;

	UPROPERTY(VisibleAnywhere, BlueprintReadWrite, Category = "Parameters")
	FString Name; 

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FDeadlineCloudEnvironmentVariablesMap Variables;

	/** Read path */
	UFUNCTION()
	void OpenEnvFile(const FString& Path);

	UFUNCTION()
	FParametersConsistencyCheckResult CheckEnvironmentVariablesConsistency(const UDeadlineCloudEnvironment* Env) ;

	UFUNCTION()
	void FixEnvironmentVariablesConsistency(UDeadlineCloudEnvironment* Env);

	FDeadlineCloudEnvironmentOverride GetEnvironmentData();

	bool IsDefaultVariables();
	void ResetVariables();

	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
};