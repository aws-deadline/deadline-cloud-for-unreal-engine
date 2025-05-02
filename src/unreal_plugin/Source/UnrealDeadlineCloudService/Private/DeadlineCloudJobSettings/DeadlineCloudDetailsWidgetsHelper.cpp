// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "DeadlineCloudJobSettings/DeadlineCloudInputValidationHelper.h"
#include "Widgets/Input/SFilePathPicker.h"
#include "DetailLayoutBuilder.h"
#include "Widgets/Input/SNumericEntryBox.h"
#include "EditorDirectories.h"
#include "Widgets/Notifications/SPopUpErrorText.h"

#define LOCTEXT_NAMESPACE "DeadlineWidgets"

/*
SDeadlineCloudFilePathWidget is a custom Slate widget class that implements a file path picker interface.
 */
class  SDeadlineCloudFilePathWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDeadlineCloudFilePathWidget) {}
        SLATE_ARGUMENT(TSharedPtr<IPropertyHandle>, PathPropertyHandle)
		SLATE_EVENT(FOnVerifyTextChanged, IsValidInput)
    SLATE_END_ARGS()
    void Construct(const FArguments& InArgs);
private:
    TSharedPtr<IPropertyHandle> PathProperty;
	FOnVerifyTextChanged IsValidInput;
	TSharedPtr<SPopupErrorText> ErrorReporting;
	bool bUpdateErrorReporting = false;

    FString GetSelectedFilePath() const;
    void OnPathPicked(const FString& PickedPath);
	EVisibility GetErrorReportingVisibility() const;
};

void SDeadlineCloudFilePathWidget::Construct(const FArguments& InArgs)
{
    PathProperty = InArgs._PathPropertyHandle;
	IsValidInput = InArgs._IsValidInput;

    ChildSlot
        [
			SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				.VAlign(VAlign_Fill)
				.HAlign(HAlign_Fill)
				.FillWidth(1)
				[
					SNew(SFilePathPicker)
						.BrowseButtonImage(FAppStyle::GetBrush("PropertyWindow.Button_Ellipsis"))
						.BrowseButtonStyle(FAppStyle::Get(), "HoverHintOnly")
						.BrowseButtonToolTip(LOCTEXT("FileButtonToolTipText", "Choose a file from this computer"))
						.BrowseDirectory(FEditorDirectories::Get().GetLastDirectory(ELastDirectory::GENERIC_OPEN))
						.BrowseTitle(LOCTEXT("PropertyEditorTitle", "File picker..."))
						.FilePath(this, &SDeadlineCloudFilePathWidget::GetSelectedFilePath)
						.OnPathPicked(this, &SDeadlineCloudFilePathWidget::OnPathPicked)
				]
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(3, 0)
				[
					SAssignNew(ErrorReporting, SPopupErrorText)
						.Visibility(TAttribute<EVisibility>::Create(
							TAttribute<EVisibility>::FGetter::CreateSP(this, &SDeadlineCloudFilePathWidget::GetErrorReportingVisibility)))
				]
		];

	if (IsValidInput.IsBound())
	{
		FText OutError = FText::GetEmpty();
		IsValidInput.Execute(FText::FromString(GetSelectedFilePath()), OutError);
		ErrorReporting->SetError(OutError);
	}
}

EVisibility SDeadlineCloudFilePathWidget::GetErrorReportingVisibility() const
{
	if (ErrorReporting.IsValid())
	{
		return ErrorReporting->HasError() ? EVisibility::Visible : EVisibility::Hidden;
	}
	return EVisibility::Collapsed;
}

void SDeadlineCloudFilePathWidget::OnPathPicked(const FString& PickedPath)
{
	FPropertyAccess::Result PathResult = PathProperty->SetValue(PickedPath);

	if (PathResult != FPropertyAccess::Success)
	{
		UE_LOG(LogTemp, Error, TEXT("SetValue failed! Result: %d"), static_cast<int32>(PathResult));
	}

	bUpdateErrorReporting = true;
}

FString SDeadlineCloudFilePathWidget::GetSelectedFilePath() const
{
	FString FilePath;
	PathProperty->GetValue(FilePath);

	if (ErrorReporting.IsValid() && IsValidInput.IsBound() && bUpdateErrorReporting)
	{
		FText Error = FText::GetEmpty();

		IsValidInput.Execute(FText::FromString(FilePath), Error);
		ErrorReporting->SetError(Error);
	}

	return FilePath;
}
/*
SDeadlineCloudStringWidget is a custom Slate widget that creates an editable text box for string properties.
It handles the display and editing of string values through a property handle.
*/
class SDeadlineCloudStringWidget : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SDeadlineCloudStringWidget) {}
		SLATE_ARGUMENT(TSharedPtr<IPropertyHandle>, StringPropertyHandle)
		SLATE_EVENT(FOnVerifyTextChanged, IsValidInput)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs)
	{
		StringProperty = InArgs._StringPropertyHandle;
		IsValidInput = InArgs._IsValidInput;
		ChildSlot
			[
				SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.VAlign(VAlign_Center)
					[
						SAssignNew(TextBox, SEditableTextBox)
							.Font(IDetailLayoutBuilder::GetDetailFont())
							.Text(this, &SDeadlineCloudStringWidget::GetText)
							.OnTextCommitted(this, &SDeadlineCloudStringWidget::OnTextCommitted)
							.OnTextChanged(this, &SDeadlineCloudStringWidget::OnTextChanged)
					]
			];

		if (IsValidInput.IsBound())
		{
			Error = FText::GetEmpty();
			IsValidInput.Execute(GetText(), Error);
			TextBox->SetError(Error);
		}
	}

