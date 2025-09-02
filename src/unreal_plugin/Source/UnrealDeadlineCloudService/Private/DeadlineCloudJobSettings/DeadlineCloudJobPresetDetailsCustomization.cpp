// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "DetailWidgetRow.h"
#include "IDetailChildrenBuilder.h"
#include "DetailLayoutBuilder.h"
#include "IDetailGroup.h"
#include "PropertyCustomizationHelpers.h"
#include "Widgets/Input/SCheckBox.h"
#include "Misc/EngineVersionComparison.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "Framework/MetaData/DriverMetaData.h"
#include "PropertyEditorModule.h"
#include "DeadlineCloudJobSettings/DeadlineCloudStepOverrideCustomization.h"

#define LOCTEXT_NAMESPACE "UnrealDeadlineCloudServiceModule"

TSharedRef<IPropertyTypeCustomization> FDeadlineCloudJobPresetDetailsCustomization::MakeInstance()
{
    return MakeShared<FDeadlineCloudJobPresetDetailsCustomization>();
}

void FDeadlineCloudJobPresetDetailsCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> PropertyHandle, FDetailWidgetRow& HeaderRow,
    IPropertyTypeCustomizationUtils& CustomizationUtils)
{
}

void FDeadlineCloudJobPresetDetailsCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> StructHandle,
    IDetailChildrenBuilder& ChildBuilder, IPropertyTypeCustomizationUtils& CustomizationUtils)
{
    UMoviePipelineDeadlineCloudExecutorJob* OuterJob = FPropertyAvailabilityHandler::GetOuterJob(StructHandle);
    PropertyOverrideHandler = MakeShared<FPropertyAvailabilityHandler>(OuterJob);

    TMap<FName, IDetailGroup*> CreatedCategories;
    const FName StructName(StructHandle->GetProperty()->GetFName());

    if (OuterJob)
    {
        IDetailGroup& BaseCategoryGroup = ChildBuilder.AddGroup(StructName, StructHandle->GetPropertyDisplayName());
        CreatedCategories.Add(StructName, &BaseCategoryGroup);
    }

    // For each map member and each struct member in the map member value
    uint32 NumChildren;
    StructHandle->GetNumChildren(NumChildren);

    // For each struct member
    for (uint32 ChildIndex = 0; ChildIndex < NumChildren; ++ChildIndex)
    {
        const TSharedRef<IPropertyHandle> ChildHandle = StructHandle->GetChildHandle(ChildIndex).ToSharedRef();

        // Skip properties that are hidden so we don't end up creating empty categories in the job details
        if (OuterJob && IsPropertyHiddenInMovieRenderQueue(*ChildHandle->GetProperty()->GetPathName()))
        {
            continue;
        }

        IDetailGroup* GroupToUse = nullptr;
        if (const FString* PropertyCategoryString = ChildHandle->GetProperty()->FindMetaData(TEXT("Category")))
        {
            FName PropertyCategoryName(*PropertyCategoryString);

            if (IDetailGroup** FoundCategory = CreatedCategories.Find(PropertyCategoryName))
            {
                GroupToUse = *FoundCategory;
            }
            else
            {
                if (OuterJob)
                {
                    GroupToUse = CreatedCategories.FindChecked(StructName);
                }
                else
                {
                    IDetailGroup& NewGroup = ChildBuilder.AddGroup(StructName, StructHandle->GetPropertyDisplayName());
                    NewGroup.ToggleExpansion(true);
                    GroupToUse = CreatedCategories.Add(PropertyCategoryName, &NewGroup);
                }
            }
        }

        IDetailPropertyRow& PropertyRow = GroupToUse->AddPropertyRow(ChildHandle);

        TSharedPtr<SWidget> CustomValueWidget = FDeadlineCloudDetailsWidgetsHelper::TryCreatePropertyWidgetFromMetadata(ChildHandle);
        if (CustomValueWidget.IsValid())
        {
            FString ParameterName = ChildHandle->GetProperty()->GetName();
            FName Tag = FName("JobPreset." + ParameterName);
            CustomValueWidget->AddMetadata(FDriverMetaData::Id(Tag));
        }

        if (OuterJob)
        {
            CustomizeStructChildrenInMovieRenderQueue(PropertyRow, OuterJob, CustomValueWidget);
        }
        else
        {
            CustomizeStructChildrenInAssetDetails(PropertyRow, CustomValueWidget);
        }
    }

    // Force expansion of all categories
    for (const TTuple<FName, IDetailGroup*>& Pair : CreatedCategories)
    {
        if (Pair.Value)
        {
            Pair.Value->ToggleExpansion(true);
        }
    }
}

