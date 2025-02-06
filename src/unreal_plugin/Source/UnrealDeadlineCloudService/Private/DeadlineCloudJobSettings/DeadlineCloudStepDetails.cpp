// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudStepDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudStep.h"
#include "PropertyEditorModule.h"
#include "Modules/ModuleManager.h"
#include "DetailLayoutBuilder.h"
#include "DetailWidgetRow.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/SBoxPanel.h"
#include "DesktopPlatformModule.h"
#include "Widgets/Input/SFilePathPicker.h"
#include "IDetailChildrenBuilder.h"
#include "Widgets/Input/SNumericEntryBox.h"
#include "PythonAPILibraries/PythonParametersConsistencyChecker.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"

#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJobPresetDetailsCustomization.h"

#define LOCTEXT_NAMESPACE "StepDetails"



bool FDeadlineCloudStepDetails::CheckConsistency(UDeadlineCloudStep* Step)
{
    FParametersConsistencyCheckResult result;
    result = Step->CheckStepParametersConsistency(Step);

    UE_LOG(LogTemp, Warning, TEXT("Check consistency result: %s"), *result.Reason);
    return result.Passed;
}

void FDeadlineCloudStepDetails::OnViewAllButtonClicked()
{
    bool Show = Settings->GetDisplayHiddenParameters();
    Settings->SetDisplayHiddenParameters(!Show);
    ForceRefreshDetails();
}

void FDeadlineCloudStepDetails::OnConsistencyButtonClicked()
{
    Settings->FixStepParametersConsistency(Settings.Get());
    UE_LOG(LogTemp, Warning, TEXT("FixStepParametersConsistency"));
    ForceRefreshDetails();
}

void FDeadlineCloudStepDetails::RespondToEvent()
{
    ForceRefreshDetails();
}

void FDeadlineCloudStepDetails::ForceRefreshDetails()
{
    MainDetailLayout->ForceRefreshDetails();
}

/*Details*/
TSharedRef<IDetailCustomization> FDeadlineCloudStepDetails::MakeInstance()
{
    return MakeShareable(new FDeadlineCloudStepDetails);
}

void FDeadlineCloudStepDetails::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
    MainDetailLayout = &DetailBuilder;
    TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
    DetailBuilder.GetObjectsBeingCustomized(ObjectsBeingCustomized);
	Settings = Cast<UDeadlineCloudStep>(ObjectsBeingCustomized[0].Get());

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
						.Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudStepDetails::GetEnvironmentErrorWidgetVisibility)))
				]
				+ SHorizontalBox::Slot()
				.HAlign(HAlign_Left)
				.VAlign(VAlign_Center)
				[
					SNew(SOverlay)
						.Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudStepDetails::GetEnvironmentDefaultWidgetVisibility)))
						+ SOverlay::Slot()
						[
							OutValueWidgetEnv.ToSharedRef()
						]
				]
		];

	TSharedPtr<FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget> ConsistencyUpdateWidget;
	FParametersConsistencyCheckResult result;

	TSharedPtr<FDeadlineCloudDetailsWidgetsHelper::SEyeUpdateWidget> HiddenParametersUpdateWidget;

	/* Update all when one Parameters widget is checked as hidden */
	if (Settings.IsValid())
	{
		Settings->OnParameterHidden.BindSP(this, &FDeadlineCloudStepDetails::RespondToEvent);
	}
	/* Collapse hidden parameters array  */
	TSharedRef<IPropertyHandle> HideHandle = MainDetailLayout->GetProperty("HiddenParametersList");
	IDetailPropertyRow* HideRow = MainDetailLayout->EditDefaultProperty(HideHandle);
	HideRow->Visibility(EVisibility::Collapsed);

	/* Consistency check */
	if (Settings.IsValid() && Settings->GetStepParameters().Num() > 0)
	{
		UDeadlineCloudStep* MyObject = Settings.Get();
		bCheckConsistensyPassed = CheckConsistency(MyObject);
	}

	IDetailCategoryBuilder& PropertiesCategory = MainDetailLayout->EditCategory("Parameters");

	PropertiesCategory.AddCustomRow(FText::FromString("Consistency"))
		.Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudStepDetails::GetWidgetVisibility)))
		.WholeRowContent()
		[
			SAssignNew(ConsistencyUpdateWidget, FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget)
				.OnFixButtonClicked(FSimpleDelegate::CreateSP(this, &FDeadlineCloudStepDetails::OnConsistencyButtonClicked))
		];

	if (Settings.IsValid() && (MainDetailLayout != nullptr))
	{
		Settings->OnPathChanged = FSimpleDelegate::CreateSP(this, &FDeadlineCloudStepDetails::ForceRefreshDetails);
	};

	PropertiesCategory.AddCustomRow(FText::FromString("Visibility"))
		.Visibility(TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(this, &FDeadlineCloudStepDetails::GetEyeWidgetVisibility)))
		.WholeRowContent()
		[
			SAssignNew(HiddenParametersUpdateWidget, FDeadlineCloudDetailsWidgetsHelper::SEyeUpdateWidget)

				.OnEyeUpdateButtonClicked(FSimpleDelegate::CreateSP(this, &FDeadlineCloudStepDetails::OnViewAllButtonClicked))
				.bShowHidden_(Settings->GetDisplayHiddenParameters())
		];
}

