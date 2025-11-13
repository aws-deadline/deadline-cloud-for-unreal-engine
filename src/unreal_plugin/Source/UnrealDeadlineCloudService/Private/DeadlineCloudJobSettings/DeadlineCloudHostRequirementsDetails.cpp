// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudHostRequirementsDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudHostRequirements.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "PropertyEditorModule.h"
#include "Modules/ModuleManager.h"
#include "DetailLayoutBuilder.h"
#include "DetailWidgetRow.h"
#include "DesktopPlatformModule.h"
#include "UnrealDeadlineCloudServiceModule.h"
#include "CoreMinimal.h"
#include "Widgets/Input/SSpinbox.h" 
#include "Templates/SharedPointer.h"
#include "IDetailsView.h"
#include "IDetailChildrenBuilder.h"
#include "IDetailPropertyRow.h"
#include "IPropertyUtilities.h"  
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"
#include "EditorDirectories.h"
#include "Widgets/Input/SFilePathPicker.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SCheckBox.h"
#include "Framework/MetaData/DriverMetaData.h"
#include "PythonAPILibraries/DeadlineCloudJobBundleLibrary.h"
#include "Widgets/Input/SNumericEntryBox.h"
#include "Widgets/Layout/SWidgetSwitcher.h"
#define LOCTEXT_NAMESPACE "HostReq"

TSharedRef<IDetailCustomization> FDeadlineCloudHostRequirementsDetails::MakeInstance()
{
	return MakeShareable(new FDeadlineCloudHostRequirementsDetails);
}

void FDeadlineCloudHostRequirementsDetails::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
	// The detail layout builder that is using us
	MainDetailLayout = &DetailBuilder;

	TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
	MainDetailLayout->GetObjectsBeingCustomized(ObjectsBeingCustomized);
	Settings = Cast<UDeadlineCloudHostRequirements>(ObjectsBeingCustomized[0].Get());

	TSharedPtr<FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget> ConsistencyUpdateWidget;
	FParametersConsistencyCheckResult result;

	TSharedPtr<FDeadlineCloudDetailsWidgetsHelper::SEyeUpdateWidget> HiddenParametersUpdateWidget;

	TSharedRef<IPropertyHandle> PathToTemplate = MainDetailLayout->GetProperty("PathToTemplate");
	IDetailPropertyRow* PathToTemplateRow = MainDetailLayout->EditDefaultProperty(PathToTemplate);

	if (PathToTemplateRow)
	{
		TSharedPtr<SWidget> NameWidget;
		TSharedPtr<SWidget> ValueWidget;
		PathToTemplateRow->GetDefaultWidgets(NameWidget, ValueWidget);

		FName Tag = FName("HostReq.PathToTemplate");
		ValueWidget->AddMetadata(FDriverMetaData::Id(Tag));

		PathToTemplateRow->CustomWidget()
			.NameContent()
			[
				NameWidget.ToSharedRef()
			]
			.ValueContent()
			[
				ValueWidget.ToSharedRef()
			];	
	}

	IDetailCategoryBuilder& PropertiesCategory = MainDetailLayout->EditCategory("Parameters");

	//  Dispatcher handle bind
	if (Settings.IsValid() && (MainDetailLayout != nullptr))
	{
		Settings->OnPathChanged = FSimpleDelegate::CreateSP(this, &FDeadlineCloudHostRequirementsDetails::ForceRefreshDetails);
	};

	/* Update all when one Parameters widget is checked as hidden */
	if (Settings.IsValid())
	{
		Settings->OnParameterHidden.BindSP(this, &FDeadlineCloudHostRequirementsDetails::RespondToEvent);
	}

	PropertiesCategory.AddCustomRow(FText::FromString("Visibility"))
		.Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudHostRequirementsDetails::GetEyeWidgetVisibility)))
		.WholeRowContent()
		[
			SAssignNew(HiddenParametersUpdateWidget, FDeadlineCloudDetailsWidgetsHelper::SEyeUpdateWidget)
				.OnEyeUpdateButtonClicked(FSimpleDelegate::CreateSP(this, &FDeadlineCloudHostRequirementsDetails::OnResetHiddenParametersClicked))
		];
}