void FDeadlineCloudJobPresetDetailsCustomization::CustomizeStructChildrenInAssetDetails(
    IDetailPropertyRow& PropertyRow, TSharedPtr<SWidget> CustomValueWidget) const
{
    TSharedPtr<SWidget> NameWidget;
    TSharedPtr<SWidget> ValueWidget;
    FDetailWidgetRow Row;
    PropertyRow.GetDefaultWidgets(NameWidget, ValueWidget, Row);

    PropertyRow.CustomWidget(true)
        .NameContent()
        .MinDesiredWidth(Row.NameWidget.MinWidth)
        .MaxDesiredWidth(Row.NameWidget.MaxWidth)
        .HAlign(HAlign_Fill)
        [
            NameWidget.ToSharedRef()
        ]
        .ValueContent()
        .MinDesiredWidth(Row.ValueWidget.MinWidth)
        .MaxDesiredWidth(Row.ValueWidget.MaxWidth)
        .VAlign(VAlign_Center)
        [
            CustomValueWidget.IsValid() ? CustomValueWidget.ToSharedRef() : ValueWidget.ToSharedRef()
        ];
}

void FDeadlineCloudJobPresetDetailsCustomization::CustomizeStructChildrenInMovieRenderQueue(
    IDetailPropertyRow& PropertyRow, UMoviePipelineDeadlineCloudExecutorJob* Job, TSharedPtr<SWidget> CustomValueWidget) const
{
    PropertyOverrideHandler->EnableInMovieRenderQueue(PropertyRow, CustomValueWidget);
}

TSharedRef<IPropertyTypeCustomization> FDeadlineCloudAttachmentDetailsCustomization::MakeInstance()
{
    return MakeShared<FDeadlineCloudAttachmentDetailsCustomization>();
}

void FDeadlineCloudAttachmentDetailsCustomization::CustomizeHeader(
    TSharedRef<IPropertyHandle> PropertyHandle, FDetailWidgetRow& HeaderRow,
    IPropertyTypeCustomizationUtils& CustomizationUtils)
{
    const auto NameWidget = PropertyHandle->CreatePropertyNameWidget();
    const auto ValueWidget = PropertyHandle->CreatePropertyValueWidget();

    HeaderRow
        .NameContent()
        [
            NameWidget
        ]
        .ValueContent()
        [
            ValueWidget
        ];
}

TSharedRef<SWidget> FDeadlineCloudAttachmentDetailsCustomization::BuildPathsValidationWidget(
    TSharedRef<IPropertyHandle> PathsHandle)
{
    return SNew(SVerticalBox)

        // Empty paths
        + SVerticalBox::Slot()
        .AutoHeight()
        [
            SNew(STextBlock)
                .Text(LOCTEXT("EmptyPathsError", "The list contains empty elements"))
                .Font(IDetailLayoutBuilder::GetDetailFont())
                .ColorAndOpacity(FLinearColor(1.0f, 0.756f, 0.027f)) // #FFC107
                .Visibility_Lambda([PathsHandle, this]() {
                return GetPathsEmptyWidgetVisibility(PathsHandle);
                    })
        ]

    // Too many paths
    + SVerticalBox::Slot()
        .AutoHeight()
        [
            SNew(STextBlock)
                .Text(LOCTEXT("ExceedPathsNumberError", "The list must not contain more than 50 paths"))
                .Font(IDetailLayoutBuilder::GetDetailFont())
                .ColorAndOpacity(FLinearColor(1.0f, 0.756f, 0.027f))
                .Visibility_Lambda([PathsHandle, this]() {
                return GetPathsNumberExceededWidgetVisibility(PathsHandle);
                    })
        ];
}

