// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudJobDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "PropertyEditorModule.h"
#include "Modules/ModuleManager.h"
#include "DetailLayoutBuilder.h"
#include "DetailWidgetRow.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/SBoxPanel.h"
#include "DesktopPlatformModule.h"
#include "EditorDirectories.h"
#include "Widgets/Input/SFilePathPicker.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "UnrealDeadlineCloudServiceModule.h"
#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"
#include "Templates/SharedPointer.h"
#include "PropertyEditorModule.h"
#include "IDetailsView.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"
#include "IDetailChildrenBuilder.h"
#include "Misc/MessageDialog.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"

#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"

#define LOCTEXT_NAMESPACE "JobDetails"



/*Details*/
TSharedRef<IDetailCustomization> FDeadlineCloudJobDetails::MakeInstance()
{
    return MakeShareable(new FDeadlineCloudJobDetails);
}

void FDeadlineCloudJobDetails::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
    // The detail layout builder that is using us
    MyDetailLayout = &DetailBuilder;

    TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
    MyDetailLayout->GetObjectsBeingCustomized(ObjectsBeingCustomized);
    Settings = Cast<UDeadlineCloudJob>(ObjectsBeingCustomized[0].Get());

    TSharedPtr<FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget> ConsistencyUpdateWidget;
    FParametersConsistencyCheckResult result;

    /* Consistency check */
    if (Settings.IsValid() && Settings->GetJobParameters().Num() > 0)
    {
        UDeadlineCloudJob* MyObject = Settings.Get();
        bCheckConsistensyPassed = CheckConsistency(MyObject);
    }

    TSharedRef<IPropertyHandle> StepsHandle = MyDetailLayout->GetProperty("Steps");
    IDetailPropertyRow* StepsRow = MyDetailLayout->EditDefaultProperty(StepsHandle);
    TSharedPtr<SWidget> OutNameWidget;
    TSharedPtr<SWidget> OutValueWidget;
    StepsRow->GetDefaultWidgets(OutNameWidget, OutValueWidget);
    StepsRow->ShowPropertyButtons(true);

    StepsRow->CustomWidget(true)
        .NameContent()
        [
            OutNameWidget.ToSharedRef()
        ]
        .ValueContent()
        [
            SNew(SHorizontalBox)
                + SHorizontalBox::Slot()
                .HAlign(HAlign_Left)
                .VAlign(VAlign_Center)
                [
                    SNew(STextBlock)
                        .Text(LOCTEXT("StepsError", "Contains empty or duplicate items"))
                        .Font(IDetailLayoutBuilder::GetDetailFont())
                        .ColorAndOpacity(FLinearColor::Red)
                        .Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudJobDetails::GetStepErrorWidgetVisibility)))
                ]
                + SHorizontalBox::Slot()
                .HAlign(HAlign_Left)
                .VAlign(VAlign_Center)
                [
                    SNew(SOverlay)
                        .Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudJobDetails::GetStepDefaultWidgetVisibility)))
                        + SOverlay::Slot()
                        [
                            OutValueWidget.ToSharedRef()
                        ]
                ]

        ];

    TSharedRef<IPropertyHandle> EnvironmentsHandle = MyDetailLayout->GetProperty("Environments");
    IDetailPropertyRow* EnvironmentsRow = MyDetailLayout->EditDefaultProperty(EnvironmentsHandle);
    TSharedPtr<SWidget> OutNameWidgetEnv;
    TSharedPtr<SWidget> OutValueWidgetEnv;
    EnvironmentsRow->GetDefaultWidgets(OutNameWidgetEnv, OutValueWidgetEnv);
    EnvironmentsRow->ShowPropertyButtons(true);

    EnvironmentsRow->CustomWidget(true)
        .NameContent()
        [
            OutNameWidgetEnv.ToSharedRef()
        ]
        .ValueContent()
        [
            SNew(SHorizontalBox)
                + SHorizontalBox::Slot()
                .HAlign(HAlign_Left)
                .VAlign(VAlign_Center)
                [
                    SNew(STextBlock)
                        .Text(LOCTEXT("EnvironmentsError", "Contains empty or duplicate items"))
                        .Font(IDetailLayoutBuilder::GetDetailFont())
                        .ColorAndOpacity(FLinearColor::Red)
                        .Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudJobDetails::GetEnvironmentErrorWidgetVisibility)))
                ]
                + SHorizontalBox::Slot()
                .HAlign(HAlign_Left)
                .VAlign(VAlign_Center)
                [
                    SNew(SOverlay)
                        .Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudJobDetails::GetEnvironmentDefaultWidgetVisibility)))
                        + SOverlay::Slot()
                        [
                            OutValueWidgetEnv.ToSharedRef()
                        ]
                ]
        ];

    IDetailCategoryBuilder& PropertiesCategory = MyDetailLayout->EditCategory("Parameters");

    PropertiesCategory.AddCustomRow(FText::FromString("Consistency"))
        .Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudJobDetails::GetConsistencyWidgetVisibility)))
        .WholeRowContent()
        [
            SAssignNew(ConsistencyUpdateWidget, FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget)
                .OnFixButtonClicked(FSimpleDelegate::CreateSP(this, &FDeadlineCloudJobDetails::OnButtonClicked))
        ];

    //  Dispatcher handle bind
    if (Settings.IsValid() && (MyDetailLayout != nullptr))
    {
        Settings->OnSomethingChanged = FSimpleDelegate::CreateSP(this, &FDeadlineCloudJobDetails::ForceRefreshDetails);
    };
}
void FDeadlineCloudJobDetails::ForceRefreshDetails()
{
    MyDetailLayout->ForceRefreshDetails();
}

