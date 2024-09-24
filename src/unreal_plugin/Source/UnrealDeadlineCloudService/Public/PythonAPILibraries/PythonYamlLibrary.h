#pragma once

#include "CoreMinimal.h"
#include "PythonAPILibrary.h"
#include "UObject/Object.h"
#include "PythonYamlLibrary.generated.h"

/*
 Intended to be implemented in Python: Content/Python/unreal_yaml_api.py
 */


 /*
  Job .yaml struct
  */
UENUM(BlueprintType)
enum class EValueType : uint8
{
	INT UMETA(DisplayName = "Integer"),
	FLOAT   UMETA(DisplayName = "Float"),
	STRING UMETA(DisplayName = "String"),
	PATH    UMETA(DisplayName = "Path")
};

USTRUCT(BlueprintType)
struct FParameterDefinition
{
	GENERATED_BODY()

	// Name
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job")
	FString Name;

	// Type	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job")
	EValueType Type;


	FParameterDefinition()
		: Name("DefaultName"),
		Type(EValueType::STRING)
	{}
};
/*
Step .yaml struct
 */

USTRUCT(BlueprintType)
struct FStepTaskParameterDefinition
{
	GENERATED_BODY()


	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Step")
	FString Name;

	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Step")
	EValueType Type;


	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Step")
	TArray <FString> Range;

};

USTRUCT(BlueprintType)
struct FStepParameterSpace
{
	GENERATED_BODY()

	// Name
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Step")
	FString Name;

	// Tasks Array	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Step")
	TArray<FStepTaskParameterDefinition> StepTaskParameterDefinition;

	// Value	
	//UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Step")
	//FString Script;

};

/*
Env .yaml struct
 */

USTRUCT(BlueprintType)
struct FEnvironmentParameterDefinition
{
	GENERATED_BODY()

	// Name
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Environment")
	FString Name;

	// Value	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Environment")
	FString Description;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Step")
	TArray <FString> Variables;
};





UCLASS()
class UNREALDEADLINECLOUDSERVICE_API UPythonYamlLibrary: public UObject, public TPythonAPILibraryBase<UPythonYamlLibrary>
{
	GENERATED_BODY()

public:

	// job
	UFUNCTION(BlueprintImplementableEvent)
	TArray <FParameterDefinition> OpenJobFile(const FString& Path);

	// steps 
	UFUNCTION(BlueprintImplementableEvent)
	TArray <FStepParameterSpace> OpenStepFile(const FString& Path);

	// env
	UFUNCTION(BlueprintImplementableEvent)
	TArray <FEnvironmentParameterDefinition> OpenEnvFile(const FString& Path);
};
	
