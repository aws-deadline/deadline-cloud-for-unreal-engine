// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "PythonAPILibrary.h"
#include "PythonYamlLibrary.h"
#include "UObject/Object.h"
#include "PythonParametersConsistencyChecker.generated.h"

USTRUCT(BlueprintType)
struct FParametersConsistencyCheckResult 

{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Checker")
    bool Passed = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Checker")
    FString Reason;

};



UCLASS()
class UNREALDEADLINECLOUDSERVICE_API UPythonParametersConsistencyChecker : public UObject, public TPythonAPILibraryBase<UPythonParametersConsistencyChecker>
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintImplementableEvent)
    FParametersConsistencyCheckResult    CheckJobParametersConsistency(const UDeadlineCloudJob* Job);

	UFUNCTION(BlueprintImplementableEvent)
	void FixJobParametersConsistency (UDeadlineCloudJob* Job);
   
	UFUNCTION(BlueprintImplementableEvent)
	FParametersConsistencyCheckResult	CheckStepParametersConsistency(const UDeadlineCloudStep* Step);

	UFUNCTION(BlueprintImplementableEvent)
	void	FixStepParametersConsistency (UDeadlineCloudStep* Step);

	UFUNCTION(BlueprintImplementableEvent)
	FParametersConsistencyCheckResult	CheckEnvironmentVariablesConsistency(const UDeadlineCloudEnvironment* Environment);

	UFUNCTION(BlueprintImplementableEvent)
	void	FixEnvironmentVariablesConsistency(UDeadlineCloudEnvironment* Environment);
 
};