bool FDeadlineCloudStepDetails::IsEnvironmentContainsErrors() const
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

EVisibility FDeadlineCloudStepDetails::GetEyeWidgetVisibility() const
{
	return ((Settings->AreEmptyHiddenParameters())) ? EVisibility::Collapsed : EVisibility::Visible;
}

EVisibility FDeadlineCloudStepDetails::GetEnvironmentErrorWidgetVisibility() const
{
	return IsEnvironmentContainsErrors() ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility FDeadlineCloudStepDetails::GetEnvironmentDefaultWidgetVisibility() const
{
	return IsEnvironmentContainsErrors() ? EVisibility::Collapsed : EVisibility::Visible;
}

bool FDeadlineCloudStepParametersArrayCustomization::IsEnabled(TSharedRef<IPropertyHandle> InPropertyHandle) const
{
	auto OuterStep = FDeadlineCloudStepParametersArrayBuilder::GetOuterStep(InPropertyHandle);
	return !OuterStep->TaskParameterDefinitions.Parameters.IsEmpty();
}

void FDeadlineCloudStepParametersArrayCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	const TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Parameters", false);

	ArrayBuilder = FDeadlineCloudStepParametersArrayBuilder::MakeInstance(ArrayHandle.ToSharedRef());

	auto OuterStep = FDeadlineCloudStepParametersArrayBuilder::GetOuterStep(InPropertyHandle);
	if (IsValid(OuterStep))
	{
		ArrayBuilder->OnIsEnabled.BindSP(this, &FDeadlineCloudStepParametersArrayCustomization::IsEnabled, InPropertyHandle);
	}

	//Get StepsOverride handle from TaskParametersDefinition handle and get name of RenderStep
	TSharedPtr<IPropertyHandle> ParentHandle = InPropertyHandle->GetParentHandle();
	TSharedPtr<IPropertyHandle> NameHandle = ParentHandle->GetChildHandle("Name");

	FString StepNameValue;
	NameHandle->GetValue(StepNameValue);

	ArrayBuilder->StepName = FName(StepNameValue);
	ArrayBuilder->GenerateWrapperStructHeaderRowContent(InHeaderRow, InPropertyHandle->CreatePropertyNameWidget());
}

void FDeadlineCloudStepParametersArrayCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> InPropertyHandle, IDetailChildrenBuilder& InChildBuilder, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	ArrayBuilder->MrqJob = GetMrqJob(InPropertyHandle);
	ArrayBuilder->Step = GetStep(InPropertyHandle);
	InChildBuilder.AddCustomBuilder(ArrayBuilder.ToSharedRef());
}