void FDeadlineCloudAttachmentDetailsCustomization::CustomizePathsRow(
    IDetailPropertyRow& Row,
    TSharedRef<IPropertyHandle> PathsHandle,
    bool bCheckPaths)
{
    TSharedPtr<SWidget> NameWidget;
    TSharedPtr<SWidget> ValueWidget;
    Row.GetDefaultWidgets(NameWidget, ValueWidget);

    Row.CustomWidget(true)
        .NameContent()
        [
            NameWidget.ToSharedRef()
        ]
        .ValueContent()
        [
            SNew(SHorizontalBox)
                // Only add the validation widget if bCheckPaths is true
                + SHorizontalBox::Slot()
                .HAlign(HAlign_Left)
                .VAlign(VAlign_Center)
                .Padding(4, 0)
                [
                    bCheckPaths ? BuildPathsValidationWidget(PathsHandle) : SNullWidget::NullWidget
                ]
                + SHorizontalBox::Slot()
                .AutoWidth()
                .HAlign(HAlign_Left)
                .VAlign(VAlign_Center)
                [
                    SNew(SOverlay)
                        + SOverlay::Slot()
                        [
                            ValueWidget.ToSharedRef()
                        ]
                ]
        ];
}

void FDeadlineCloudAttachmentDetailsCustomization::CustomizeChildren(
    TSharedRef<IPropertyHandle> StructHandle, IDetailChildrenBuilder& ChildBuilder,
    IPropertyTypeCustomizationUtils& CustomizationUtils)
{
    auto ShowAutoDetectedHandle = StructHandle->GetChildHandle(0);
    const auto PathsHandle = StructHandle->GetChildHandle(1);
    const auto AutoDetectedPathsHandle = StructHandle->GetChildHandle(2);

    // Show autodetect
    auto& ShowAutoDetectedRow = ChildBuilder.AddProperty(ShowAutoDetectedHandle.ToSharedRef());
    auto& PathsRow = ChildBuilder.AddProperty(PathsHandle.ToSharedRef());
    auto& AutoDetectedPathsRow = ChildBuilder.AddProperty(AutoDetectedPathsHandle.ToSharedRef());

    UMoviePipelineDeadlineCloudExecutorJob* OuterJob = FPropertyAvailabilityHandler::GetOuterJob(StructHandle);
    PropertyOverrideHandler = MakeShared<FPropertyAvailabilityHandler>(OuterJob);

    if (OuterJob)
    {
        PropertyOverrideHandler->EnableInMovieRenderQueue(PathsRow);
        AutoDetectedPathsRow
            .Visibility(
                TAttribute<EVisibility>::Create([ShowAutoDetectedHandle]
                    {
                        bool bVisible = false;
                        ShowAutoDetectedHandle->GetValue(bVisible);
                        return bVisible
                            ? EVisibility::Visible
                            : EVisibility::Hidden;
                    }));
    }
    else
    { 
        PropertyOverrideHandler->DisableRowInDataAsset(AutoDetectedPathsRow);
    }
        CustomizePathsRow(PathsRow, PathsHandle.ToSharedRef(), true);
        CustomizePathsRow(AutoDetectedPathsRow, AutoDetectedPathsHandle.ToSharedRef(), false);

    // Since we updating auto-detected files mostly to show them in the UI. We don't want to put it into job initialization methods
    if (OuterJob && StructHandle->GetProperty()->GetName() == "InputFiles")
    {
        OuterJob->UpdateAttachmentFields();
    }
}

bool FDeadlineCloudAttachmentDetailsCustomization::ExceededPathsNumber(TSharedPtr<IPropertyHandle> PropertyHandle) const
{
	if (!PropertyHandle.IsValid())
	{
		return false;
	}
	auto Paths = PropertyHandle->GetChildHandle("Paths", false);
	if (!Paths.IsValid())
	{
		return false;
	}

	auto ArrayHandle = Paths->AsArray();
	if (!ArrayHandle.IsValid())
	{
		return false;
	}

	uint32 NumChildren = 0;
	ArrayHandle->GetNumElements(NumChildren);
    if (NumChildren >= 50)
    {
        return true;
    }

    return false;
}

