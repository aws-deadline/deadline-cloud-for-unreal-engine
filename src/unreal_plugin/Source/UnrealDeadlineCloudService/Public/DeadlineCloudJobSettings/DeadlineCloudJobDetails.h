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

#include "PropertyCustomizationHelpers.h"


class UDeadlineCloudJob;

class FDeadlineCloudJobParametersArrayBuilder
	: public FDetailArrayBuilder
	, public TSharedFromThis<FDeadlineCloudJobParametersArrayBuilder>
{
public:

	static TSharedRef<FDeadlineCloudJobParametersArrayBuilder> MakeInstance(
		TSharedRef<IPropertyHandle> InPropertyHandle);

	FDeadlineCloudJobParametersArrayBuilder(
		TSharedRef<IPropertyHandle> InPropertyHandle);
	
	virtual void GenerateHeaderRowContent(FDetailWidgetRow& NodeRow) override;

	void GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent);

	FUIAction EmptyCopyPasteAction;
	FOnIsEnabled OnIsEnabled;

private:
    static UDeadlineCloudJob* GetOuterJob(TSharedRef<IPropertyHandle> Handle);

	void OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32 ElementIndex, IDetailChildrenBuilder& ChildrenBuilder) const;

	TSharedPtr<IPropertyHandleArray> ArrayProperty;
    TSharedRef<IPropertyHandle> BaseProperty;
};

class FDeadlineCloudJobParametersArrayCustomization : public IPropertyTypeCustomization
{
public:

	static TSharedRef<IPropertyTypeCustomization> MakeInstance()
	{
		return MakeShared<FDeadlineCloudJobParametersArrayCustomization>();
	}

	FDeadlineCloudJobParametersArrayCustomization() {}
	
	/** Begin IPropertyTypeCustomization interface */
	virtual void CustomizeHeader(
		TSharedRef<IPropertyHandle> InPropertyHandle,
		FDetailWidgetRow& InHeaderRow,
		IPropertyTypeCustomizationUtils& InCustomizationUtils) override;

	virtual void CustomizeChildren(
		TSharedRef<IPropertyHandle> InPropertyHandle,
		IDetailChildrenBuilder& InChildBuilder,
		IPropertyTypeCustomizationUtils& InCustomizationUtils) override;
	/** End IPropertyTypeCustomization interface */
	
private:
	/*static UDeadlineCloudStep* GetOuterJob(TSharedRef<IPropertyHandle> Handle);*/

	TSharedPtr<FDeadlineCloudJobParametersArrayBuilder> ArrayBuilder;
};


class FDeadlineCloudJobDetails : public IDetailCustomization
{
private:


public:

    static TSharedRef<IDetailCustomization> MakeInstance();
    virtual  void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;
    IDetailLayoutBuilder* MyDetailLayout;

    TWeakObjectPtr<UDeadlineCloudJob> Settings;
  
public:
    
    void HandlePathChanged()
    {
        if (Settings.IsValid())
        {

            UE_LOG(LogTemp, Log, TEXT("Something changed!"));
        }
    }

    void OnButtonClicked();

protected:

private:
    

    //TSharedRef<SWidget> CreateNameWidget(FString Parameter);
    //TSharedRef<SWidget> CreatePathWidget(TSharedPtr<IPropertyHandle> ParameterHandle);
    //TSharedRef<SWidget> CreateStringWidget(FParameterDefinition *Parameter);

    void ForceRefreshDetails();
    bool CheckConsistency(UDeadlineCloudJob* Job);


    bool CheckConsidtensyPassed = true;
public:
	bool IsStepContainsErrors() const;
	EVisibility GetStepErrorWidgetVisibility() const;
	EVisibility GetStepDefaultWidgetVisibility() const;

	bool IsEnvironmentContainsErrors() const;
	EVisibility GetEnvironmentErrorWidgetVisibility() const;
	EVisibility GetEnvironmentDefaultWidgetVisibility() const;

    EVisibility GetWidgetVisibility() const
    {
        // if true, widget collapsed
        return (!CheckConsidtensyPassed) ? EVisibility::Visible : EVisibility::Collapsed;
    }
};

