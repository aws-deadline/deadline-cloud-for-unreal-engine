// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudDetailsWidgetsHelper.h"
#include "DeadlineCloudJobSettings/DeadlineCloudInputValidationHelper.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "Widgets/Input/SFilePathPicker.h"
#include "DetailLayoutBuilder.h"
#include "Widgets/Input/SNumericEntryBox.h"
#include "EditorDirectories.h"
#include "Widgets/Notifications/SPopUpErrorText.h"
#include "DesktopPlatformModule.h"

#define LOCTEXT_NAMESPACE "DeadlineWidgets"

/*
SDeadlineCloudFilePathWidget is a custom Slate widget class that implements a file path picker interface.
 */
class  SDeadlineCloudFilePathWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDeadlineCloudFilePathWidget) 
		: _BrowseButtonToolTip(LOCTEXT("BrowseButtonToolTip", "Choose a file from this computer"))
		, _FileTypeFilter(TEXT("All files (*.*)|*.*"))
		, _Font()
		, _IsReadOnly(false)
		, _DialogReturnsFullPath(false)
		{}
		/** The property handle for the file path. */
        SLATE_ARGUMENT(TSharedPtr<IPropertyHandle>, PathPropertyHandle)

		/** The function to call when the text is changed. */
		SLATE_EVENT(FOnVerifyTextChanged, IsValidInput)

		/** Browse button image resource. */
		SLATE_ATTRIBUTE(const FSlateBrush*, BrowseButtonImage)

		/** Browse button visual style. */
		SLATE_STYLE_ARGUMENT(FButtonStyle, BrowseButtonStyle)

		/** Browse button tool tip text. */
		SLATE_ATTRIBUTE(FText, BrowseButtonToolTip)

		/** The directory to browse by default */
		SLATE_ATTRIBUTE(FString, BrowseDirectory)

		/** Title for the browse dialog window. */
		SLATE_ATTRIBUTE(FText, BrowseTitle)

		/** The currently selected file path. */
		SLATE_ATTRIBUTE(FString, FilePath)

		/** File type filter string. */
		SLATE_ATTRIBUTE(FString, FileTypeFilter)

		/** Font color and opacity of the path text box. */
		SLATE_ATTRIBUTE(FSlateFontInfo, Font)

		/** Whether the path text box can be modified by the user. */
		SLATE_ATTRIBUTE(bool, IsReadOnly)

		/** Whether the path returned by the dialog should be converted from relative to full */
		SLATE_ATTRIBUTE(bool, DialogReturnsFullPath)

    SLATE_END_ARGS()
    void Construct(const FArguments& InArgs);
private:
    TSharedPtr<IPropertyHandle> PathProperty;
	FOnVerifyTextChanged IsValidInput;

	/** Holds the directory path to browse by default. */
	TAttribute<FString> BrowseDirectory;

	/** Holds the title for the browse dialog window. */
	TAttribute<FText> BrowseTitle;

	/** Holds the currently selected file path. */
	TAttribute<FString> FilePath;

	/** Holds the file type filter string. */
	TAttribute<FString> FileTypeFilter;

	/** Holds the editable text box. */
	TSharedPtr<SEditableTextBox> TextBox;

	/** Holds the option for the dialog to return full path instead of relative. */
	TAttribute<bool> DialogReturnsFullPath;
    FString GetSelectedFilePath() const;

    void OnPathPickedFromDialog(const FString& PickedPath);
    void OnPathPicked(const FString& PickedPath);

	void OnTextChanged(const FText& InText);
	/** Callback for clicking the browse button. */
	FReply HandleBrowseButtonClicked( );

	/** Callback for getting the text in the path text box. */
	FText HandleTextBoxText( ) const;

	/** Callback for committing the text in the path text box. */
	void HandleTextBoxTextCommitted( const FText& NewText, ETextCommit::Type /*CommitInfo*/ );

	void HandleExternalPathPropertyChanged();
};

void SDeadlineCloudFilePathWidget::Construct(const FArguments& InArgs)
{
	BrowseDirectory = InArgs._BrowseDirectory;
	BrowseTitle = InArgs._BrowseTitle;
	FilePath = InArgs._FilePath;
	FileTypeFilter = InArgs._FileTypeFilter;
	DialogReturnsFullPath = InArgs._DialogReturnsFullPath;
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
					SNew(SHorizontalBox)

					+ SHorizontalBox::Slot()
						.FillWidth(1.0f)
						.VAlign(VAlign_Center)
						[
							SAssignNew(TextBox, SEditableTextBox)
								.Text(HandleTextBoxText())
								.Font(InArgs._Font)
								.SelectAllTextWhenFocused(true)
								.ClearKeyboardFocusOnCommit(true)
								.OnTextCommitted(this, &SDeadlineCloudFilePathWidget::HandleTextBoxTextCommitted)
								.OnTextChanged(this, &SDeadlineCloudFilePathWidget::OnTextChanged)
								.SelectAllTextOnCommit(false)
								.IsReadOnly(InArgs._IsReadOnly)
						]

					+ SHorizontalBox::Slot()
						.AutoWidth()
						.Padding(4.0f, 0.0f, 0.0f, 0.0f)
						.VAlign(VAlign_Center)
						[
							SNew(SButton)
								.ButtonStyle(InArgs._BrowseButtonStyle)
								.ToolTipText(InArgs._BrowseButtonToolTip)
								.OnClicked(this, &SDeadlineCloudFilePathWidget::HandleBrowseButtonClicked)
								.ContentPadding(2.0f)
								.ForegroundColor(FSlateColor::UseForeground())
								.IsFocusable(false)
								[
									SNew(SImage)
										.Image(InArgs._BrowseButtonImage)
										.ColorAndOpacity(FSlateColor::UseForeground())
								]
						]
				]
		];

	if (IsValidInput.IsBound())
	{
		FText OutError = FText::GetEmpty();
		IsValidInput.Execute(FText::FromString(GetSelectedFilePath()), OutError);
		TextBox->SetError(OutError);
	}

	if (PathProperty.IsValid())
	{
		PathProperty->SetOnPropertyValueChanged(FSimpleDelegate::CreateSP(this, &SDeadlineCloudFilePathWidget::HandleExternalPathPropertyChanged));
	}
}