void FDeadlineCloudHostRequirementsDetails::ForceRefreshDetails()
{
	MainDetailLayout->ForceRefreshDetails();
}

void FDeadlineCloudHostRequirementsDetails::RespondToEvent()
{
	ForceRefreshDetails();
}

void FDeadlineCloudHostRequirementsDetails::OnResetHiddenParametersClicked()
{
	Settings->GetAmountsHiddenManager().ResetToDefault();
	Settings->GetAttributesHiddenManager().ResetToDefault();
	ForceRefreshDetails();
}

EVisibility FDeadlineCloudHostRequirementsDetails::GetEyeWidgetVisibility() const
{
	return EVisibility::Collapsed;
}

TSharedRef<FDeadlineCloudAttributeBuilder> FDeadlineCloudAttributeBuilder::MakeInstance(
    TSharedRef<IPropertyHandle> InPropertyHandle, bool bIsDefaultRequirement)
{
	return MakeShared<FDeadlineCloudAttributeBuilder>(InPropertyHandle, bIsDefaultRequirement);
}

FDeadlineCloudAttributeBuilder::FDeadlineCloudAttributeBuilder(TSharedRef<IPropertyHandle> InPropertyHandle, bool IsDefaultRequirement)
	: FDeadlineCloudRequirementBuilder(InPropertyHandle, IsDefaultRequirement)
{
}

FName FDeadlineCloudAttributeBuilder::GetName() const
{
    return FName("Attribute");
}

void FDeadlineCloudAttributeBuilder::OnEyeHideWidgetButtonClicked(FName InProperty) const
{
    if (HostReq)
    {
        if (HostReq->GetAttributesHiddenManager().Contains(InProperty))
        {
            HostReq->GetAttributesHiddenManager().Remove(InProperty);
        }
        else
        {
            HostReq->GetAttributesHiddenManager().Add(InProperty);
        }
    }
}

void FDeadlineCloudAttributeBuilder::BindEyeWidget(TSharedRef<FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox> EyeWidget)
{
    EyeWidget->SetOnCheckStateChangedDelegate(FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox::FOnCheckStateChangedDelegate::CreateSP(this, &FDeadlineCloudRequirementBuilder::OnEyeHideWidgetButtonClicked));
	EyeWidget->SetVisibility((MrqJob) ? EVisibility::Hidden : EVisibility::Visible);
}

TSharedRef<SWidget> FDeadlineCloudAttributeBuilder::CreateNameWidget(TSharedPtr<IPropertyHandle> NameHandle, FString Name, FString FriendlyName)
{
    TSharedPtr<SWidget> NameWidget;
    if (bIsDefaultRequirement)
    {
        NameWidget = SNew(STextBlock)
            .Text(FText::FromString(FriendlyName))
            .ToolTipText(FText::FromString(Name))
            .IsEnabled(IsEnabledAttr)
            .Font(IDetailLayoutBuilder::GetDetailFont());
    }
    else
    {
        NameWidget = FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(
            NameHandle, 
            EValueType::STRING, 
            EValueValidationType::Default, 
            FText::FromString("attr.[.]*")
        );
        NameWidget->SetEnabled(IsEnabledAttr);
    }

	return NameWidget.ToSharedRef();
}

TSharedRef<SWidget> FDeadlineCloudAttributeBuilder::CreateValueWidget()
{
    TSharedPtr<IPropertyHandle> SelectedValueHandle = Property->GetChildHandle(GET_MEMBER_NAME_CHECKED(FDeadlineCloudAttributeRequirements, SelectedValue));
    check(SelectedValueHandle.IsValid());
    TSharedPtr<IPropertyHandle> AllOfHandle = Property->GetChildHandle(GET_MEMBER_NAME_CHECKED(FDeadlineCloudAttributeRequirements, AllOf));
    check(AllOfHandle.IsValid());
    TSharedPtr<IPropertyHandle> AnyOfHandle = Property->GetChildHandle(GET_MEMBER_NAME_CHECKED(FDeadlineCloudAttributeRequirements, AnyOf));
    check(AnyOfHandle.IsValid());

    TSharedPtr<SWidget> ValueWidget;
    if (bIsDefaultRequirement)
    {
        ValueWidget = FDeadlineCloudDetailsWidgetsHelper::CreateDefaultAttributeValueWidget(AllOfHandle, AnyOfHandle, SelectedValueHandle, IsEnabledAttr);
    }
    else
    {
        ValueWidget = FDeadlineCloudDetailsWidgetsHelper::CreateCustomAttributeValueWidget(AllOfHandle, AnyOfHandle, IsEnabledAttr);
    }

	return ValueWidget.ToSharedRef();
}