UMoviePipelineDeadlineCloudExecutorJob* FDeadlineCloudStepParametersArrayCustomization::GetMrqJob(TSharedRef<IPropertyHandle> Handle)
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

UDeadlineCloudStep* FDeadlineCloudStepParametersArrayCustomization::GetStep(TSharedRef<IPropertyHandle> Handle)
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
	UDeadlineCloudStep* Step = Cast<UDeadlineCloudStep>(OuterObject);
	return Step;
}

UDeadlineCloudStep* FDeadlineCloudStepParametersArrayBuilder::GetOuterStep(TSharedRef<IPropertyHandle> Handle)
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
	UDeadlineCloudStep* OuterStep = Cast<UDeadlineCloudStep>(OuterObject);
	return OuterStep;
}

TSharedRef<FDeadlineCloudStepParametersArrayBuilder> FDeadlineCloudStepParametersArrayBuilder::MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle)
{
	TSharedRef<FDeadlineCloudStepParametersArrayBuilder> Builder =
		MakeShared<FDeadlineCloudStepParametersArrayBuilder>(InPropertyHandle);

	Builder->OnGenerateArrayElementWidget(
		FOnGenerateArrayElementWidget::CreateSP(Builder, &FDeadlineCloudStepParametersArrayBuilder::OnGenerateEntry));
	return Builder;
}

FDeadlineCloudStepParametersArrayBuilder::FDeadlineCloudStepParametersArrayBuilder(TSharedRef<IPropertyHandle> InPropertyHandle)
	: FDetailArrayBuilder(InPropertyHandle, false, false, true),
	ArrayProperty(InPropertyHandle->AsArray())
{

}