bool FDeadlineCloudAttachmentDetailsCustomization::ContainsEmptyPaths(TSharedPtr<IPropertyHandle> PropertyHandle) const
{
    if (!PropertyHandle.IsValid())
    {
        return false;
    }
    auto Paths = PropertyHandle->GetChildHandle("Paths", false);
    if (!Paths.IsValid())
    {
        return false;
    }

    auto ArrayHandle = Paths->AsArray();
    if (!ArrayHandle.IsValid())
    {
        return false;
    }

    uint32 NumChildren = 0;
    ArrayHandle->GetNumElements(NumChildren);
    if (NumChildren == 0)
    {
        return false;
    }
    for (uint32 ChildIndex = 0; ChildIndex < NumChildren; ++ChildIndex)
    {
        TSharedPtr<IPropertyHandle> ChildHandle = ArrayHandle->GetElement(ChildIndex);
        if (!ChildHandle.IsValid())
        {
            continue;
        }

        FString Value;
        auto FilePath = ChildHandle->GetChildHandle("FilePath", false);
        if (FilePath.IsValid())
        {
            FilePath->GetValue(Value);
        }
        else
        {
            auto Path = ChildHandle->GetChildHandle("Path", false);
            if (Path.IsValid())
            {
                Path->GetValue(Value);
            }
        }

        if (Value.IsEmpty())
        {
            return true;
        }
    }

    return false;
}