bool FDeadlineCloudAttributeBuilder::IsPropertyHidden(FName Parameter) const
{
    bool Contains = false;
    if (HostReq)
    {
        Contains = HostReq->GetAttributesHiddenManager().Contains(Parameter);
    }
    return Contains;
}

bool FDeadlineCloudAttributeBuilder::IsEyeWidgetEnabled(FName Parameter) const
{
    bool result = false;
    if (HostReq)
    {
        result = HostReq->GetAttributesHiddenManager().Contains(Parameter);
    }

    return result;
}

bool FDeadlineCloudAttributeBuilder::IsParameterChangedFromDefault(FName Parameter) const
{
    if (!HostReq)
        return false;

    return HostReq->GetAttributesHiddenManager().IsDefaultForParameter(Parameter);
}

TSharedRef<FDeadlineCloudAmountBuilder> FDeadlineCloudAmountBuilder::MakeInstance(
    TSharedRef<IPropertyHandle> InPropertyHandle, bool IsDefaultRequirement)
{
    return MakeShared<FDeadlineCloudAmountBuilder>(InPropertyHandle, IsDefaultRequirement);
}

FDeadlineCloudAmountBuilder::FDeadlineCloudAmountBuilder(TSharedRef<IPropertyHandle> InPropertyHandle, bool IsDefaultRequirement)
	: FDeadlineCloudRequirementBuilder(InPropertyHandle, IsDefaultRequirement)
{
}

FName FDeadlineCloudAmountBuilder::GetName() const
{
    return FName("Amount");
}


void FDeadlineCloudAmountBuilder::OnEyeHideWidgetButtonClicked(FName InProperty) const
{
    if (HostReq)
    {
        if (HostReq->GetAmountsHiddenManager().Contains(InProperty))
        {
            HostReq->GetAmountsHiddenManager().Remove(InProperty);
        }
        else
        {
            HostReq->GetAmountsHiddenManager().Add(InProperty);
        }
    }
}

void FDeadlineCloudAmountBuilder::BindEyeWidget(TSharedRef<FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox> EyeWidget)
{
    EyeWidget->SetOnCheckStateChangedDelegate(FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox::FOnCheckStateChangedDelegate::CreateSP(this, &FDeadlineCloudRequirementBuilder::OnEyeHideWidgetButtonClicked));
    EyeWidget->SetVisibility((MrqJob) ? EVisibility::Hidden : EVisibility::Visible);
}

TSharedRef<SWidget> FDeadlineCloudAmountBuilder::CreateNameWidget(TSharedPtr<IPropertyHandle> NameHandle, FString Name, FString FriendlyName)
{
    TSharedPtr<SWidget> NameWidget;
    if (bIsDefaultRequirement)
    {
        NameWidget = SNew(STextBlock)
            .Text(FText::FromString(FriendlyName))
            .ToolTipText(FText::FromString(Name))
            .IsEnabled(IsEnabledAttr)
            .Font(IDetailLayoutBuilder::GetDetailFont());
    }
    else
    {
        NameWidget = FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(
            NameHandle, 
            EValueType::STRING,
			EValueValidationType::Default,
			FText::FromString("amount.[.]*")
        );
        NameWidget->SetEnabled(IsEnabledAttr);
    }

	return NameWidget.ToSharedRef();
}

TSharedRef<SWidget> FDeadlineCloudAmountBuilder::CreateValueWidget()
{
    TSharedPtr<IPropertyHandle> RangeHandle = Property->GetChildHandle("AmountRequirement");
    return FDeadlineCloudDetailsWidgetsHelper::CreateAmountValueWidget(RangeHandle, IsEnabledAttr);
}

