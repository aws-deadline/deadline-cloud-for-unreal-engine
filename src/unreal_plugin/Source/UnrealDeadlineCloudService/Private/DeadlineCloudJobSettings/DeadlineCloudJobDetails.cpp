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

    /* If passed - Open job file*/
    if (bCheckConsistensyPassed || Settings->GetJobParameters().Num() == 0)
    {
        Settings->OpenJobFile(Settings->PathToTemplate.FilePath);
    }

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
        {
            Settings->OnSomethingChanged = FSimpleDelegate::CreateSP(this, &FDeadlineCloudJobDetails::ForceRefreshDetails);
        }
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
       
    UE_LOG(LogTemp, Warning, TEXT("check consistency result: %s"), *result.Reason);
    return result.Passed;
}

EVisibility FDeadlineCloudJobDetails::GetConsistencyWidgetVisibility() const
{
		return (!bCheckConsistensyPassed) ? EVisibility::Visible : EVisibility::Collapsed;
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
	.HAlign( HAlign_Left )
	.VAlign( VAlign_Center )
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

	EValueType Type = (EValueType)TypeValue;


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
			FIsResetToDefaultVisible::CreateSPLambda(this, [this, OuterJob, ParameterName](TSharedPtr<IPropertyHandle> PropertyHandle)->bool
                {
                    if (!PropertyHandle.IsValid())
                    {
                        return false;
                    }

					if (!IsValid(OuterJob))
					{
                        return false;
					}

					FString DefaultValue = OuterJob->GetDefaultParameterValue(ParameterName);
					FString CurrentValue;
					PropertyHandle->GetValue(CurrentValue);

                    return !CurrentValue.Equals(DefaultValue);
                }),
            FResetToDefaultHandler::CreateSPLambda(this, [this, ParameterName, OuterJob](TSharedPtr<IPropertyHandle> PropertyHandle)
                {
                    if (!PropertyHandle.IsValid())
                    {
                        return;
                    }

					if (!IsValid(OuterJob))
					{
                        return;
					}

					FString DefaultValue = OuterJob->GetDefaultParameterValue(ParameterName);
					PropertyHandle->SetValue(DefaultValue);
                })
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

	PropertyRow.GetDefaultWidgets( NameWidget, ValueWidget);

	PropertyRow.CustomWidget(true)
	.CopyAction(EmptyCopyPasteAction)
	.PasteAction(EmptyCopyPasteAction)
	.NameContent()
	.HAlign(HAlign_Fill)
	[
        SNew(SHorizontalBox)
            + SHorizontalBox::Slot()
		    .Padding( FMargin( 0.0f, 1.0f, 0.0f, 1.0f) )
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
		FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(ValueHandle, Type)
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

void FDeadlineCloudJobParametersArrayCustomization::CustomizeHeader(TSharedRef<IPropertyHandle> InPropertyHandle, FDetailWidgetRow& InHeaderRow, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
    TSharedPtr<IPropertyHandle> ArrayHandle = InPropertyHandle->GetChildHandle("Parameters", false);

	ArrayBuilder = FDeadlineCloudJobParametersArrayBuilder::MakeInstance(ArrayHandle.ToSharedRef());

    ArrayBuilder->GenerateWrapperStructHeaderRowContent(InHeaderRow, InPropertyHandle->CreatePropertyNameWidget());
}

void FDeadlineCloudJobParametersArrayCustomization::CustomizeChildren(TSharedRef<IPropertyHandle> InPropertyHandle, IDetailChildrenBuilder& InChildBuilder, IPropertyTypeCustomizationUtils& InCustomizationUtils)
{
	InChildBuilder.AddCustomBuilder(ArrayBuilder.ToSharedRef());
}

#undef LOCTEXT_NAMESPACE