private:

	void OnTextChanged(const FText& InText)
	{
		if (IsValidInput.IsBound())
		{
			Error = FText::GetEmpty();
			IsValidInput.Execute(InText, Error);
			TextBox->SetError(Error);
		}
	}

	void OnTextCommitted(const FText& InText, ETextCommit::Type InCommitType)
	{
		if (!Error.IsEmpty())
		{
			Error = FText::GetEmpty();
			TextBox->SetError(Error);
			return;
		}

		StringProperty->SetValue(InText.ToString());
	}

	FText GetText() const
	{
		FString String;
		StringProperty->GetValue(String);

		return FText::FromString(String);
	}

	TSharedPtr<IPropertyHandle> StringProperty;
	TSharedPtr<SEditableTextBox> TextBox;
	FOnVerifyTextChanged IsValidInput;
	FText Error;
};
/*
SDeadlineCloudIntWidget is a custom Slate widget for integer input fields.
It wraps a SNumericEntryBox that converts between string-based input and integer display/editing.
*/
class SDeadlineCloudIntWidget : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SDeadlineCloudIntWidget) {}
		SLATE_ARGUMENT(TSharedPtr<IPropertyHandle>, PropertyHandle)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs)
	{
		Property = InArgs._PropertyHandle;

		ChildSlot
			[
				SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.VAlign(VAlign_Center)
					[
						SNew(SNumericEntryBox<int32>)
							.Font(IDetailLayoutBuilder::GetDetailFont())
							.AllowSpin(false)
							.MinDesiredValueWidth(50.0f)
							.Value_Lambda([this]
								{
									FString String;
									Property->GetValue(String);
									return FCString::Atoi(*String);
								})
							.OnValueCommitted_Lambda([this](int32 Value, ETextCommit::Type)
								{
									Property->SetValue(FString::FromInt(Value));
								})
					]
			];
	}

private:

	TSharedPtr<IPropertyHandle> Property;
};
/*
SDeadlineCloudFloatWidget is a custom Slate widget for float input fields.
*/
class SDeadlineCloudFloatWidget : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SDeadlineCloudFloatWidget) {}
		SLATE_ARGUMENT(TSharedPtr<IPropertyHandle>, PropertyHandle)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs)
	{
		Property = InArgs._PropertyHandle;

		ChildSlot
			[
				SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.VAlign(VAlign_Center)
					[
						SNew(SNumericEntryBox<double>)
							.Font(IDetailLayoutBuilder::GetDetailFont())
							.AllowSpin(false)
							.MinDesiredValueWidth(50.0f)
							.Value_Lambda([this]
								{
									FString String;
									Property->GetValue(String);

									return FCString::Atod(*String);
								})
							.OnValueCommitted_Lambda([this](double Value, ETextCommit::Type)
								{
									Property->SetValue(FString::SanitizeFloat(Value));
								})
					]
			];
	}