bool FDeadlineCloudAmountBuilder::IsPropertyHidden(FName Parameter) const
{
    bool Contains = false;
    if (HostReq)
    {
        Contains = HostReq->GetAmountsHiddenManager().Contains(Parameter);
    }
    return Contains;
}

bool FDeadlineCloudAmountBuilder::IsEyeWidgetEnabled(FName Parameter) const
{
    bool result = false;
    if (HostReq)
    {
        result = HostReq->GetAmountsHiddenManager().Contains(Parameter);
    }

    return result;
}

bool FDeadlineCloudAmountBuilder::IsParameterChangedFromDefault(FName Parameter) const
{
    if (!HostReq)
        return false;

    return HostReq->GetAmountsHiddenManager().IsDefaultForParameter(Parameter);
}

TSharedRef<IPropertyTypeCustomization>
FDeadlineCloudHostRequirementCustomization::MakeInstance()
{
    return MakeShareable(new FDeadlineCloudHostRequirementCustomization);
}

void FDeadlineCloudHostRequirementCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> StructPropertyHandle, FDetailWidgetRow& HeaderRow, IPropertyTypeCustomizationUtils& CustomizationUtils)
{
    //wihout header
}

void FDeadlineCloudHostRequirementCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> StructPropertyHandle, IDetailChildrenBuilder& StructBuilder, IPropertyTypeCustomizationUtils& CustomizationUtils)
{
    TSharedPtr<IPropertyHandle> AttributesMapHandle = StructPropertyHandle->GetChildHandle("Attributes", false);
    check(AttributesMapHandle.IsValid());

    TSharedPtr<IPropertyHandle> AmountsMapHandle = StructPropertyHandle->GetChildHandle("Amounts", false);
    check(AmountsMapHandle.IsValid());

    //add default Attributes as child rows
    AddDefaultsAttributesRequirementsRows(AttributesMapHandle, StructBuilder, StructPropertyHandle);
    AddDefaultsAmountsRequirementsRows(AmountsMapHandle, StructBuilder, StructPropertyHandle);

    auto AmountsMapBuilder = FDeadlineCloudCustomAmountRequirementCustomization::MakeInstance(AmountsMapHandle.ToSharedRef());
    StructBuilder.AddCustomBuilder(AmountsMapBuilder);

	auto AttributesMapBuilder = FDeadlineCloudCustomAttributeRequirementCustomization::MakeInstance(AttributesMapHandle.ToSharedRef());
	StructBuilder.AddCustomBuilder(AttributesMapBuilder);

    TWeakPtr<IPropertyUtilities> WeakPU = CustomizationUtils.GetPropertyUtilities();

    AmountsMapHandle->AsMap()->SetOnNumElementsChanged(
        FSimpleDelegate::CreateSPLambda(this, [WeakPU]()
            {
                if (auto PU = WeakPU.Pin())
                {
                    PU->RequestForceRefresh();
                }
        })
    );

    AttributesMapHandle->AsMap()->SetOnNumElementsChanged(
        FSimpleDelegate::CreateSPLambda(this, [WeakPU]()
            {
                if (auto PU = WeakPU.Pin())
                {
                    PU->RequestForceRefresh();
                }
            })
    );
}

void FDeadlineCloudHostRequirementCustomization::AddDefaultsAmountsRequirementsRows(
    TSharedPtr<IPropertyHandle> MapHandle, 
    IDetailChildrenBuilder& StructBuilder, 
    TSharedRef<IPropertyHandle> StructPropertyHandle)
{
    uint32 NumChildren = 0;
    MapHandle->GetNumChildren(NumChildren);
    for (uint32 ChildIndex = 0; ChildIndex < NumChildren; ++ChildIndex)
    {
        TSharedPtr<IPropertyHandle> ItemHandle = MapHandle->AsMap()->GetElement(ChildIndex);
        if (!ItemHandle.IsValid())
        {
            continue;
        }

        FString AttributeName;
        ItemHandle->GetKeyHandle()->GetValue(AttributeName);
        bool bIsDefaultAttribute = false;

        if (auto Library = UDeadlineCloudJobBundleLibrary::Get())
        {
            bIsDefaultAttribute = Library->IsAmountRequirementDefault(AttributeName);
        }
        else
        {
            UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
        }

        if (!bIsDefaultAttribute)
        {
            continue;
        }

        auto ChildBuilder = FDeadlineCloudAmountBuilder::MakeInstance(ItemHandle.ToSharedRef(), bIsDefaultAttribute);
        StructBuilder.AddCustomBuilder(ChildBuilder);
    }
}