bool FDeadlineCloudJobDetails::CheckConsistency(UDeadlineCloudJob* Job)
{
    FParametersConsistencyCheckResult result;
    result = Job->CheckJobParametersConsistency(Job);

    UE_LOG(LogTemp, Warning, TEXT("Check consistency result: %s"), *result.Reason);
    return result.Passed;
}

EVisibility FDeadlineCloudJobDetails::GetConsistencyWidgetVisibility() const
{
    return (!bCheckConsistensyPassed) ? EVisibility::Visible : EVisibility::Collapsed;
}

bool FDeadlineCloudJobDetails::IsStepContainsErrors() const
{
    TArray<UObject*> ExistingSteps;
    for (auto Step : Settings->Steps)
    {
        if (!IsValid(Step) || ExistingSteps.Contains(Step))
        {
            return true;
        }

        ExistingSteps.Add(Step);
    }

    return false;
}

EVisibility FDeadlineCloudJobDetails::GetStepErrorWidgetVisibility() const
{
    return IsStepContainsErrors() ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility FDeadlineCloudJobDetails::GetStepDefaultWidgetVisibility() const
{
    return IsStepContainsErrors() ? EVisibility::Collapsed : EVisibility::Visible;
}

bool FDeadlineCloudJobDetails::IsEnvironmentContainsErrors() const
{
    TArray<UObject*> ExistingEnvironment;
    for (auto Environment : Settings->Environments)
    {
        if (!IsValid(Environment) || ExistingEnvironment.Contains(Environment))
        {
            return true;
        }

        ExistingEnvironment.Add(Environment);
    }

    return false;
}

EVisibility FDeadlineCloudJobDetails::GetEnvironmentErrorWidgetVisibility() const
{
    return IsEnvironmentContainsErrors() ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility FDeadlineCloudJobDetails::GetEnvironmentDefaultWidgetVisibility() const
{
    return IsEnvironmentContainsErrors() ? EVisibility::Collapsed : EVisibility::Visible;
}

void FDeadlineCloudJobDetails::OnButtonClicked()
{
    Settings->FixJobParametersConsistency(Settings.Get());
    UE_LOG(LogTemp, Warning, TEXT("FixJobParametersConsistency"));
    ForceRefreshDetails();
}

TSharedRef<FDeadlineCloudJobParametersArrayBuilder> FDeadlineCloudJobParametersArrayBuilder::MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle)
{
    TSharedRef<FDeadlineCloudJobParametersArrayBuilder> Builder =
        MakeShared<FDeadlineCloudJobParametersArrayBuilder>(InPropertyHandle);

    Builder->OnGenerateArrayElementWidget(
        FOnGenerateArrayElementWidget::CreateSP(Builder, &FDeadlineCloudJobParametersArrayBuilder::OnGenerateEntry));
    return Builder;
}

FDeadlineCloudJobParametersArrayBuilder::FDeadlineCloudJobParametersArrayBuilder(TSharedRef<IPropertyHandle> InPropertyHandle)
    : FDetailArrayBuilder(InPropertyHandle, false, false, true),
    ArrayProperty(InPropertyHandle->AsArray()),
    BaseProperty(InPropertyHandle)
{
}

void FDeadlineCloudJobParametersArrayBuilder::GenerateHeaderRowContent(FDetailWidgetRow& NodeRow)
{
}

void FDeadlineCloudJobParametersArrayBuilder::GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent)
{
    FDetailArrayBuilder::GenerateHeaderRowContent(NodeRow);

    EmptyCopyPasteAction = FUIAction(
        FExecuteAction::CreateLambda([]() {}),
        FCanExecuteAction::CreateLambda([]() { return false; })
    );

    NodeRow.CopyAction(EmptyCopyPasteAction);
    NodeRow.PasteAction(EmptyCopyPasteAction);

    const FResetToDefaultOverride ResetDefaultOverride = FResetToDefaultOverride::Create(TAttribute<bool>(false));
    NodeRow.OverrideResetToDefault(ResetDefaultOverride);


    NodeRow.ValueContent()
        .HAlign(HAlign_Left)
        .VAlign(VAlign_Center)
        .MinDesiredWidth(170.f)
        .MaxDesiredWidth(170.f);

    NodeRow.NameContent()
        [
            NameContent
        ];

    NodeRow.IsEnabled(TAttribute<bool>::CreateLambda([this]()
        {
            if (OnIsEnabled.IsBound())
                return OnIsEnabled.Execute();
            return true;
        })
    );
}

