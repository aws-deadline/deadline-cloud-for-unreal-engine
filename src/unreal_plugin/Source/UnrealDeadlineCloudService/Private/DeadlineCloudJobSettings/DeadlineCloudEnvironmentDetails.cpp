// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudEnvironmentDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudEnvironment.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "PropertyEditorModule.h"
#include "Modules/ModuleManager.h"
#include "DetailLayoutBuilder.h"
#include "DetailWidgetRow.h"
#include "DesktopPlatformModule.h"
#include "UnrealDeadlineCloudServiceModule.h"
#include "CoreMinimal.h"

#include "Templates/SharedPointer.h"
#include "IDetailsView.h"
#include "IDetailChildrenBuilder.h"
#include "IDetailPropertyRow.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"
#include "EditorDirectories.h"
#include "Widgets/Input/SFilePathPicker.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SCheckBox.h"
#include "Framework/MetaData/DriverMetaData.h"
#define LOCTEXT_NAMESPACE "EnvironmentDetails"

bool FDeadlineCloudEnvironmentDetails::CheckConsistency(UDeadlineCloudEnvironment* Env)
{
    FParametersConsistencyCheckResult result;
    if (Env != nullptr)
    {
        result = Env->CheckEnvironmentVariablesConsistency(Env);

        UE_LOG(LogTemp, Warning, TEXT("Check consistency result: %s"), *result.Reason);
        return result.Passed;
	}
	else
	{
		UE_LOG(LogTemp, Error, TEXT("Deadline Environment is nullptr"));
		return false;
	}
}
/*Details*/
TSharedRef<IDetailCustomization> FDeadlineCloudEnvironmentDetails::MakeInstance()
{
	return MakeShareable(new FDeadlineCloudEnvironmentDetails);
}

void FDeadlineCloudEnvironmentDetails::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
	// The detail layout builder that is using us
	MainDetailLayout = &DetailBuilder;

	TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
	MainDetailLayout->GetObjectsBeingCustomized(ObjectsBeingCustomized);
	Settings = Cast<UDeadlineCloudEnvironment>(ObjectsBeingCustomized[0].Get());

	TSharedPtr<FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget> ConsistencyUpdateWidget;
	FParametersConsistencyCheckResult result;

	TSharedPtr<FDeadlineCloudDetailsWidgetsHelper::SEyeUpdateWidget> HiddenParametersUpdateWidget;

	/* Consistency check */
	if (Settings.IsValid() && Settings->Variables.Variables.Num() > 0)
	{
		UDeadlineCloudEnvironment* MyObject = Settings.Get();
		bCheckConsistensyPassed = CheckConsistency(MyObject);
	}

	TSharedRef<IPropertyHandle> PathToTemplate = MainDetailLayout->GetProperty("PathToTemplate");
	IDetailPropertyRow* PathToTemplateRow = MainDetailLayout->EditDefaultProperty(PathToTemplate);

	if (PathToTemplateRow)
	{
		TSharedPtr<SWidget> NameWidget;
		TSharedPtr<SWidget> ValueWidget;
		PathToTemplateRow->GetDefaultWidgets(NameWidget, ValueWidget);

		FName Tag = FName("Environment.PathToTemplate");
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

	PropertiesCategory.AddCustomRow(FText::FromString("Consistency"))
		.Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudEnvironmentDetails::GetWidgetVisibility)))
		.WholeRowContent()
		[
			SAssignNew(ConsistencyUpdateWidget, FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget)
				.OnFixButtonClicked(FSimpleDelegate::CreateSP(this, &FDeadlineCloudEnvironmentDetails::OnConsistencyButtonClicked))
		];

	//  Dispatcher handle bind
	if (Settings.IsValid() && (MainDetailLayout != nullptr))
	{
		Settings->OnPathChanged = FSimpleDelegate::CreateSP(this, &FDeadlineCloudEnvironmentDetails::ForceRefreshDetails);
	};

	/* Update all when one Parameters widget is checked as hidden */
	if (Settings.IsValid())
	{
		Settings->OnParameterHidden.BindSP(this, &FDeadlineCloudEnvironmentDetails::RespondToEvent);
	}

	PropertiesCategory.AddCustomRow(FText::FromString("Visibility"))
		.Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudEnvironmentDetails::GetEyeWidgetVisibility)))
		.WholeRowContent()
		[
			SAssignNew(HiddenParametersUpdateWidget, FDeadlineCloudDetailsWidgetsHelper::SEyeUpdateWidget)

				.OnEyeUpdateButtonClicked(FSimpleDelegate::CreateSP(this, &FDeadlineCloudEnvironmentDetails::OnResetHiddenParametersClicked))
		];
}

void FDeadlineCloudEnvironmentDetails::OnConsistencyButtonClicked()
{
	{
		Settings->FixEnvironmentVariablesConsistency(Settings.Get());
		UE_LOG(LogTemp, Warning, TEXT("FixStepParametersConsistency"));
		ForceRefreshDetails();
	}
}