void FDeadlineCloudHostRequirementCustomization::AddDefaultsAttributesRequirementsRows(
    TSharedPtr<IPropertyHandle> MapHandle, 
    IDetailChildrenBuilder& StructBuilder, 
    TSharedRef<IPropertyHandle> StructPropertyHandle)
{
    uint32 NumChildren = 0;
    MapHandle->GetNumChildren(NumChildren);
    for (uint32 ChildIndex = 0; ChildIndex < NumChildren; ++ChildIndex)
    {
        TSharedPtr<IPropertyHandle> ItemHandle = MapHandle->AsMap()->GetElement(ChildIndex);
        if (!ItemHandle.IsValid())
        {
            continue;
        }

        FString AttributeName;
        ItemHandle->GetKeyHandle()->GetValue(AttributeName);
        bool bIsDefaultAttribute = false;

        if (auto Library = UDeadlineCloudJobBundleLibrary::Get())
        {
            bIsDefaultAttribute = Library->IsAttributeRequirementDefault(AttributeName);
        }
        else
        {
            UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
        }

        if (!bIsDefaultAttribute)
        {
            continue;
        }

        auto ChildBuilder = FDeadlineCloudAttributeBuilder::MakeInstance(ItemHandle.ToSharedRef(), bIsDefaultAttribute);
        StructBuilder.AddCustomBuilder(ChildBuilder);
    }
}

FText FDeadlineCloudCustomAmountRequirementCustomization::GetHeaderRowName() const
{
    return LOCTEXT("AmountRequirementsHeaderTitle", "Custom Amount Requirements");
}

TSharedRef<class IDetailCustomNodeBuilder> FDeadlineCloudCustomAmountRequirementCustomization::CreateChildBuilder(TSharedRef<IPropertyHandle> InPropertyHandle, bool bIsDefaultAttribute)
{
    return FDeadlineCloudAmountBuilder::MakeInstance(InPropertyHandle, bIsDefaultAttribute);
}

bool FDeadlineCloudCustomAmountRequirementCustomization::IsDefaultRequirement(const TSharedPtr<IPropertyHandle>& ElementHandle)
{
    FString AttributeName;
    ElementHandle->GetKeyHandle()->GetValue(AttributeName);
    bool bIsDefaultAttribute = false;
    if (auto Library = UDeadlineCloudJobBundleLibrary::Get())
    {
        bIsDefaultAttribute = Library->IsAmountRequirementDefault(AttributeName);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
    }

	return bIsDefaultAttribute;
}

int32 FDeadlineCloudCustomAmountRequirementCustomization::GetFilteredCount(const TSharedPtr<IPropertyHandle>& Map)
{
    int32 Filtered = 0;

    uint32 NumElements = 0;
    Map->GetNumChildren(NumElements);
    for (uint32 Index = 0; Index < NumElements; ++Index)
    {
		auto Element = Map->GetChildHandle(Index);
        if (Element.IsValid()
            && !IsDefaultRequirement(Element))
        {
            ++Filtered;
        }
    }
    return Filtered;
}

FName FDeadlineCloudCustomAmountRequirementCustomization::GetName() const
{
    return FName("CustomAmountRequirements");
}


TSharedRef<FDeadlineCloudCustomAmountRequirementCustomization> FDeadlineCloudCustomAmountRequirementCustomization::MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle)
{
    return MakeShareable(new FDeadlineCloudCustomAmountRequirementCustomization(InPropertyHandle));
}

FDeadlineCloudCustomAmountRequirementCustomization::FDeadlineCloudCustomAmountRequirementCustomization(TSharedRef<IPropertyHandle> InPropertyHandle)
	: FDeadlineCloudCustomRequirementCustomization(InPropertyHandle)
{
}