UDeadlineCloudJob* FDeadlineCloudJobParametersArrayBuilder::GetOuterJob(TSharedRef<IPropertyHandle> Handle)
{
    TArray<UObject*> OuterObjects;
    Handle->GetOuterObjects(OuterObjects);

    if (OuterObjects.Num() == 0)
    {
        return nullptr;
    }

    const TWeakObjectPtr<UObject> OuterObject = OuterObjects[0];
    if (!OuterObject.IsValid())
    {
        return nullptr;
    }
    UDeadlineCloudJob* OuterJob = Cast<UDeadlineCloudJob>(OuterObject);
    return OuterJob;
}

bool FDeadlineCloudJobParametersArrayBuilder::IsResetToDefaultVisible(TSharedPtr<IPropertyHandle> PropertyHandle, FString InParameterName) const
{
	if (!PropertyHandle.IsValid())
	{
		return false;
	}

	auto OuterJob = GetOuterJob(PropertyHandle.ToSharedRef());

	if (!IsValid(OuterJob))
	{
		return false;
	}

	FString DefaultValue = OuterJob->GetDefaultParameterValue(InParameterName);
	FString CurrentValue;
	PropertyHandle->GetValue(CurrentValue);

	return !CurrentValue.Equals(DefaultValue);
}

void FDeadlineCloudJobParametersArrayBuilder::ResetToDefaultHandler(TSharedPtr<IPropertyHandle> PropertyHandle, FString InParameterName) const
{
	if (!PropertyHandle.IsValid())
	{
		return;
	}

	auto OuterJob = GetOuterJob(PropertyHandle.ToSharedRef());

	if (!IsValid(OuterJob))
	{
		return;
	}

	FString DefaultValue = OuterJob->GetDefaultParameterValue(InParameterName);
	PropertyHandle->SetValue(DefaultValue);
}

