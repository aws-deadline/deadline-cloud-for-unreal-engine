#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
//#include "DeadlineCloudStatusHandler.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "DetailLayoutBuilder.h"
#include "IDetailCustomization.h"


class UDeadlineCloudJob;

class FDeadlineCloudJobDetails : public IDetailCustomization
{
private:
    TWeakObjectPtr<UDeadlineCloudJob> CustomizedSettings;
//    TUniquePtr<FDeadlineCloudStatusHandler> DeadlineCloudStatusHandler;

public:
    static TSharedRef<IDetailCustomization> MakeInstance();

    // this method is called when we open UDeadlineCloudJob in UI
    virtual void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;

};