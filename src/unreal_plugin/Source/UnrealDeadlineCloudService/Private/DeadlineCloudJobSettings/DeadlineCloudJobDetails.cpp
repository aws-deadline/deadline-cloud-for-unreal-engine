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
#include "DeadlineCloudJobSettings/DeadlineCloudEnvironmentOverrideCustomization.h"
#include "Framework/MetaData/DriverMetaData.h"

#define LOCTEXT_NAMESPACE "JobDetails"



/*Details*/
TSharedRef<IDetailCustomization> FDeadlineCloudJobDetails::MakeInstance()
{
    return MakeShareable(new FDeadlineCloudJobDetails);
}

void FDeadlineCloudJobDetails::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
    // The detail layout builder that is using us
    MainDetailLayout = &DetailBuilder;

    TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
    MainDetailLayout->GetObjectsBeingCustomized(ObjectsBeingCustomized);
    Settings = Cast<UDeadlineCloudJob>(ObjectsBeingCustomized[0].Get());

    TSharedPtr<FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget> ConsistencyUpdateWidget;
    FParametersConsistencyCheckResult result;

    TSharedPtr<FDeadlineCloudDetailsWidgetsHelper::SEyeUpdateWidget> HiddenParametersUpdateWidget;

    /* Update all when one Parameters widget is checked as hidden */
    if (Settings.IsValid())
    {
        Settings->OnParameterHidden.BindSP(this, &FDeadlineCloudJobDetails::RespondToEvent);
    }
    /* Collapse hidden parameters array  */
    TSharedRef<IPropertyHandle> HideHandle = MainDetailLayout->GetProperty("HiddenParametersList");
    IDetailPropertyRow* HideRow = MainDetailLayout->EditDefaultProperty(HideHandle);
    HideRow->Visibility(EVisibility::Collapsed);


    /* Consistency check */
    if (Settings.IsValid() && Settings->GetJobParameters().Num() > 0)
    {
        UDeadlineCloudJob* MyObject = Settings.Get();
        bCheckConsistensyPassed = CheckConsistency(MyObject);
    }

    TSharedRef<IPropertyHandle> StepsHandle = MainDetailLayout->GetProperty("Steps");
    IDetailPropertyRow* StepsRow = MainDetailLayout->EditDefaultProperty(StepsHandle);
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

    TSharedRef<IPropertyHandle> EnvironmentsHandle = MainDetailLayout->GetProperty("Environments");
    IDetailPropertyRow* EnvironmentsRow = MainDetailLayout->EditDefaultProperty(EnvironmentsHandle);
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

   

    IDetailCategoryBuilder& PropertiesCategory = MainDetailLayout->EditCategory("Parameters");

    PropertiesCategory.AddCustomRow(FText::FromString("Consistency"))
        .Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudJobDetails::GetConsistencyWidgetVisibility)))
        .WholeRowContent()
        [
            SAssignNew(ConsistencyUpdateWidget, FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget)
                .OnFixButtonClicked(FSimpleDelegate::CreateSP(this, &FDeadlineCloudJobDetails::OnConsistencyButtonClicked))
        ];

    //  Dispatcher handle bind
    if (Settings.IsValid() && (MainDetailLayout != nullptr))
    {
        Settings->OnPathChanged = FSimpleDelegate::CreateSP(this, &FDeadlineCloudJobDetails::ForceRefreshDetails);
    };



    PropertiesCategory.AddCustomRow(FText::FromString("Visibility"))
        .Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudJobDetails::GetEyeWidgetVisibility)))
        .WholeRowContent()
        [
            SAssignNew(HiddenParametersUpdateWidget, FDeadlineCloudDetailsWidgetsHelper::SEyeUpdateWidget)

                .OnEyeUpdateButtonClicked(FSimpleDelegate::CreateSP(this, &FDeadlineCloudJobDetails::OnResetHiddenParametersClicked))
        ];

}
void FDeadlineCloudJobDetails::RespondToEvent()
{
    ForceRefreshDetails();
}
void FDeadlineCloudJobDetails::ForceRefreshDetails()
{
    MainDetailLayout->ForceRefreshDetails();
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

EVisibility FDeadlineCloudJobDetails::GetEyeWidgetVisibility() const
{
    return ((Settings->IsParametersHiddenByDefault())) ? EVisibility::Collapsed : EVisibility::Visible;
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

void FDeadlineCloudJobDetails::OnConsistencyButtonClicked()
{
    /* Compare hidden parameters after consistency check */
    if (bCheckConsistensyPassed == false)
    {
        /* Remove hidden parameters in TArray missing in .yaml */
        if (Settings->AreEmptyHiddenParameters() == false)
        {
            Settings->FixConsistencyForHiddenParameters();
        }

    }
    Settings->FixJobParametersConsistency(Settings.Get());
    UE_LOG(LogTemp, Warning, TEXT("FixJobParametersConsistency"));
    ForceRefreshDetails();
}

void FDeadlineCloudJobDetails::OnResetHiddenParametersClicked()
{
    Settings->ResetParametersHiddenToDefault();
    ForceRefreshDetails();
}

void FDeadlineCloudJobParametersArrayBuilder::OnEyeHideWidgetButtonClicked(FName Property) const
{

    if (Job)
    {
        if (Job->ContainsHiddenParameters(Property))
        {
            Job->RemoveHiddenParameters(Property);
        }
        else
        {
            Job->AddHiddenParameter(Property);
        }
    }
}

bool FDeadlineCloudJobParametersArrayBuilder::IsPropertyHidden(FName Parameter) const
{
    bool Contains = false;

    if (MrqJob)
    {
        if (MrqJob->JobPreset)
        {
            Contains = MrqJob->JobPreset->ContainsHiddenParameters(Parameter);
        }
    }
    return Contains;
}


void FDeadlineCloudJobParametersArrayBuilder::GenerateStepsExtraChildren(IDetailChildrenBuilder& ChildrenBuilder)
{
    TSharedPtr<IPropertyHandle> ParentStruct = BaseProperty->GetParentHandle();
    if (!ParentStruct || !ParentStruct->IsValidHandle())
        return;

    // Get HiddenParametersList from each StepOverride element
    TSharedPtr<IPropertyHandle> StepsHandle =
        ParentStruct->GetChildHandle(GET_MEMBER_NAME_CHECKED(FJobTemplateOverrides, StepsOverrides));
    if (StepsHandle && StepsHandle->IsValidHandle())
    {
        if ( MrqJob)
        {
            // Access the array property of StepOverride elements
            TArray<FDeadlineCloudStepOverride>& Steps = MrqJob->JobTemplateOverrides.StepsOverrides;

            for (FDeadlineCloudStepOverride& Step : Steps)
            {
                // Check Steps all > Steps hidden 
                if (Step.TaskParameterDefinitions.Parameters.Num() > Step.HiddenParametersList.Num())
                {
                    // Use custom array builder to hide the header
                    TSharedRef<FDeadlineCloudStepOverrideArrayBuilder> StepsArrayBuilder = 
                    FDeadlineCloudStepOverrideArrayBuilder::MakeInstance(StepsHandle.ToSharedRef());

                    ChildrenBuilder.AddCustomBuilder(StepsArrayBuilder);
                }
            }
        }
    }
}

void FDeadlineCloudJobParametersArrayBuilder::GenerateEnvironmentsExtraChildren(IDetailChildrenBuilder& ChildrenBuilder)
{
    TSharedPtr<IPropertyHandle> ParentStruct = BaseProperty->GetParentHandle();
    if (!ParentStruct || !ParentStruct->IsValidHandle())
        return;

    TSharedPtr<IPropertyHandle> EnvHandle =
        ParentStruct->GetChildHandle(GET_MEMBER_NAME_CHECKED(FJobTemplateOverrides, EnvironmentsOverrides));
    if (EnvHandle && EnvHandle->IsValidHandle())
    {
        if (MrqJob)
        {
            // Access the array property of StepOverride elements
            TArray<FDeadlineCloudEnvironmentOverride>& Envs = MrqJob->JobTemplateOverrides.EnvironmentsOverrides;

            for (FDeadlineCloudEnvironmentOverride& Environment : Envs)
            {
                // Check Steps all > Steps hidden 
                if (Environment.Variables.Variables.Num() > Environment.HiddenVarsList.Num())
                {
                    // Use custom array builder to hide the header
                    TSharedRef<FDeadlineCloudEnvOverrideArrayBuilder> EnvsArrayBuilder =
                        FDeadlineCloudEnvOverrideArrayBuilder::MakeInstance(EnvHandle.ToSharedRef());

                    ChildrenBuilder.AddCustomBuilder(EnvsArrayBuilder);
                }
            }
        }
    }
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
    
    TWeakPtr<FDeadlineCloudJobParametersArrayBuilder> LocalWeakThis = SharedThis(this);

    NodeRow.IsEnabled(TAttribute<bool>::CreateLambda([LocalWeakThis]()
        {
            if (auto Pinned = LocalWeakThis.Pin())
            {
                if (Pinned->OnIsEnabled.IsBound())
                    return Pinned->OnIsEnabled.Execute();
            }
            return true;
        }));
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


bool FDeadlineCloudJobParametersArrayBuilder::IsEyeWidgetEnabled(FName Parameter) const
{
    bool result = false;

    if (Job)
    {
        result = Job->ContainsHiddenParameters(Parameter);
    }

    if (MrqJob && MrqJob->JobPreset)
    {
        result = MrqJob->JobPreset->ContainsHiddenParameters(Parameter);
    }

    return result;
}

bool FDeadlineCloudJobParametersArrayBuilder::IsParameterVisibilityChangedFromDefault(FName Parameter) const
{
    if (!Job)
        return false;

    return Job->IsParameterVisibilityChangedFromDefault(Parameter);
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
    ValueWidget = FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(ValueHandle, Type, EValueValidationType::JobParameterValue);
	FName Tag = FName("JobParameter." + ParameterName);
	ValueWidget->AddMetadata(FDriverMetaData::Id(Tag));

    bool Checked = !(IsEyeWidgetEnabled(FName(ParameterName)));
    bool isChangedByUser = IsParameterVisibilityChangedFromDefault(FName(ParameterName));
    TSharedRef<FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox> EyeWidget = SNew(FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox, FName(ParameterName), Checked, isChangedByUser);

    EyeWidget->SetOnCheckStateChangedDelegate(FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox::FOnCheckStateChangedDelegate::CreateSP(this, &FDeadlineCloudJobParametersArrayBuilder::OnEyeHideWidgetButtonClicked));
    EyeWidget->SetVisibility((MrqJob) ? EVisibility::Hidden : EVisibility::Visible);

    PropertyRow.CustomWidget(true)
        .CopyAction(EmptyCopyPasteAction)
        .PasteAction(EmptyCopyPasteAction)
        .NameContent()
        .HAlign(HAlign_Fill)
        [
            SNew(SHorizontalBox)
                + SHorizontalBox::Slot()
                .AutoWidth()
                .Padding(4, 0)
                [
                    MrqJob
                        ? SNew(SCheckBox)
                        .IsChecked_Lambda([this, Tag]()
                            {
                                if (MrqJob)
                                {
                                    return MrqJob->IsPropertyRowEnabledInMovieRenderJob(Tag)
                                        ? ECheckBoxState::Checked
                                        : ECheckBoxState::Unchecked;
                                }
                                return ECheckBoxState::Unchecked;
                            })
                        .OnCheckStateChanged_Lambda([this, Tag](ECheckBoxState NewState)
                            {
                                if (MrqJob)
                                {
                                    const bool bEnabled = (NewState == ECheckBoxState::Checked);
                                    UE_LOG(LogTemp, Warning, TEXT("Setting Tag = %s, Enabled = %d"), *Tag.ToString(), bEnabled);
                                    MrqJob->SetPropertyRowEnabledInMovieRenderJob(Tag, bEnabled);
                                }
                            })
                        : SNullWidget::NullWidget
                ]
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
            ValueWidget.ToSharedRef()
        ]
        .ExtensionContent()
        [
            EyeWidget
        ];

    ValueWidget->SetEnabled(
        TAttribute<bool>::CreateLambda([this, Tag]()
            {
                if (MrqJob)
                {
                    return MrqJob->IsPropertyRowEnabledInMovieRenderJob(Tag);
                }
                
                if (OnIsEnabled.IsBound())
                    return OnIsEnabled.Execute();
                return true;
            })
    );

    PropertyRow.Visibility(IsPropertyHidden(FName(ParameterName)) ? EVisibility::Collapsed : EVisibility::Visible);
}



void FJobTemplateOverridesCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
    TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Parameters", false);

    ParametersArrayBuilder = FDeadlineCloudJobParametersArrayBuilder::MakeInstance(ArrayHandle.ToSharedRef());
    ParametersArrayBuilder->GenerateWrapperStructHeaderRowContent(InHeaderRow, InPropertyHandle->CreatePropertyNameWidget());

}

void FJobTemplateOverridesCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> InPropertyHandle, IDetailChildrenBuilder& InChildBuilder, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{

    //Parameters
    {
        TSharedPtr<IPropertyHandle> ParametersHandle =
            InPropertyHandle->GetChildHandle(GET_MEMBER_NAME_CHECKED(FJobTemplateOverrides, Parameters));

        if (ParametersHandle && ParametersHandle->IsValidHandle())
        {
             ParametersArrayBuilder =
                FDeadlineCloudJobParametersArrayBuilder::MakeInstance(ParametersHandle.ToSharedRef());

            ParametersArrayBuilder->MrqJob = FDeadlineCloudDetailsWidgetsHelper::GetMrqJob(InPropertyHandle);
            ParametersArrayBuilder->Job = GetJob(InPropertyHandle);

            InChildBuilder.AddCustomBuilder(ParametersArrayBuilder.ToSharedRef());
        }
    }

    //StepsOverrides only if array is not empty   
    {
        auto StepsHandle = InPropertyHandle->GetChildHandle(GET_MEMBER_NAME_CHECKED(FJobTemplateOverrides, StepsOverrides))->AsArray();
        uint32 NumSteps = 0;
        if (StepsHandle.IsValid())
        {
            StepsHandle->GetNumElements(NumSteps);
            if (NumSteps > 0)
                ParametersArrayBuilder->GenerateStepsExtraChildren(InChildBuilder);
        }
    }

    // Environments only if array is not empty  
    {
        auto EnvHandle = InPropertyHandle->GetChildHandle(GET_MEMBER_NAME_CHECKED(FJobTemplateOverrides, EnvironmentsOverrides))->AsArray();
        uint32 NumEnvs = 0;
        if (EnvHandle.IsValid())
        {
            EnvHandle->GetNumElements(NumEnvs);
            if (NumEnvs > 0)
                ParametersArrayBuilder->GenerateEnvironmentsExtraChildren(InChildBuilder);
        }
    }
}


UDeadlineCloudJob* FJobTemplateOverridesCustomization::GetJob(TSharedRef<IPropertyHandle> Handle)
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
    UDeadlineCloudJob* Job = Cast<UDeadlineCloudJob>(OuterObject);
    return Job;
}

UDeadlineCloudJob* FDeadlineCloudJobParametersArrayCustomization::GetJob(TSharedRef<IPropertyHandle> Handle)
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
    UDeadlineCloudJob* Job = Cast<UDeadlineCloudJob>(OuterObject);
    return Job;
}

void FDeadlineCloudJobParametersArrayCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
    TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Parameters", false);

    ArrayBuilder = FDeadlineCloudJobParametersArrayBuilder::MakeInstance(ArrayHandle.ToSharedRef());
    ArrayBuilder->GenerateWrapperStructHeaderRowContent(InHeaderRow, InPropertyHandle->CreatePropertyNameWidget());
}

void FDeadlineCloudJobParametersArrayCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> InPropertyHandle, IDetailChildrenBuilder& InChildBuilder, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{

    ArrayBuilder->MrqJob = FDeadlineCloudDetailsWidgetsHelper::GetMrqJob(InPropertyHandle);
    ArrayBuilder->Job = GetJob(InPropertyHandle);

    InChildBuilder.AddCustomBuilder(ArrayBuilder.ToSharedRef());
}
#undef LOCTEXT_NAMESPACE