void SDeadlineCloudFilePathWidget::HandleExternalPathPropertyChanged()
{
	FString NewPath;
	if (PathProperty->GetValue(NewPath) == FPropertyAccess::Success)
	{
		TextBox->SetText(FText::FromString(NewPath));
	}
}

FReply SDeadlineCloudFilePathWidget::HandleBrowseButtonClicked()
{
	IDesktopPlatform* DesktopPlatform = FDesktopPlatformModule::Get();

	if (DesktopPlatform == nullptr)
	{
		return FReply::Handled();
	}

	const FString DefaultPath = BrowseDirectory.IsSet()
		? BrowseDirectory.Get()
		: FPaths::GetPath(GetSelectedFilePath());

	TSharedPtr<SWindow> ParentWindow = FSlateApplication::Get().FindWidgetWindow(AsShared());
	void* ParentWindowHandle = (ParentWindow.IsValid() && ParentWindow->GetNativeWindow().IsValid())
		? ParentWindow->GetNativeWindow()->GetOSWindowHandle()
		: nullptr;

	TArray<FString> OutFiles;

	if (DesktopPlatform->OpenFileDialog(ParentWindowHandle, BrowseTitle.Get().ToString(), DefaultPath, TEXT(""), FileTypeFilter.Get(), EFileDialogFlags::None, OutFiles))
	{
		if (DialogReturnsFullPath.Get())
		{
			OnPathPickedFromDialog(FPaths::ConvertRelativePathToFull(OutFiles[0]));
		}
		else
		{
			OnPathPickedFromDialog(OutFiles[0]);
		}
	}

	return FReply::Handled();
}

FText SDeadlineCloudFilePathWidget::HandleTextBoxText() const
{
	return FText::FromString(GetSelectedFilePath());
}

void SDeadlineCloudFilePathWidget::OnTextChanged(const FText& InText)
{
	if (IsValidInput.IsBound())
	{
		FText Error = FText::GetEmpty();
		IsValidInput.Execute(InText, Error);
		TextBox->SetError(Error);
	}

	TextBox->SetText(InText);
}

void SDeadlineCloudFilePathWidget::HandleTextBoxTextCommitted(const FText& NewText, ETextCommit::Type CommitInfo)
{
	if (IsValidInput.IsBound())
	{
		FText Error = FText::GetEmpty();
		IsValidInput.Execute(NewText, Error);

		if (!Error.IsEmpty())
		{
			TextBox->SetText(HandleTextBoxText());
		}
		else
		{
			OnPathPicked(NewText.ToString());
		}
		TextBox->SetError(FText::GetEmpty());
	}
	else
	{
		OnPathPicked(NewText.ToString());
	}
}

void SDeadlineCloudFilePathWidget::OnPathPickedFromDialog(const FString& PickedPath)
{
	if (IsValidInput.IsBound())
	{
		FText Error = FText::GetEmpty();
		IsValidInput.Execute(FText::FromString(PickedPath), Error);
		TextBox->SetError(Error);
	}

	OnPathPicked(PickedPath);
}

void SDeadlineCloudFilePathWidget::OnPathPicked(const FString& PickedPath)
{
	FPropertyAccess::Result PathResult = PathProperty->SetValue(PickedPath);

	if (PathResult != FPropertyAccess::Success)
	{
		UE_LOG(LogTemp, Error, TEXT("SetValue failed! Result: %d"), static_cast<int32>(PathResult));
	}
}

FString SDeadlineCloudFilePathWidget::GetSelectedFilePath() const
{
	FString PropertyFilePath;
	PathProperty->GetValue(PropertyFilePath);

	return PropertyFilePath;
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
		if (IsValidInput.IsBound())
		{
			Error = FText::GetEmpty();
			IsValidInput.Execute(InText, Error);
			if (Error.IsEmpty())
			{
				StringProperty->SetValue(InText.ToString());
			}
			else
			{
				TextBox->SetText(GetText());
			}

			TextBox->SetError(FText::GetEmpty());
		}
		else
		{
			StringProperty->SetValue(InText.ToString());
		}
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

	ChildSlot
		[
			SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				.Padding(5)
				[
					SNew(STextBlock)
						.Text(FText::FromString("Visibility parameters have been changed by the user, restore default values?"))
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
		.IsValidInput(Validation)
		.BrowseButtonImage(FAppStyle::GetBrush("PropertyWindow.Button_Ellipsis"))
		.BrowseButtonStyle(FAppStyle::Get(), "HoverHintOnly")
		.BrowseButtonToolTip(LOCTEXT("FileButtonToolTipText", "Choose a file from this computer"))
		.BrowseDirectory(FEditorDirectories::Get().GetLastDirectory(ELastDirectory::GENERIC_OPEN))
		.BrowseTitle(LOCTEXT("PropertyEditorTitle", "File picker..."));
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

UMoviePipelineDeadlineCloudExecutorJob* FDeadlineCloudDetailsWidgetsHelper::GetMrqJob(TSharedRef<IPropertyHandle> Handle)
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
	if (MrqJob)
	{
		return MrqJob;
	}
	else return nullptr;
}


#undef LOCTEXT_NAMESPACE