void FDeadlineCloudJobParametersArrayBuilder::OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32 ElementIndex, IDetailChildrenBuilder& ChildrenBuilder) const
{
    const TSharedPtr<IPropertyHandle> TypeHandle = ElementProperty->GetChildHandle("Type", false);

    if (!TypeHandle.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("FDeadlineCloudJobParametersArrayBuilder Type handle is not valid"));
        return;
    }

    uint8 TypeValue;
    TypeHandle->GetValue(TypeValue);

    auto Type = (EValueType)TypeValue;


    const TSharedPtr<IPropertyHandle> NameHandle = ElementProperty->GetChildHandle("Name", false);
    if (!NameHandle.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("FDeadlineCloudStepParametersArrayBuilder Name handle is not valid"));
        return;
    }

    FString ParameterName;
    NameHandle->GetValue(ParameterName);

    const TSharedPtr<IPropertyHandle> ValueHandle = ElementProperty->GetChildHandle("Value", false);
    if (!NameHandle.IsValid())
    {
        UE_LOG(LogTemp, Error, TEXT("FDeadlineCloudStepParametersArrayBuilder Name handle is not valid"));
        return;
    }

    IDetailPropertyRow& PropertyRow = ChildrenBuilder.AddProperty(ValueHandle.ToSharedRef());

    auto OuterJob = GetOuterJob(ElementProperty);
    if (IsValid(OuterJob))
    {
        const FResetToDefaultOverride ResetDefaultOverride = FResetToDefaultOverride::Create(
			FIsResetToDefaultVisible::CreateSP(this, &FDeadlineCloudJobParametersArrayBuilder::IsResetToDefaultVisible, ParameterName),
			FResetToDefaultHandler::CreateSP(this, &FDeadlineCloudJobParametersArrayBuilder::ResetToDefaultHandler, ParameterName)
		);
		PropertyRow.OverrideResetToDefault(ResetDefaultOverride);
    }
    else
    {
        // Hide the reset to default button since it provides little value
        const FResetToDefaultOverride ResetDefaultOverride = FResetToDefaultOverride::Create(TAttribute<bool>(false));
        PropertyRow.OverrideResetToDefault(ResetDefaultOverride);
    }

    PropertyRow.ShowPropertyButtons(true);

    TSharedPtr<SWidget> NameWidget;
    TSharedPtr<SWidget> ValueWidget;

    PropertyRow.GetDefaultWidgets(NameWidget, ValueWidget);
    ValueWidget = FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(ValueHandle, Type);

    PropertyRow.CustomWidget(true)
        .CopyAction(EmptyCopyPasteAction)
        .PasteAction(EmptyCopyPasteAction)
        .NameContent()
        .HAlign(HAlign_Fill)
        [
            SNew(SHorizontalBox)
                + SHorizontalBox::Slot()
                .Padding(FMargin(0.0f, 1.0f, 0.0f, 1.0f))
                .FillWidth(1)
                [
                    SNew(STextBlock)
                        .Text(FText::FromString(ParameterName))
                        .Font(IDetailLayoutBuilder::GetDetailFont())
                        .ColorAndOpacity(FSlateColor::UseForeground())
                ]
        ]
        .ValueContent()
        .HAlign(HAlign_Fill)
        [
            //FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(ValueHandle, Type)
            ValueWidget.ToSharedRef()
        ];

    ValueWidget->SetEnabled(
        TAttribute<bool>::CreateLambda([this, ParameterName]()
            {
                if (OnIsEnabled.IsBound())
                {
                        OnIsEnabled.Execute();
                }
                if (MrqJob)
                {
                    return ParameterName == "ExtraCmdArgs";
                }
                else
                {
                    return true;
                }
            })
    );

}

UMoviePipelineDeadlineCloudExecutorJob* FDeadlineCloudJobParametersArrayCustomization::GetMrqJob(TSharedRef<IPropertyHandle> Handle)
{
    TArray<UObject*> OuterObjects;
    Handle->GetOuterObjects(OuterObjects);

    if (OuterObjects.Num() == 0)
    {
        return nullptr;
    }

    const TWeakObjectPtr<UObject> OuterObject = OuterObjects[0];
    if (!OuterObject.IsValid())
    {
        return nullptr;
    }
    UMoviePipelineDeadlineCloudExecutorJob* MrqJob = Cast<UMoviePipelineDeadlineCloudExecutorJob>(OuterObject);
    return MrqJob;
}

void FDeadlineCloudJobParametersArrayCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
    TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Parameters", false);

    ArrayBuilder = FDeadlineCloudJobParametersArrayBuilder::MakeInstance(ArrayHandle.ToSharedRef());
    ArrayBuilder->GenerateWrapperStructHeaderRowContent(InHeaderRow, InPropertyHandle->CreatePropertyNameWidget());
}

void FDeadlineCloudJobParametersArrayCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> InPropertyHandle, IDetailChildrenBuilder& InChildBuilder, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
    
        ArrayBuilder->MrqJob = GetMrqJob(InPropertyHandle);
        InChildBuilder.AddCustomBuilder(ArrayBuilder.ToSharedRef());
}
#undef LOCTEXT_NAMESPACE