// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#include "DeadlineCloudJobSettings/DeadlineCloudStepOverrideCustomization.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"
#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "DeadlineCloudJobSettings/DeadlineCloudEnvironmentOverrideCustomization.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "DetailWidgetRow.h"
#include "IDetailChildrenBuilder.h"
#include "DetailLayoutBuilder.h"
#include "IDetailGroup.h"
#include "PropertyCustomizationHelpers.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Misc/EngineVersionComparison.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "Framework/MetaData/DriverMetaData.h"
#include "PropertyEditorModule.h"
#include "Framework/MetaData/DriverMetaData.h"

#define LOCTEXT_NAMESPACE "UnrealDeadlineCloudServiceModule"

TSharedRef<IPropertyTypeCustomization> FDeadlineCloudStepOverrideCustomization::MakeInstance()
{
    return MakeShareable(new FDeadlineCloudStepOverrideCustomization);
}

void FDeadlineCloudStepOverrideCustomization::CustomizeHeader(
    TSharedRef<IPropertyHandle> StructPropertyHandle,
    FDetailWidgetRow& HeaderRow,
    IPropertyTypeCustomizationUtils& StructCustomizationUtils)
{
    // Get the Name property handle from the step
    TSharedPtr<IPropertyHandle> NameHandle = StructPropertyHandle->GetChildHandle(GET_MEMBER_NAME_CHECKED(FDeadlineCloudStepOverride, Name));
    
    if (NameHandle.IsValid())
    {
        FString StepName;
        NameHandle->GetValue(StepName);
        
        TSharedRef<SWidget> CustomNameWidget = SNew(STextBlock)
            .Text(FText::FromString(FString::Printf(TEXT("Step: %s"), *StepName)))
            .Font(IDetailLayoutBuilder::GetDetailFont());

        FName Tag = FName("MRQStepHeader." + StepName);
		CustomNameWidget->AddMetadata(FDriverMetaData::Id(Tag));

        HeaderRow.NameContent()
        [
			CustomNameWidget
        ];
    }
    else
    {
        HeaderRow.NameContent()
        [
            SNew(STextBlock)
            .Text(FText::FromString(TEXT("Step")))
            .Font(IDetailLayoutBuilder::GetDetailFont())
        ];
    }
    FUIAction EmptyCopyPasteAction = FUIAction(
        FExecuteAction::CreateLambda([]() {}),
        FCanExecuteAction::CreateLambda([]() { return false; }));

	HeaderRow.CopyAction(EmptyCopyPasteAction);
	HeaderRow.PasteAction(EmptyCopyPasteAction);
}

void FDeadlineCloudStepOverrideCustomization::CustomizeChildren(
    TSharedRef<IPropertyHandle> StructPropertyHandle,
    IDetailChildrenBuilder& StructBuilder,
    IPropertyTypeCustomizationUtils& StructCustomizationUtils)
{
    uint32 NumChildren;
    StructPropertyHandle->GetNumChildren(NumChildren);

    for (uint32 ChildIndex = 0; ChildIndex < NumChildren; ++ChildIndex)
    {
        TSharedRef<IPropertyHandle> ChildHandle = StructPropertyHandle->GetChildHandle(ChildIndex).ToSharedRef();
        FString PropertyName = ChildHandle->GetProperty()->GetName();
        if (PropertyName == "Name")
        {
            continue;
        }
        if (PropertyName == "DependsOn")
        {
            continue;
        }

        else if (PropertyName == "EnvironmentsOverrides")
        {
            auto EnvHandle = StructPropertyHandle->GetChildHandle(GET_MEMBER_NAME_CHECKED(FDeadlineCloudStepOverride, EnvironmentsOverrides))->AsArray();
            uint32 NumEnvs = 0;
            if (EnvHandle.IsValid())
            {
                EnvHandle->GetNumElements(NumEnvs);
                if (NumEnvs > 0)
                {
                    // Use custom array builder to hide the header for inner EnvironmentsOverrides
                    TSharedRef<FDeadlineCloudEnvOverrideArrayBuilder> InnerEnvsArrayBuilder = 
                        FDeadlineCloudEnvOverrideArrayBuilder::MakeInstance(ChildHandle);
                    
                    StructBuilder.AddCustomBuilder(InnerEnvsArrayBuilder);
                }
            }
        }
        else  StructBuilder.AddProperty(ChildHandle);
    }
}

//FDeadlineCloudStepOverrideArrayBuilder 
TSharedRef<FDeadlineCloudStepOverrideArrayBuilder> FDeadlineCloudStepOverrideArrayBuilder::MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle)
{
    TSharedRef<FDeadlineCloudStepOverrideArrayBuilder> Builder =
        MakeShared<FDeadlineCloudStepOverrideArrayBuilder>(InPropertyHandle);

    Builder->OnGenerateArrayElementWidget(
        FOnGenerateArrayElementWidget::CreateSP(Builder, &FDeadlineCloudStepOverrideArrayBuilder::OnGenerateEntry));
    return Builder;
}

FDeadlineCloudStepOverrideArrayBuilder::FDeadlineCloudStepOverrideArrayBuilder(TSharedRef<IPropertyHandle> InPropertyHandle)
    : FDetailArrayBuilder(InPropertyHandle, false, false, false),
    ArrayProperty(InPropertyHandle->AsArray()),
    PropertyHandle(InPropertyHandle)
{
    // Initialize PropertyOverrideHandler
    UMoviePipelineDeadlineCloudExecutorJob* OuterJob = FPropertyAvailabilityHandler::GetOuterJob(InPropertyHandle);
    PropertyOverrideHandler = MakeShared<FPropertyAvailabilityHandler>(OuterJob);
}

void FDeadlineCloudStepOverrideArrayBuilder::GenerateHeaderRowContent(FDetailWidgetRow& NodeRow)
{
    // Empty implementation to hide the array header
}

void FDeadlineCloudStepOverrideArrayBuilder::GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent)
{
    // Empty implementation to hide the wrapper struct header
}

void FDeadlineCloudStepOverrideArrayBuilder::OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32, IDetailChildrenBuilder& ChildrenBuilder) const
{
    IDetailPropertyRow& PropertyRow = ChildrenBuilder.AddProperty(ElementProperty);
    PropertyRow.ShowPropertyButtons(false);

    // Hide the reset to default button since it provides little value
    const FResetToDefaultOverride ResetDefaultOverride =
        FResetToDefaultOverride::Create(TAttribute<bool>(false));

    PropertyRow.OverrideResetToDefault(ResetDefaultOverride);
}



#undef LOCTEXT_NAMESPACE