private:

	TSharedPtr<IPropertyHandle> Property;
};
/*
SConsistencyWidget shows consistency check result for Deadline Job|Step|Environment parameters and same parameters loaded from .yaml for consistency check.
A part of parameter consistency checking system in a Deadline Cloud plugin, where it notifies users of parameter changes and provides a way to update them.
*/
void FDeadlineCloudDetailsWidgetsHelper::SConsistencyWidget::Construct(const FArguments& InArgs) {

	OnFixButtonClicked = InArgs._OnFixButtonClicked;

	ChildSlot
		[
			SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(5)
				[
					SNew(STextBlock)
						.Text(FText::FromString("Parameters changed. Update parameters?"))
						.ColorAndOpacity(FLinearColor::Yellow) //
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SButton)
						.Text(FText::FromString("OK"))
						.OnClicked(this, &SConsistencyWidget::HandleButtonClicked)
				]
		];
};
/*
SEyeUpdateWidget shows that some Deadline Job|Step|Environment parameters will be hidden in MRQ tab.
SEyeUpdateWidget makes these parameters visible/hidden to user in Deadline Job|Step|Environment widget.
*/
void FDeadlineCloudDetailsWidgetsHelper::SEyeUpdateWidget::Construct(const FArguments& InArgs) {

	OnEyeUpdateButtonClicked = InArgs._OnEyeUpdateButtonClicked;
	bShowHidden = InArgs._bShowHidden_;

	ChildSlot
		[
			SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(5)
				[
					SNew(STextBlock)
						.Text(FText::FromString("Some parameters will be hidden in MRQ. "))
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(5)
				[
					SNew(SButton)
						.OnClicked(this, &SEyeUpdateWidget::HandleButtonClicked)
						.Text(this, &SEyeUpdateWidget::GetButtonText)
				]
		];
};


TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(TSharedPtr<IPropertyHandle> ParameterHandle, EValueType Type, EValueValidationType ValidationType)
{

	switch (Type)
	{
		using enum EValueType;
	case EValueType::STRING:
	{
		FOnVerifyTextChanged Validation = FDeadlineCloudInputValidationHelper::GetStringValidationFunction(ValidationType);
		return CreateStringWidget(ParameterHandle, Validation);
	}
	case EValueType::PATH:
	{
		FOnVerifyTextChanged Validation = FDeadlineCloudInputValidationHelper::GetPathValidationFunction(ValidationType);
		return CreatePathWidget(ParameterHandle, Validation);
	}
	case EValueType::INT:
	{
		return CreateIntWidget(ParameterHandle);
	}
	case EValueType::FLOAT:
	{
		return CreateFloatWidget(ParameterHandle);
	}
	default:
	{
		UE_LOG(LogTemp, Error, TEXT("CreatePropertyWidgetByType : Unknown type"));
		break;
	}
	}

	return SNullWidget::NullWidget;
}

TSharedPtr<SWidget> FDeadlineCloudDetailsWidgetsHelper::TryCreatePropertyWidgetFromMetadata(TSharedPtr<IPropertyHandle> ParameterHandle)
{
	if (!ParameterHandle.IsValid())
	{
		return nullptr;
	}

	FString TypeString;
	FString ValidationTypeString;

    if (const FString* CustomWidget = ParameterHandle->GetProperty()->FindMetaData(TEXT("CustomWidgetType")))
    {
		FString CustomWidgetName(*CustomWidget);
        UEnum* EnumPtr = StaticEnum<EValueType>();
		if (EnumPtr)
		{
			const int32 EnumValue = EnumPtr->GetValueByName(FName(*CustomWidgetName));
			if (EnumValue != INDEX_NONE)
			{
				EValueValidationType ValidationType = EValueValidationType::Default;

				if (const FString* Validation = ParameterHandle->GetProperty()->FindMetaData(TEXT("ValidationType")))
				{
					FString ValidationString(*Validation);
					UEnum* EnumValueType = StaticEnum<EValueValidationType>();
                    if (EnumValueType)
					{
						const int32 EnumValidationValue = EnumValueType->GetValueByName(FName(*ValidationString));
						if (EnumValidationValue != INDEX_NONE)
                        {
							ValidationType = EValueValidationType(EnumValidationValue);
						}
					}
				}

				return FDeadlineCloudDetailsWidgetsHelper::CreatePropertyWidgetByType(
					ParameterHandle, EValueType(EnumValue), ValidationType);
			}
		}
    }

	return nullptr;
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateNameWidget(FString Parameter)
{
	return  SNew(SHorizontalBox)
		+ SHorizontalBox::Slot()
		.Padding(FMargin(0.0f, 1.0f, 0.0f, 1.0f))
		.FillWidth(1)
		[
			SNew(STextBlock)
				.Text(FText::FromString(Parameter))
				.Font(IDetailLayoutBuilder::GetDetailFont())
				.ColorAndOpacity(FSlateColor::UseForeground())
		];
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateConsistencyWidget(FString ResultString)
{
	TSharedRef<SConsistencyWidget> ConsistensyWidget = SNew(SConsistencyWidget)
		.CheckResult(ResultString)
		.Visibility(EVisibility::Collapsed);
	return  ConsistensyWidget;
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateEyeUpdateWidget()
{
	TSharedRef<SEyeUpdateWidget> EyeUpdateWidget = SNew(SEyeUpdateWidget)
		.Visibility(EVisibility::Collapsed);
	return  EyeUpdateWidget;
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreatePathWidget(TSharedPtr<IPropertyHandle> ParameterHandle, FOnVerifyTextChanged Validation)
{
	return SNew(SDeadlineCloudFilePathWidget)
		.PathPropertyHandle(ParameterHandle)
		.IsValidInput(Validation);
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateIntWidget(TSharedPtr<IPropertyHandle> ParameterHandle)
{
	return SNew(SDeadlineCloudIntWidget)
		.PropertyHandle(ParameterHandle);
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateFloatWidget(TSharedPtr<IPropertyHandle> ParameterHandle)
{
	return SNew(SDeadlineCloudFloatWidget)
		.PropertyHandle(ParameterHandle);
}

TSharedRef<SWidget> FDeadlineCloudDetailsWidgetsHelper::CreateStringWidget(TSharedPtr<IPropertyHandle> ParameterHandle, FOnVerifyTextChanged Validation)
{
	return SNew(SDeadlineCloudStringWidget)
		.StringPropertyHandle(ParameterHandle)
		.IsValidInput(Validation);
}


#undef LOCTEXT_NAMESPACE