void FDeadlineCloudEnvironmentDetails::OnResetHiddenParametersClicked()
{
	Settings->GetHiddenManager().ResetToDefault();
    ForceRefreshDetails();
}

EVisibility FDeadlineCloudEnvironmentDetails::GetEyeWidgetVisibility() const
{
	return ((Settings->GetHiddenManager().IsDefaultState())) ? EVisibility::Collapsed : EVisibility::Visible;
}

void FDeadlineCloudEnvironmentDetails::ForceRefreshDetails()
{
	MainDetailLayout->ForceRefreshDetails();
}

void FDeadlineCloudEnvironmentDetails::RespondToEvent()
{
	ForceRefreshDetails();
}

TSharedRef<FDeadlineCloudEnvironmentParametersMapBuilder> FDeadlineCloudEnvironmentParametersMapBuilder::MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle)
{
	TSharedRef<FDeadlineCloudEnvironmentParametersMapBuilder> Builder =
		MakeShared<FDeadlineCloudEnvironmentParametersMapBuilder>(InPropertyHandle);
	Builder->MrqJob = FDeadlineCloudDetailsWidgetsHelper::GetMrqJob(InPropertyHandle);
	return Builder;
}

FDeadlineCloudEnvironmentParametersMapBuilder::FDeadlineCloudEnvironmentParametersMapBuilder(TSharedRef<IPropertyHandle> InPropertyHandle)
	: MapProperty(InPropertyHandle->AsMap()),
	BaseProperty(InPropertyHandle)
{
	check(MapProperty.IsValid());
}

FName FDeadlineCloudEnvironmentParametersMapBuilder::GetName() const
{
	return BaseProperty->GetProperty()->GetFName();
}

void FDeadlineCloudEnvironmentParametersMapBuilder::GenerateChildContent(IDetailChildrenBuilder& InChildrenBuilder)
{
	uint32 NumChildren = 0;
	BaseProperty->GetNumChildren(NumChildren);

	EmptyCopyPasteAction = FUIAction(
		FExecuteAction::CreateLambda([]() {}),
		FCanExecuteAction::CreateLambda([]() { return false; })
	);

	for (uint32 ChildIndex = 0; ChildIndex < NumChildren; ++ChildIndex)
	{
		TSharedPtr<IPropertyHandle> ItemHandle = BaseProperty->GetChildHandle(ChildIndex);
		if (!ItemHandle.IsValid())
		{
			continue;
		}

		TSharedPtr<SWidget> CustomValueWidget = FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(ItemHandle, EValueType::STRING, EValueValidationType::EnvParameterValue);
		TSharedPtr<IPropertyHandle> KeyHandle = ItemHandle->GetKeyHandle();
		FString Name;
		KeyHandle->GetValue(Name);
		FName Tag = FName("EnvironmentParameter." + Name);
		CustomValueWidget->AddMetadata(FDriverMetaData::Id(Tag));

		const FString EnvVarPropertyPathString = ItemHandle->GeneratePathToProperty();
		const FName EnvVarPropertyPath(*EnvVarPropertyPathString);

		FDetailWidgetRow& VarItemRow = InChildrenBuilder.AddCustomRow(FText::FromString(Name));
		
		VarItemRow.NameContent()
			[
				SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(2.0f, 0.0f)
					.HAlign(HAlign_Left)
					.VAlign(VAlign_Center)
					[
						SNew(STextBlock)
						.Text(FText::FromString(Name))
					]
			];

		VarItemRow.ValueContent()
			[
				CustomValueWidget.ToSharedRef()
			];

		bool Checked = !(IsEyeWidgetEnabled(FName(Name)));
		bool isChangedByUser = !IsParameterChangedFromDefault(FName(Name));
		TSharedRef<FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox> EyeWidget = SNew(FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox, FName(Name), Checked, isChangedByUser);

		EyeWidget->SetOnCheckStateChangedDelegate(FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox::FOnCheckStateChangedDelegate::CreateSP(this, &FDeadlineCloudEnvironmentParametersMapBuilder::OnEyeHideWidgetButtonClicked));
		EyeWidget->SetVisibility((MrqJob) ? EVisibility::Hidden : EVisibility::Visible);

		VarItemRow.ExtensionContent()
			[
				EyeWidget
			];
	}
}

TSharedPtr<IPropertyHandle> FDeadlineCloudEnvironmentParametersMapBuilder::GetPropertyHandle() const
{
	return BaseProperty;
}

void FDeadlineCloudEnvironmentParametersMapBuilder::SetOnRebuildChildren(FSimpleDelegate InOnRebuildChildren)
{
	OnRebuildChildren = InOnRebuildChildren;
}

bool FDeadlineCloudEnvironmentParametersMapCustomization::IsResetToDefaultVisible(TSharedPtr<IPropertyHandle> PropertyHandle) const
{
	if (!PropertyHandle.IsValid())
	{
		return false;
	}

	auto OuterEnvironment = FDeadlineCloudDetailsWidgetsHelper::GetPropertyOuter<UDeadlineCloudEnvironment>(PropertyHandle.ToSharedRef());

	if (!IsValid(OuterEnvironment))
	{
		return false;
	}

	return !OuterEnvironment->IsDefaultVariables();
}