TSharedRef<FDeadlineCloudCustomAttributeRequirementCustomization> FDeadlineCloudCustomAttributeRequirementCustomization::MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle)
{
    return MakeShareable(new FDeadlineCloudCustomAttributeRequirementCustomization(InPropertyHandle));
}

FDeadlineCloudCustomAttributeRequirementCustomization::FDeadlineCloudCustomAttributeRequirementCustomization(TSharedRef<IPropertyHandle> InPropertyHandle)
    : FDeadlineCloudCustomRequirementCustomization(InPropertyHandle)
{
}

FText FDeadlineCloudCustomAttributeRequirementCustomization::GetHeaderRowName() const
{
    return LOCTEXT("AttrubutesRequirementsHeaderTitle", "Custom Attributes Requirements");
}

TSharedRef<class IDetailCustomNodeBuilder> FDeadlineCloudCustomAttributeRequirementCustomization::CreateChildBuilder(TSharedRef<IPropertyHandle> InPropertyHandle, bool bIsDefaultAttribute)
{
    return FDeadlineCloudAttributeBuilder::MakeInstance(InPropertyHandle, bIsDefaultAttribute);
}

bool FDeadlineCloudCustomAttributeRequirementCustomization::IsDefaultRequirement(const TSharedPtr<IPropertyHandle>& ElementHandle)
{
    FString Name;
    ElementHandle->GetKeyHandle()->GetValue(Name);
    bool bIsDefaultAttribute = false;
    if (auto Library = UDeadlineCloudJobBundleLibrary::Get())
    {
        bIsDefaultAttribute = Library->IsAttributeRequirementDefault(Name);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
    }

    return bIsDefaultAttribute;
}

int32 FDeadlineCloudCustomAttributeRequirementCustomization::GetFilteredCount(const TSharedPtr<IPropertyHandle>& Map)
{
    int32 Filtered = 0;

    uint32 NumElements = 0;
    Map->GetNumChildren(NumElements);
    for (uint32 Index = 0; Index < NumElements; ++Index)
    {
        auto Element = Map->GetChildHandle(Index);
        if (Element.IsValid()
            && !IsDefaultRequirement(Element))
        {
            ++Filtered;
        }
    }
    return Filtered;
}


FName FDeadlineCloudCustomAttributeRequirementCustomization::GetName() const
{
    return FName("CustomAttributeRequirements");
}

FDeadlineCloudRequirementBuilder::FDeadlineCloudRequirementBuilder(
    TSharedRef<IPropertyHandle> InPropertyHandle, bool IsDefaultRequirement)
    : Property(InPropertyHandle), bIsDefaultRequirement(IsDefaultRequirement)
{
}