void FDeadlineCloudStepParametersArrayBuilder::GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent)
{
	FDetailArrayBuilder::GenerateHeaderRowContent(NodeRow);

	EmptyCopyPasteAction = FUIAction(
		FExecuteAction::CreateLambda([]() {}),
		FCanExecuteAction::CreateLambda([]() { return false; })
	);

	NodeRow.CopyAction(EmptyCopyPasteAction);
	NodeRow.PasteAction(EmptyCopyPasteAction);

	NodeRow.OverrideResetToDefault(FResetToDefaultOverride::Create(TAttribute<bool>(false)));

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

bool FDeadlineCloudStepParametersArrayBuilder::IsResetToDefaultVisible(TSharedPtr<IPropertyHandle> PropertyHandle, FString InParameterName) const
{
	if (!PropertyHandle.IsValid())
	{
		return false;
	}

	auto OuterStep = FDeadlineCloudStepParametersArrayBuilder::GetOuterStep(PropertyHandle.ToSharedRef());
	if (!IsValid(OuterStep))
	{
		return false;
	}

	return !OuterStep->IsParameterArrayDefault(InParameterName);
}

void FDeadlineCloudStepParametersArrayBuilder::ResetToDefaultHandler(TSharedPtr<IPropertyHandle> PropertyHandle, FString InParameterName) const
{
	if (!PropertyHandle.IsValid())
	{
		return;
	}

	auto OuterStep = FDeadlineCloudStepParametersArrayBuilder::GetOuterStep(PropertyHandle.ToSharedRef());
	if (!IsValid(OuterStep))
	{
		return;
	}

	OuterStep->ResetParameterArray(InParameterName);
}

void FDeadlineCloudStepParametersArrayBuilder::OnEyeHideWidgetButtonClicked(FName Property) const
{
	if (Step)
	{
		if (Step->ContainsHiddenParameters(Property))
		{
			Step->RemoveHiddenParameters(Property);
		}
		else
		{
			Step->AddHiddenParameter(Property);
		}
	}
}

bool FDeadlineCloudStepParametersArrayBuilder::IsPropertyHidden(FName Parameter) const
{
	bool Contains = false;
	if (Step)
	{
		Contains = Step->ContainsHiddenParameters(Parameter) && (Step->GetDisplayHiddenParameters() == false);
	}
	if (MrqJob)
	{
		for (auto StepOverride : MrqJob->JobPreset->Steps)
		{
			if (StepOverride)
			{
				if (FName(StepOverride->Name) == StepName)
				{
					Contains = StepOverride->ContainsHiddenParameters(Parameter);
				}
			}
		}
	}
	return Contains;
}

UMoviePipelineDeadlineCloudExecutorJob* FDeadlineCloudStepParametersArrayBuilder::GetMrqJob(TSharedRef<IPropertyHandle> Handle)
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

void FDeadlineCloudStepParametersArrayBuilder::OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32 ElementIndex, IDetailChildrenBuilder& ChildrenBuilder) const
{
	IDetailPropertyRow& PropertyRow = ChildrenBuilder.AddProperty(ElementProperty);

	const TSharedPtr<IPropertyHandle> NameHandle = ElementProperty->GetChildHandle("Name", false);
	if (!NameHandle.IsValid())
	{
		UE_LOG(LogTemp, Error, TEXT("FDeadlineCloudStepParametersArrayBuilder Name handle is not valid"));
		return;
	}

	FString ParameterName;
	NameHandle->GetValue(ParameterName);

	auto OuterStep = FDeadlineCloudStepParametersArrayBuilder::GetOuterStep(ElementProperty);
	if (IsValid(OuterStep))
	{
		const FResetToDefaultOverride ResetDefaultOverride = FResetToDefaultOverride::Create(
			FIsResetToDefaultVisible::CreateSP(this, &FDeadlineCloudStepParametersArrayBuilder::IsResetToDefaultVisible, ParameterName),
			FResetToDefaultHandler::CreateSP(this, &FDeadlineCloudStepParametersArrayBuilder::ResetToDefaultHandler, ParameterName)
		);
		PropertyRow.OverrideResetToDefault(ResetDefaultOverride);
	}
	else
	{
		// Hide the reset to default button since it provides little value
		const FResetToDefaultOverride ResetDefaultOverride = FResetToDefaultOverride::Create(TAttribute<bool>(false));
		PropertyRow.OverrideResetToDefault(ResetDefaultOverride);
	}

	PropertyRow.ShowPropertyButtons(false);

	TSharedPtr<SWidget> NameWidget;
	TSharedPtr<SWidget> ValueWidget;

	PropertyRow.GetDefaultWidgets(NameWidget, ValueWidget);
	bool Checked = !(IsEyeWidgetEnabled(FName(ParameterName)));
	TSharedRef<FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox> EyeWidget = SNew(FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox, FName(ParameterName), Checked);

	EyeWidget->SetOnCheckStateChangedDelegate(FDeadlineCloudDetailsWidgetsHelper::SEyeCheckBox::FOnCheckStateChangedDelegate::CreateSP(this, &FDeadlineCloudStepParametersArrayBuilder::OnEyeHideWidgetButtonClicked));
	EyeWidget->SetVisibility((MrqJob) ? EVisibility::Hidden : EVisibility::Visible);

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
			ValueWidget.ToSharedRef()
		]
		.ExtensionContent()
		[
			EyeWidget
		];
	ValueWidget.ToSharedRef()->SetEnabled(
		TAttribute<bool>::CreateLambda([this, ParameterName]()
			{
				if (OnIsEnabled.IsBound())
					return OnIsEnabled.Execute();
				return true;
			})
	);

	PropertyRow.Visibility(IsPropertyHidden(FName(ParameterName)) ? EVisibility::Collapsed : EVisibility::Visible);

}

bool FDeadlineCloudStepParametersArrayBuilder::IsEyeWidgetEnabled(FName Parameter) const
{
	bool result = false;
	if (Step)
	{
		result = Step->ContainsHiddenParameters(Parameter);
	}

	if (MrqJob)
	{
		if (MrqJob->JobPreset)
		{
			for (auto StepOverride : MrqJob->JobPreset->Steps)
			{
				if (StepOverride)
				{
					if (FName(StepOverride->Name) == StepName)
					{
						result = StepOverride->ContainsHiddenParameters(Parameter);

					}
				}
			}
		}

	}
	return result;
}