void FDeadlineCloudEnvironmentParametersMapCustomization::ResetToDefaultHandler(TSharedPtr<IPropertyHandle> PropertyHandle) const
{
	if (!PropertyHandle.IsValid())
	{
		return;
	}

	auto OuterEnvironment = FDeadlineCloudDetailsWidgetsHelper::GetPropertyOuter<UDeadlineCloudEnvironment>(PropertyHandle.ToSharedRef());

	if (!IsValid(OuterEnvironment))
	{
		return;
	}

	OuterEnvironment->ResetVariables();
}

void FDeadlineCloudEnvironmentParametersMapCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Variables", false);

	EmptyCopyPasteAction = FUIAction(
		FExecuteAction::CreateLambda([]() {}),
		FCanExecuteAction::CreateLambda([]() { return false; })
	);

	auto OuterEnvironment = FDeadlineCloudDetailsWidgetsHelper::GetPropertyOuter<UDeadlineCloudEnvironment>(InPropertyHandle);
	if (IsValid(OuterEnvironment))
	{
		const FResetToDefaultOverride ResetDefaultOverride = FResetToDefaultOverride::Create(
			FIsResetToDefaultVisible::CreateSP(this, &FDeadlineCloudEnvironmentParametersMapCustomization::IsResetToDefaultVisible),
			FResetToDefaultHandler::CreateSP(this, &FDeadlineCloudEnvironmentParametersMapCustomization::ResetToDefaultHandler)
		);
		InHeaderRow.OverrideResetToDefault(ResetDefaultOverride);
	}
	else
	{
		// Hide the reset to default button since it provides little value
		const FResetToDefaultOverride ResetDefaultOverride = FResetToDefaultOverride::Create(TAttribute<bool>(false));
		InHeaderRow.OverrideResetToDefault(ResetDefaultOverride);
	}

	InHeaderRow.ValueContent()
		.HAlign(HAlign_Left)
		.VAlign(VAlign_Center)
		.MinDesiredWidth(170.f)
		.MaxDesiredWidth(170.f);

	InHeaderRow.NameContent()
		[
			ArrayHandle->CreatePropertyNameWidget()
		];

	InHeaderRow.CopyAction(EmptyCopyPasteAction);
	InHeaderRow.PasteAction(EmptyCopyPasteAction);

	ArrayBuilder = FDeadlineCloudEnvironmentParametersMapBuilder::MakeInstance(ArrayHandle.ToSharedRef());
}

void FDeadlineCloudEnvironmentParametersMapCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> InPropertyHandle, IDetailChildrenBuilder& InChildBuilder, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	ArrayBuilder->MrqJob = FDeadlineCloudDetailsWidgetsHelper::GetMrqJob(InPropertyHandle);
	InChildBuilder.AddCustomBuilder(ArrayBuilder.ToSharedRef());
}

void FDeadlineCloudEnvironmentParametersMapBuilder::OnEyeHideWidgetButtonClicked(FName Property) const
{
	auto OuterEnvironment = FDeadlineCloudDetailsWidgetsHelper::GetPropertyOuter<UDeadlineCloudEnvironment>(BaseProperty);
	if (OuterEnvironment)
	{
		if (OuterEnvironment->GetHiddenManager().Contains(Property))
		{
			OuterEnvironment->GetHiddenManager().Remove(Property);
		}
		else
		{
			OuterEnvironment->GetHiddenManager().Add(Property);
		}
	}
}

bool FDeadlineCloudEnvironmentParametersMapBuilder::IsPropertyHidden(FName Parameter) const
{
	bool Contains = false;
	auto OuterEnvironment = FDeadlineCloudDetailsWidgetsHelper::GetPropertyOuter<UDeadlineCloudEnvironment>(BaseProperty);
	if (OuterEnvironment)
	{
		Contains = OuterEnvironment->GetHiddenManager().Contains(Parameter);
	}
	return Contains;
}

bool FDeadlineCloudEnvironmentParametersMapBuilder::IsEyeWidgetEnabled(FName Parameter) const
{
	bool result = false;

	if (MrqJob)
	{
		return result;
	}

	auto Env = FDeadlineCloudDetailsWidgetsHelper::GetPropertyOuter<UDeadlineCloudEnvironment>(BaseProperty);
	if (Env)
	{
		result = Env->GetHiddenManager().Contains(Parameter);
	}
	return result;
}

bool FDeadlineCloudEnvironmentParametersMapBuilder::IsParameterChangedFromDefault(FName Parameter) const
{
	auto Env = FDeadlineCloudDetailsWidgetsHelper::GetPropertyOuter<UDeadlineCloudEnvironment>(BaseProperty);
	if (!Env)
		return false;
	//for env enabled is always by user, not by default
	return Env->GetHiddenManager().IsDefaultForParameter(Parameter);
}

#undef LOCTEXT_NAMESPACE