void FDeadlineCloudRequirementBuilder::GenerateHeaderRowContent(FDetailWidgetRow& InNodeRow)
{
    TSharedPtr<IPropertyHandle> NameHandle = Property->GetKeyHandle();
    FString Name;
    if (NameHandle.IsValid())
    {
        NameHandle->GetValue(Name);
    }

    MrqJob = FDeadlineCloudDetailsWidgetsHelper::GetMrqJob(Property);
    HostReq = FDeadlineCloudDetailsWidgetsHelper::GetPropertyOuter<UDeadlineCloudHostRequirements>(Property);
    IsEnabledHandle = Property->GetChildHandle("bIsEnabled");
    check(IsEnabledHandle.IsValid());

    IsEnabledAttr = TAttribute<bool>::CreateLambda([this]()
        {
            if (!MrqJob)
            {
                return true;
            }

            if (!IsEnabledHandle.IsValid())
            {
                return false;
            }

            bool bEnabled;
            if (IsEnabledHandle->GetValue(bEnabled) != FPropertyAccess::Result::Success)
            {
                return false;
            }

            return bEnabled;
        });

    FString FriendlyName = Name;

    if (bIsDefaultRequirement; auto Library = UDeadlineCloudJobBundleLibrary::Get())
    {
        FriendlyName = Library->GetRequirementFriendlyName(Name);
    }
    else
    {
        UE_LOG(LogTemp, Error, TEXT("Error get DeadlineCloudJobBundleLibrary"));
    }

    TSharedPtr<SWidget> NameWidget = CreateNameWidget(NameHandle, Name, FriendlyName);

    bool Checked = !(IsEyeWidgetEnabled(FName(Name)));
    bool isChangedByUser = !IsParameterChangedFromDefault(FName(Name));
    TSharedRef<FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox> EyeWidget = SNew(FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox, FName(Name), Checked, isChangedByUser);

	BindEyeWidget(EyeWidget);

    InNodeRow
        .NameContent()
        .HAlign(HAlign_Fill)
        [
            SNew(SHorizontalBox)
                + SHorizontalBox::Slot()
                .AutoWidth()
                .Padding(0.f)
                [
                    FDeadlineCloudDetailsWidgetsHelper::CreateMrqCheckBoxWidgetForHostRequiremets(
                        MrqJob,
                        IsEnabledHandle,
                        IsEnabledAttr
                    )
                ]
            + SHorizontalBox::Slot()
                .FillWidth(1.f)
                .HAlign(HAlign_Fill)
                .Padding(0.f, 0.f, 4.f, 0.f)
                .VAlign(VAlign_Center)
                [
                    NameWidget.ToSharedRef()
                ]
        ]
    .ValueContent()
		.HAlign(HAlign_Fill)
        [
            SNew(SHorizontalBox)
                + SHorizontalBox::Slot()
				.FillWidth(1.f)
				.HAlign(HAlign_Fill)
                .Padding(0, 0, 4, 0)
                [
					CreateValueWidget()
                ]
                + SHorizontalBox::Slot()
                .AutoWidth()
                .Padding(8, 0, 0, 0)
                [
                    bIsDefaultRequirement
                        ? SNullWidget::NullWidget
                        : Property->CreateDefaultPropertyButtonWidgets()
                ]
        ]
    .ExtensionContent()
        [
            EyeWidget
        ];

    const FResetToDefaultOverride ResetDefaultOverride =
        FResetToDefaultOverride::Create(TAttribute<bool>(false));

    InNodeRow.OverrideResetToDefault(ResetDefaultOverride);
}

void FDeadlineCloudRequirementBuilder::GenerateChildContent(IDetailChildrenBuilder& InChildrenBuilder)
{
    //Without children
}

TSharedPtr<IPropertyHandle> FDeadlineCloudRequirementBuilder::GetPropertyHandle() const
{
    return Property;
}

FDeadlineCloudCustomRequirementCustomization::FDeadlineCloudCustomRequirementCustomization(TSharedRef<IPropertyHandle> InPropertyHandle)
	: Property(InPropertyHandle)
{
}

