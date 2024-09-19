#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "DetailLayoutBuilder.h"
#include "IDetailCustomization.h"


class UDeadlineCloudJob;


class FDeadlineCloudJobDetails : public IDetailCustomization
{
private:
    TWeakObjectPtr<UDeadlineCloudJob> Settings;
    TArray <FParameterDefinition> Parameters;

public:
    static TSharedRef<IDetailCustomization> MakeInstance();
    virtual  void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;
   
private:
    FString CurrentFilePath;
    FString GetCurrentFilePath() const
    {
        return CurrentFilePath;
    }

    void OnFilePathPicked(const FString& PickedPath)
    {
        CurrentFilePath = PickedPath;
    }

    TSharedRef<SWidget> CreateNameWidget(FString Parameter);
    TSharedRef<SWidget> CreateStringValueWidget(FString Parameter);
    TSharedRef<SWidget> CreateValuePathWidget(FString Parameter);
    TSharedRef<SWidget> CreateValuePathDefaultWidget(FString Parameter);




};