TSharedRef<FDeadlineCloudStepParameterListBuilder> FDeadlineCloudStepParameterListBuilder::MakeInstance(TSharedRef<IPropertyHandle> InPropertyHandle, EValueType Type)
{
	TSharedRef<FDeadlineCloudStepParameterListBuilder> Builder =
		MakeShared<FDeadlineCloudStepParameterListBuilder>(InPropertyHandle);

	Builder->Type = Type;

	Builder->OnGenerateArrayElementWidget(
		FOnGenerateArrayElementWidget::CreateSP(Builder, &FDeadlineCloudStepParameterListBuilder::OnGenerateEntry));
	return Builder;
}

FDeadlineCloudStepParameterListBuilder::FDeadlineCloudStepParameterListBuilder(TSharedRef<IPropertyHandle> InPropertyHandle)
	: FDetailArrayBuilder(InPropertyHandle, true, false, true),
	ArrayProperty(InPropertyHandle->AsArray())
{
}

void FDeadlineCloudStepParameterListBuilder::GenerateWrapperStructHeaderRowContent(FDetailWidgetRow& NodeRow, TSharedRef<SWidget> NameContent)
{
	FDetailArrayBuilder::GenerateHeaderRowContent(NodeRow);

	EmptyCopyPasteAction = FUIAction(
		FExecuteAction::CreateLambda([]() {}),
		FCanExecuteAction::CreateLambda([]() { return false; })
	);

	NodeRow.CopyAction(EmptyCopyPasteAction);
	NodeRow.PasteAction(EmptyCopyPasteAction);

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

void FDeadlineCloudStepParameterListBuilder::OnGenerateEntry(TSharedRef<IPropertyHandle> ElementProperty, int32 ElementIndex, IDetailChildrenBuilder& ChildrenBuilder) const
{

	IDetailPropertyRow& PropertyRow = ChildrenBuilder.AddProperty(ElementProperty);

	// Hide the reset to default button since it provides little value
	const FResetToDefaultOverride ResetDefaultOverride =
		FResetToDefaultOverride::Create(TAttribute<bool>(false));

	PropertyRow.OverrideResetToDefault(ResetDefaultOverride);
	PropertyRow.ShowPropertyButtons(true);

	TSharedPtr<SWidget> NameWidget;
	TSharedPtr<SWidget> ValueWidget;


	PropertyRow.GetDefaultWidgets(NameWidget, ValueWidget);

	PropertyRow.CustomWidget(true)
		.CopyAction(EmptyCopyPasteAction)
		.PasteAction(EmptyCopyPasteAction)
		.NameContent()
		.HAlign(HAlign_Fill)
		[
			NameWidget.ToSharedRef()
		]
		.ValueContent()
		.HAlign(HAlign_Fill)
		.VAlign(VAlign_Center)
		[
			FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(ElementProperty, Type)
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

void FDeadlineCloudStepParameterListCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Range", false);

	const TSharedPtr<IPropertyHandle> TypeHandle = InPropertyHandle->GetChildHandle("Type", false);

	if (!TypeHandle.IsValid())
	{
		UE_LOG(LogTemp, Error, TEXT("FDeadlineCloudStepParameterListBuilder Type handle is not valid"));
		return;
	}

	uint8 TypeValue;
	TypeHandle->GetValue(TypeValue);

	auto Type = (EValueType)TypeValue;

	ArrayBuilder = FDeadlineCloudStepParameterListBuilder::MakeInstance(ArrayHandle.ToSharedRef(), Type);

	ArrayBuilder->GenerateWrapperStructHeaderRowContent(InHeaderRow, InPropertyHandle->CreatePropertyNameWidget());
}

void FDeadlineCloudStepParameterListCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> InPropertyHandle, IDetailChildrenBuilder& InChildBuilder, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	InChildBuilder.AddCustomBuilder(ArrayBuilder.ToSharedRef());
}

#undef LOCTEXT_NAMESPACE
