#pragma once


#include "DeadlineCloudStep.h"
#include "CoreMinimal.h"
#include "DeadlineCloudJobDataAsset.h"
#include "DeadlineCloudEnvironment.h"
#include "DeadlineCloudJob.generated.h"

/**
 * All Deadline Cloud job settings container struct
 */



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

	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FString Name;

	UPROPERTY(Config, EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	FFilePath PathToTemplate;

	/** Deadline cloud job settings container struct */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Job Preset")
	FDeadlineCloudJobPresetStruct JobPresetStruct;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	TArray<UDeadlineCloudStep*> Steps;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Parameters")
	TArray<UDeadlineCloudEnvironment*> Environments;

private:	
	TArray <FParameterDefinition> JobParameters;

public:
	/*Read path */
	UFUNCTION()
	void OpenJobFile(const FString& Path);

	UFUNCTION()
	void ReadName(const FString& Path);

	UFUNCTION()
	void CheckJobParametersConsistency(UDeadlineCloudJob* Self);

	TArray <FParameterDefinition> GetJobParameters();



public:

	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override
	{
		Super::PostEditChangeProperty(PropertyChangedEvent);
		if (PropertyChangedEvent.Property != nullptr) {

			FName PropertyName = PropertyChangedEvent.Property->GetFName();
			if (PropertyName == "FilePath")
			{		
				TriggerChange();
			}
		}
	}


};
