// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#include "DeadlineCloudJobSettings/DeadlineCloudEnvironmentOverrideCustomization.h"
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
#include "DeadlineCloudJobSettings/DeadlineCloudEnvironmentDetails.h"

#define LOCTEXT_NAMESPACE "UnrealDeadlineCloudServiceModule"

TSharedRef<IPropertyTypeCustomization> FDeadlineCloudEnvironmentOverrideCustomization::MakeInstance()
{
    return MakeShareable(new FDeadlineCloudEnvironmentOverrideCustomization);
}

void FDeadlineCloudEnvironmentOverrideCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
    // Check if the parent is a FDeadlineCloudStepOverride 
    TSharedPtr<IPropertyHandle> ParentHandle = InPropertyHandle->GetParentHandle();
    if (ParentHandle.IsValid())
    {
        FString ParentPropertyName = ParentHandle->GetProperty()->GetName();
        if (ParentPropertyName == TEXT("EnvironmentsOverrides"))
        {
            TSharedPtr<IPropertyHandle> StepParentHandle = ParentHandle->GetParentHandle();
            FString StepParentPropertyName = StepParentHandle->GetProperty()->GetName();
            if (StepParentHandle.IsValid() && (StepParentPropertyName == TEXT("StepsOverrides")))
            {
				AddDefaultEnvironmentOverrideHeaderRow(InPropertyHandle, InHeaderRow, "Step Environment: ", "MRQStepEnvHeader.");
            }
            else if (StepParentHandle.IsValid() && (StepParentPropertyName == TEXT("JobTemplateOverrides")))
            {
				AddDefaultEnvironmentOverrideHeaderRow(InPropertyHandle, InHeaderRow, "Environment: ", "MRQEnvHeader.");
            }
        }
    }

    FUIAction EmptyCopyPasteAction = FUIAction(
    FExecuteAction::CreateLambda([]() {}),
    FCanExecuteAction::CreateLambda([]() { return false; }));

	InHeaderRow.CopyAction(EmptyCopyPasteAction);
	InHeaderRow.PasteAction(EmptyCopyPasteAction);
}

void FDeadlineCloudEnvironmentOverrideCustomization::CustomizeChildren(
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
        
        // Hide the Name property
        if (PropertyName == TEXT("Name"))
        {
            continue;
        }
        
        // Handle Variables property to show variables instead of the header
        if (PropertyName == TEXT("Variables"))
        {
            // Get Variables map from the FDeadlineCloudEnvironmentVariablesMap struct
            TSharedPtr<IPropertyHandle> InnerVariablesHandle = ChildHandle->GetChildHandle("Variables");
            if (InnerVariablesHandle.IsValid())
            {
                //FDeadlineCloudEnvironmentParametersMapBuilder 
                TSharedRef<FDeadlineCloudEnvironmentParametersMapBuilder> VariablesMapBuilder = 
                    FDeadlineCloudEnvironmentParametersMapBuilder::MakeInstance(InnerVariablesHandle.ToSharedRef());
                StructBuilder.AddCustomBuilder(VariablesMapBuilder);
            }
            continue;
        }
        
        StructBuilder.AddProperty(ChildHandle).IsEnabled(true);
    }
}

void FDeadlineCloudEnvironmentOverrideCustomization::AddDefaultEnvironmentOverrideHeaderRow(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, const FString& TitlePrefix, const FString& TagPrefix)
{
    FString EnvironmentName;

    // Try to get the Name property value from the current property handle
    TSharedPtr<IPropertyHandle> NamePropertyHandle = InPropertyHandle->GetChildHandle("Name");
    if (NamePropertyHandle.IsValid())
    {
        FString NameValue;
        if (NamePropertyHandle->GetValue(NameValue) == FPropertyAccess::Success && !NameValue.IsEmpty())
        {
            EnvironmentName = NameValue;
        }
    }
    if (!EnvironmentName.IsEmpty())
    {
        FString CustomTitle = TitlePrefix + EnvironmentName;

        TSharedRef<SWidget> CustomNameWidget = SNew(STextBlock)
            .Text(FText::FromString(CustomTitle))
            .Font(IDetailLayoutBuilder::GetDetailFont());

        FName Tag = FName(TagPrefix + EnvironmentName);
		CustomNameWidget->AddMetadata(FDriverMetaData::Id(Tag));
        InHeaderRow.NameContent()
            [
                CustomNameWidget
            ];
    }
}

// FDeadlineCloudEnvOverrideArrayBuilder Implementation
TSharedRef<FDeadlineCloudEnvOverrideArrayBuilder> FDeadlineCloudEnvOverrideArrayBuilder::MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle)
{
    TSharedRef<FDeadlineCloudEnvOverrideArrayBuilder> Builder =
        MakeShared<FDeadlineCloudEnvOverrideArrayBuilder>(InPropertyHandle);

    Builder->OnGenerateArrayElementWidget(
        FOnGenerateArrayElementWidget::CreateSP(Builder, &FDeadlineCloudEnvOverrideArrayBuilder::OnGenerateEntry));
    return Builder;
}

FDeadlineCloudEnvOverrideArrayBuilder::FDeadlineCloudEnvOverrideArrayBuilder(TSharedRef<IPropertyHandle> InPropertyHandle)
    : FDetailArrayBuilder(InPropertyHandle, false, false, false),
    ArrayProperty(InPropertyHandle->AsArray()),
    PropertyHandle(InPropertyHandle)
{
}

void FDeadlineCloudEnvOverrideArrayBuilder::GenerateHeaderRowContent(FDetailWidgetRow& NodeRow)
{
    // Empty implementation to hide the array header
}

void FDeadlineCloudEnvOverrideArrayBuilder::GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent)
{
    // Empty implementation to hide the wrapper struct header
}

void FDeadlineCloudEnvOverrideArrayBuilder::OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32, IDetailChildrenBuilder& ChildrenBuilder) const
{
    IDetailPropertyRow& PropertyRow = ChildrenBuilder.AddProperty(ElementProperty);
    PropertyRow.ShowPropertyButtons(false);
    // Hide the reset to default button since it provides little value
    const FResetToDefaultOverride ResetDefaultOverride =
        FResetToDefaultOverride::Create(TAttribute<bool>(false));

    PropertyRow.OverrideResetToDefault(ResetDefaultOverride);
}

#undef LOCTEXT_NAMESPACE 