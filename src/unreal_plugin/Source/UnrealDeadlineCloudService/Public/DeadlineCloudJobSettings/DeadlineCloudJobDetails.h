#pragma once

#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "DetailLayoutBuilder.h"
#include "IDetailCustomization.h"

 #include "Fonts/SlateFontInfo.h"
 #include "Misc/App.h"
 #include "Misc/FileHelper.h"
 #include "Misc/Paths.h"
 #include "Modules/ModuleManager.h"
 #include "Styling/SlateTypes.h"
 #include "Widgets/SBoxPanel.h"
 #include "Widgets/Text/STextBlock.h"
 #include "Widgets/Input/SButton.h"
 #include "Widgets/Input/SCheckBox.h"
 #include "Widgets/Input/SEditableTextBox.h"
 #include "Widgets/Input/SFilePathPicker.h"
 #include "Widgets/Input/SMultiLineEditableTextBox.h"
 #include "Widgets/Layout/SBorder.h"
 #include "Widgets/Layout/SSeparator.h"
 #include "Widgets/Notifications/SNotificationList.h"
 #include "Framework/Notifications/NotificationManager.h"
 #include "EditorDirectories.h"
 #include "EditorStyleSet.h"
 #include "SourceControlOperations.h"



class UDeadlineCloudJob;


class FDeadlineCloudJobDetails : public IDetailCustomization
{
private:
    TWeakObjectPtr<UDeadlineCloudJob> Settings;

public:

    static TSharedRef<IDetailCustomization> MakeInstance();
    virtual  void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;
    IDetailLayoutBuilder* MyDetailLayout;


public:
    
 //   UFUNCTION()
    void HandlePathChanged()
    {
        if (Settings.IsValid())
        {

            UE_LOG(LogTemp, Log, TEXT("Something changed!"));
        }
    }
//    bool GetBooleanValue() const { return bMyBoolean; }
    void OnButtonClicked();

private:

    TSharedRef<SWidget> CreateNameWidget(FString Parameter);
    TSharedRef<SWidget> CreatePathWidget(FString Parameter);
    TSharedRef<SWidget> CreateStringWidget(FParameterDefinition *Parameter);

    void ForceRefreshDetails();
    bool CheckConsistency(UDeadlineCloudJob* Job);


    bool CheckConsidtensyPassed;
public:
   // FSimpleDelegate OnSomethingChanged;
    /*
    DECLARE_DELEGATE_OneParam(FOnBooleanChanged, bool);

    bool GetBooleanValue() const { return bMyBoolean; }

    void SetBooleanValue(bool bNewValue)
    {
        if (bMyBoolean != bNewValue)
        {
            bMyBoolean = bNewValue;
            OnBooleanChanged.ExecuteIfBound(bMyBoolean);
        }
    }

    FOnBooleanChanged OnBooleanChanged;
*/
    EVisibility GetWidgetVisibility() const
    {
        // if true, widget hidden
        return !(CheckConsidtensyPassed) ? EVisibility::Visible : EVisibility::Collapsed;
    }


};

