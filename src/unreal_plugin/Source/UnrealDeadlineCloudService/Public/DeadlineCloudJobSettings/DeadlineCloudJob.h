#pragma once


#include "DeadlineCloudStep.h"
#include "CoreMinimal.h"
#include "DeadlineCloudJobDataAsset.h"
#include "DeadlineCloudEnvironment.h"
#include "DeadlineCloudJob.generated.h"

/**
 * All Deadline Cloud job settings container struct
 */


USTRUCT(BlueprintType)
struct UNREALDEADLINECLOUDSERVICE_API FDeadlineCloudJobParametersArray
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	TArray<FParameterDefinition> Parameters;
};


UCLASS(BlueprintType, Blueprintable, Config = Game)
class UNREALDEADLINECLOUDSERVICE_API UDeadlineCloudJob : public UDataAsset
{
	GENERATED_BODY()
public:

	UDeadlineCloudJob();

	FSimpleDelegate OnSomethingChanged;

	void TriggerChange()
	{
		OnSomethingChanged.Execute();
	}

	UPROPERTY(Config, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 1))
	FString Name;

	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 2))
	FFilePath PathToTemplate;

	/** Deadline cloud job settings container struct */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", DisplayName = "Job Preset", meta = (DisplayPriority = 3))
	FDeadlineCloudJobPresetStruct JobPresetStruct;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 6))
	TArray<UDeadlineCloudStep*> Steps;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 5))
	TArray<UDeadlineCloudEnvironment*> Environments;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters", meta = (DisplayPriority = 4))
	FDeadlineCloudJobParametersArray ParameterDefinition;

public:
	/*Read path */
	UFUNCTION()
	void OpenJobFile(const FString& Path);

	UFUNCTION()
	void ReadName(const FString& Path);

	FString GetDefaultParameterValue(const FString& ParameterName);

	UFUNCTION()
	FParametersConsistencyCheckResult CheckJobParametersConsistency(UDeadlineCloudJob* Self);

	UFUNCTION(BlueprintCallable, Category = "Parameters")
	TArray <FParameterDefinition> GetJobParameters();

	UFUNCTION(BlueprintCallable, Category="Parameters")
	void SetJobParameters(TArray<FParameterDefinition> InJobParameters);

	UFUNCTION()
	TArray<FString> GetCpuArchitectures();

	/** Returns list of Operating systems */
	UFUNCTION()
	TArray<FString> GetOperatingSystems();

	/** Returns list of Job initial states */
	UFUNCTION()
	TArray<FString> GetJobInitialStateOptions();
	
	UFUNCTION(BlueprintCallable, Category = "Parameters")
	void FixJobParametersConsistency(UDeadlineCloudJob* Job);

public:

	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override
	{
		Super::PostEditChangeProperty(PropertyChangedEvent);
		if (PropertyChangedEvent.Property != nullptr) {

			FName PropertyName = PropertyChangedEvent.Property->GetFName();
			if (PropertyName == "FilePath")
			{		
				OpenJobFile(PathToTemplate.FilePath);
				TriggerChange();
			}
		}
	}


};