EVisibility FDeadlineCloudAttachmentDetailsCustomization::GetPathsNumberExceededWidgetVisibility(TSharedPtr<IPropertyHandle> PropertyHandle) const
{
    return ExceededPathsNumber(PropertyHandle) ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility FDeadlineCloudAttachmentDetailsCustomization::GetPathsEmptyWidgetVisibility(TSharedPtr<IPropertyHandle> PropertyHandle) const
{
    return ContainsEmptyPaths(PropertyHandle) ? EVisibility::Visible : EVisibility::Collapsed;
}



bool FDeadlineCloudJobPresetDetailsCustomization::IsPropertyHiddenInMovieRenderQueue(const FName& InPropertyPath)
{
    return false;
}

bool GetPresetValueAsString(const FProperty* PropertyPtr, UMoviePipelineDeadlineCloudExecutorJob* Job, FString& OutFormattedValue)
{
    if (!PropertyPtr || !Job)
    {
        return false;
    }

    UDeadlineCloudJob* SelectedJobPreset = Job->JobPreset;
    if (!SelectedJobPreset)
    {
        return false;
    }

    const void* ValuePtr = PropertyPtr->ContainerPtrToValuePtr<void>(&SelectedJobPreset->JobPresetStruct);
    PropertyPtr->ExportText_Direct(OutFormattedValue, ValuePtr, ValuePtr, nullptr, PPF_None);
    return true;
}

TSharedRef<FDeadlineCloudAttachmentArrayBuilder> FDeadlineCloudAttachmentArrayBuilder::MakeInstance(
    TSharedRef<IPropertyHandle> InPropertyHandle
)
{
    TSharedRef<FDeadlineCloudAttachmentArrayBuilder> Builder =
        MakeShared<FDeadlineCloudAttachmentArrayBuilder>(InPropertyHandle);

    Builder->OnGenerateArrayElementWidget(
        FOnGenerateArrayElementWidget::CreateSP(Builder, &FDeadlineCloudAttachmentArrayBuilder::OnGenerateEntry));
    return Builder;
}

FDeadlineCloudAttachmentArrayBuilder::FDeadlineCloudAttachmentArrayBuilder(
    TSharedRef<IPropertyHandle> InPropertyHandle
) : FDetailArrayBuilder(InPropertyHandle, true, false, true),
ArrayProperty(InPropertyHandle->AsArray())
{
}

void FDeadlineCloudAttachmentArrayBuilder::GenerateHeaderRowContent(FDetailWidgetRow& NodeRow)
{
    // Do nothing since we don't want to show the "InnerArray" row, see FDeadlineCloudAttachmentArrayCustomization::CustomizeHeader
    // Source FOptimusParameterBindingArrayCustomization
}

void FDeadlineCloudAttachmentArrayBuilder::GenerateWrapperStructHeaderRowContent(
    FDetailWidgetRow& NodeRow,
    TSharedRef<SWidget> NameContent)
{
    FDetailArrayBuilder::GenerateHeaderRowContent(NodeRow);
    NodeRow.ValueContent()
        .HAlign(HAlign_Left)
        .VAlign(VAlign_Center)
        // Value grabbed from SPropertyEditorArray::GetDesiredWidth
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

void FDeadlineCloudAttachmentArrayBuilder::OnGenerateEntry(
    TSharedRef<IPropertyHandle> ElementProperty,
    int32, IDetailChildrenBuilder& ChildrenBuilder) const
{
    IDetailPropertyRow& PropertyRow = ChildrenBuilder.AddProperty(ElementProperty);

    // Hide the reset to default button since it provides little value
    const FResetToDefaultOverride ResetDefaultOverride =
        FResetToDefaultOverride::Create(TAttribute<bool>(false));

    PropertyRow.OverrideResetToDefault(ResetDefaultOverride);

    TSharedPtr<SWidget> NameWidget;
    TSharedPtr<SWidget> ValueWidget;
    PropertyRow.GetDefaultWidgets(NameWidget, ValueWidget);
    PropertyRow.CustomWidget(true)
        .NameContent()
        .HAlign(HAlign_Fill)
        [
            NameWidget.ToSharedRef()
        ]
        .ValueContent()
        .HAlign(HAlign_Fill)
        [
            ValueWidget.ToSharedRef()
        ];
    ValueWidget.ToSharedRef()->SetEnabled(
        TAttribute<bool>::CreateLambda([this]()
            {
                if (OnIsEnabled.IsBound())
                    return OnIsEnabled.Execute();
                return true;
            })
    );
}

void FDeadlineCloudAttachmentArrayCustomization::CustomizeHeader(
    TSharedRef<IPropertyHandle> InPropertyHandle,
    FDetailWidgetRow& InHeaderRow,
    IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
    const TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Paths", false);

    UMoviePipelineDeadlineCloudExecutorJob* OuterJob = FPropertyAvailabilityHandler::GetOuterJob(InPropertyHandle);
    PropertyOverrideHandler = MakeShared<FPropertyAvailabilityHandler>(OuterJob);

    const FName PropertyPath = *InPropertyHandle->GetProperty()->GetPathName();

    ArrayBuilder = FDeadlineCloudAttachmentArrayBuilder::MakeInstance(ArrayHandle.ToSharedRef());
    if (PropertyOverrideHandler->GetOuterJob(InPropertyHandle))
    {
        ArrayBuilder->OnIsEnabled.BindLambda([this, PropertyPath]()
            {
                return this->PropertyOverrideHandler->IsPropertyRowEnabledInMovieRenderJob(PropertyPath);
            });
    }
    else
    {
        ArrayBuilder->OnIsEnabled.BindLambda([this, PropertyPath]()
            {
                return this->PropertyOverrideHandler->IsPropertyRowEnabledInDataAsset(PropertyPath);
            });
    }
    ArrayBuilder->GenerateWrapperStructHeaderRowContent(InHeaderRow, InPropertyHandle->CreatePropertyNameWidget());
}

void FDeadlineCloudAttachmentArrayCustomization::CustomizeChildren(
    TSharedRef<IPropertyHandle> InPropertyHandle,
    IDetailChildrenBuilder& InChildBuilder,
    IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
    InChildBuilder.AddCustomBuilder(ArrayBuilder.ToSharedRef());
}

FPropertyAvailabilityHandler::FPropertyAvailabilityHandler(UMoviePipelineDeadlineCloudExecutorJob* InJob)
    : Job(InJob)
{

}

UMoviePipelineDeadlineCloudExecutorJob* FPropertyAvailabilityHandler::GetOuterJob(TSharedRef<IPropertyHandle> StructHandle)
{
    TArray<UObject*> OuterObjects;
    StructHandle->GetOuterObjects(OuterObjects);

    if (OuterObjects.Num() == 0)
    {
        return nullptr;
    }

    const TWeakObjectPtr<UObject> OuterObject = OuterObjects[0];
    if (!OuterObject.IsValid())
    {
        return nullptr;
    }
    UMoviePipelineDeadlineCloudExecutorJob* OuterJob = Cast<UMoviePipelineDeadlineCloudExecutorJob>(OuterObject);
    return OuterJob;
}

bool FPropertyAvailabilityHandler::IsPropertyRowEnabledInMovieRenderJob(const FName& InPropertyPath)
{
    return Job && Job->IsPropertyRowEnabledInMovieRenderJob(InPropertyPath);
}

bool FPropertyAvailabilityHandler::IsPropertyRowEnabledInDataAsset(const FName& InPropertyPath)
{
    if (PropertiesDisabledInDataAsset.Contains(InPropertyPath))
    {
        return false;
    }
    return true;
}

void FPropertyAvailabilityHandler::DisableRowInDataAsset(const IDetailPropertyRow& PropertyRow)
{
    const FName PropertyPath = *PropertyRow.GetPropertyHandle()->GetProperty()->GetPathName();
    PropertiesDisabledInDataAsset.Add(PropertyPath);
}


void FPropertyAvailabilityHandler::EnableInMovieRenderQueue(IDetailPropertyRow& PropertyRow, TSharedPtr<SWidget> CustomValueWidget) const
{
    if (!Job) return;

    TSharedPtr<SWidget> NameWidget;
    TSharedPtr<SWidget> ValueWidget;
    FDetailWidgetRow Row;
    PropertyRow.GetDefaultWidgets(NameWidget, ValueWidget, Row);

    const FName PropertyPath = *PropertyRow.GetPropertyHandle()->GetProperty()->GetPathName();
    TAttribute<bool> IsEnabled = TAttribute<bool>::CreateLambda([this, PropertyPath]()
        {
            return Job->IsPropertyRowEnabledInMovieRenderJob(PropertyPath);
        });

    if (CustomValueWidget.IsValid())
    {
        CustomValueWidget->SetEnabled(IsEnabled);
    }
	else
	{
		ValueWidget->SetEnabled(IsEnabled);
	}

    PropertyRow
        .CustomWidget(true)
        .NameContent()
        .MinDesiredWidth(Row.NameWidget.MinWidth)
        .MaxDesiredWidth(Row.NameWidget.MaxWidth)
        .HAlign(HAlign_Fill)
        [
            SNew(SHorizontalBox)
                + SHorizontalBox::Slot()
                .AutoWidth()
                .Padding(4, 0)
                [
                    SNew(SCheckBox)
                        .IsChecked_Lambda([this, PropertyPath]()
                            {
                                return Job->IsPropertyRowEnabledInMovieRenderJob(PropertyPath) ?
                                    ECheckBoxState::Checked : ECheckBoxState::Unchecked;
                            })
                        .OnCheckStateChanged_Lambda([this, PropertyPath](const ECheckBoxState NewState)
                            {
                                return Job->SetPropertyRowEnabledInMovieRenderJob(
                                    PropertyPath, NewState == ECheckBoxState::Checked
                                );
                            })
                ]
                + SHorizontalBox::Slot()
                [
                    NameWidget.ToSharedRef()
                ]
        ]
        .ValueContent()
        .MinDesiredWidth(Row.ValueWidget.MinWidth)
        .MaxDesiredWidth(Row.ValueWidget.MaxWidth)
        .VAlign(VAlign_Center)
        [
            CustomValueWidget.IsValid() ? CustomValueWidget.ToSharedRef() : ValueWidget.ToSharedRef()
        ];
}


#undef LOCTEXT_NAMESPACE