void FDeadlineCloudCustomRequirementCustomization::GenerateHeaderRowContent(FDetailWidgetRow& InNodeRow)
{
    // We need the map interface for indexed removal.
    TSharedPtr<IPropertyHandleMap> MapInterface = Property->AsMap();
    check(MapInterface.IsValid());

    TWeakPtr<IPropertyHandle>    WeakMapHandle = Property;
    TWeakPtr<IPropertyHandleMap> WeakMapIface = MapInterface;

    // Dynamic header text: "Elements: N" where N is your filtered count (!IsDefaultRequirement).
    const TAttribute<FText> HeaderTextAttr = TAttribute<FText>::Create(
        TAttribute<FText>::FGetter::CreateLambda([this, WeakMapHandle]()
            {
                int32 Count = 0;
                if (auto Pinned = WeakMapHandle.Pin())
                {
                    Count = GetFilteredCount(Pinned);
                }
                return FText::Format(
                    LOCTEXT("RequirementsHeaderCounter", "{0} element(s)"),
                    FText::AsNumber(Count));
            })
    );

    // Delete-only-defaults action (uses your IsDefaultRequirement).
    auto DeleteDefaults = [this, WeakMapHandle, WeakMapIface]()
        {
            auto MapHandlePinned = WeakMapHandle.Pin();
            auto MapIfacePinned = WeakMapIface.Pin();
            if (!MapHandlePinned.IsValid() || !MapIfacePinned.IsValid())
            {
                return FReply::Handled();
            }

            // Collect indices of items that not pass IsDefaultRequirement.
            TArray<int32> IndexesToRemove;
            uint32 NumChildren = 0;
            MapHandlePinned->GetNumChildren(NumChildren);

            for (int32 Index = 0; Index < static_cast<int32>(NumChildren); ++Index)
            {
                TSharedPtr<IPropertyHandle> ElementHandle = MapHandlePinned->GetChildHandle(Index);
                if (ElementHandle.IsValid() && !IsDefaultRequirement(ElementHandle))
                {
                    IndexesToRemove.Add(Index);
                }
            }

            // Remove from the end to keep indices valid.
            IndexesToRemove.Sort(TGreater<int32>());
            for (int32 Idx : IndexesToRemove)
            {
                MapIfacePinned->DeleteItem(Idx);
            }

            return FReply::Handled();
        };

    InNodeRow
        .NameContent()
        [
            SNew(STextBlock)
                .Text(GetHeaderRowName())
                .Font(IDetailLayoutBuilder::GetDetailFont())
        ]
        .ValueContent()
        [
            SNew(SHorizontalBox)

                // Left: standard counter text (filtered count).
                + SHorizontalBox::Slot()
                .VAlign(VAlign_Center)
                .AutoWidth()
                [
                    SNew(STextBlock)
                        .Text(HeaderTextAttr) // "Elements: N"
                        .Font(IDetailLayoutBuilder::GetDetailFont())
                ]

                + SHorizontalBox::Slot()
                .AutoWidth()
                .VAlign(VAlign_Center)
                .Padding(2.f, 0.f)
                [
                    SNew(SButton)
                        .ButtonStyle(FAppStyle::Get(), "SimpleButton")
                        .ToolTipText(LOCTEXT("AddElementTT", "Add a new element."))
                        .OnClicked_Lambda([WeakMapIface]()
                            {
                                if (auto MapIfacePinned = WeakMapIface.Pin())
                                {
                                    // Add a new item — this creates a new key/value entry
                                    MapIfacePinned->AddItem();
                                }
                                return FReply::Handled();
                            })
                        [
                            SNew(SImage)
                                .Image(FAppStyle::Get().GetBrush("Icons.PlusCircle"))
                        ]
                ]
            // Default-styled Delete button: removes only non default elements (trash icon).
            + SHorizontalBox::Slot()
                .AutoWidth()
                .VAlign(VAlign_Center)
                .Padding(2.f, 0.f)
                [
                    SNew(SButton)
                        .ButtonStyle(FAppStyle::Get(), "SimpleButton")
                        .OnClicked_Lambda(DeleteDefaults)
                        [
                            SNew(SImage)
                                .Image(FAppStyle::Get().GetBrush("Icons.Delete"))
                        ]
                ]
        ];

    auto EmptyCopyPasteAction = FUIAction(
        FExecuteAction::CreateLambda([]() {}),
        FCanExecuteAction::CreateLambda([]() { return false; })
    );

    const FResetToDefaultOverride ResetDefaultOverride =
        FResetToDefaultOverride::Create(TAttribute<bool>(false));

    InNodeRow.OverrideResetToDefault(ResetDefaultOverride);
    InNodeRow.CopyAction(EmptyCopyPasteAction);
    InNodeRow.PasteAction(EmptyCopyPasteAction);
}

void FDeadlineCloudCustomRequirementCustomization::GenerateChildContent(IDetailChildrenBuilder& InChildrenBuilder)
{
    // For custom attributes, we need to use a custom builder for each element 
    uint32 NumElements = 0;
    Property->GetNumChildren(NumElements);
    for (uint32 Index = 0; Index < NumElements; ++Index)
    {
        TSharedPtr<IPropertyHandle> ElementHandle = Property->GetChildHandle(Index);
        bool bIsDefaultAttribute = IsDefaultRequirement(ElementHandle);

        if (bIsDefaultAttribute)
        {
            continue;
        }

		auto ChildBuilder = CreateChildBuilder(ElementHandle.ToSharedRef(), bIsDefaultAttribute);
        InChildrenBuilder.AddCustomBuilder(ChildBuilder);
    };
}

TSharedPtr<IPropertyHandle> FDeadlineCloudCustomRequirementCustomization::GetPropertyHandle() const
{
    return Property;
}

#undef LOCTEXT_NAMESPACE

