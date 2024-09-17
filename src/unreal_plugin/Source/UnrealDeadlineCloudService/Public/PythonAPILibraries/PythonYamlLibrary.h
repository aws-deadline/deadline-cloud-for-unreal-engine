#pragma once

#include "CoreMinimal.h"
#include "PythonAPILibrary.h"
//#include "Kismet/BlueprintFunctionLibrary.h"
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
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Name-Value Pair")
	FString Name;

	// Value	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Name-Value Pair")
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

	// Name
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Name-Value Pair")
	FString Name;

	// Value	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Name-Value Pair")
	EValueType Type;

	// Value	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Name-Value Pair")
	FString Range;

};
USTRUCT(BlueprintType)
struct FStepParameterDefinition
{
	GENERATED_BODY()

	// Name
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Name-Value Pair")
	FString Name;

	// Value	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Name-Value Pair")
	FStepTaskParameterDefinition Task;

	// Value	
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Name-Value Pair")
	FString Script;

};





UCLASS()
class UNREALDEADLINECLOUDSERVICE_API UPythonYamlLibrary: public UObject, public TPythonAPILibraryBase<UPythonYamlLibrary>
{
	GENERATED_BODY()

public:

	// job
	UFUNCTION(BlueprintImplementableEvent)
	TArray <FParameterDefinition> OpenJobFile(const FString& Path);

	// step
	UFUNCTION(BlueprintImplementableEvent)
	TArray <FStepParameterDefinition> OpenStepFile(const FString& Path);
};
	
