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
//#include "Widgets/Dialogs/SMessageDialog.h"
#include "Misc/MessageDialog.h"




#define LOCTEXT_NAMESPACE "JobDetails"

/* SFilePathPicker widget wrapper with selected path */

class  SFilePathWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SFilePathWidget) {}
        SLATE_ARGUMENT(FString, Path)
    SLATE_END_ARGS()
    void Construct(const FArguments& InArgs);
private:
    FString SelectedFilePath;
    FString GetSelectedFilePath() const;
    void OnPathPicked(const FString& PickedPath);
};

void SFilePathWidget::Construct(const FArguments& InArgs)
{
    SelectedFilePath = InArgs._Path;
    ChildSlot
        [
            SNew(SVerticalBox)
                + SVerticalBox::Slot()
                .Padding(5)
                [
                    SNew(SFilePathPicker)
                        .BrowseButtonImage(FAppStyle::GetBrush("PropertyWindow.Button_Ellipsis"))
                        .BrowseButtonStyle(FAppStyle::Get(), "HoverHintOnly")
                        .BrowseButtonToolTip(LOCTEXT("FileButtonToolTipText", "Choose a file from this computer"))
                        .BrowseDirectory(FEditorDirectories::Get().GetLastDirectory(ELastDirectory::GENERIC_OPEN))
                        .FilePath(this, &SFilePathWidget::GetSelectedFilePath)
                        .OnPathPicked(this, &SFilePathWidget::OnPathPicked)
                ]
        ];
}

void SFilePathWidget::OnPathPicked(const FString& PickedPath)
{
    SelectedFilePath = PickedPath;
}

FString SFilePathWidget::GetSelectedFilePath() const
{
    return SelectedFilePath;
}



/* Editable string widget to structure */

class SStringWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SStringWidget) {}
        SLATE_ARGUMENT(FParameterDefinition*, Parameter)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs)
    {
        Parameter = InArgs._Parameter;
        type = Parameter->Type;
        switch (type)
        {
        case EValueType::INT:
            EditableString = FString::FromInt(Parameter->IntValue);
            break;

        case EValueType::FLOAT:
            EditableString = FString::SanitizeFloat(Parameter->FloatValue);
            break;

        case EValueType::STRING:
            EditableString = Parameter->StringValue;
            break;
        case EValueType::PATH:
            EditableString = Parameter->PathValue;
            break;

        default:
            EditableString = "";
            break;
        }

        ChildSlot
            [
                SNew(SEditableTextBox)

                    .OnTextChanged(this, &SStringWidget::HandleTextChanged)
                    .Text(FText::FromString(EditableString))
            ];
    }

private:
    void HandleTextChanged(const FText& NewText)
    {

        EditableString = NewText.ToString();
        UE_LOG(LogTemp, Warning, TEXT("Parameter changed "), *EditableString);
        /*
        if (type == EValueType::PATH) { Parameter->PathValue = EditableString; }
        if (type == EValueType::STRING)
        {
            Parameter->ChangeParameterStringValue(EditableString);
        }
       if (type == EValueType::INT) { Parameter->IntValue = FCString::Atoi(*EditableString); }
        if (type == EValueType::FLOAT) { Parameter->IntValue = FCString::Atof(*EditableString); }
       else
        {
            Parameter->StringValue = EditableString;
        }

    */
    }
    EValueType type;
    FParameterDefinition* Parameter;
    FString EditableString;
};



TSharedRef<SWidget> FDeadlineCloudJobDetails::CreateStringWidget(FParameterDefinition* Parameter_)
{

    TSharedRef<SStringWidget> StringWidget = SNew(SStringWidget)
        .Parameter(Parameter_);
    return  StringWidget;
}

TSharedRef<SWidget> FDeadlineCloudJobDetails::CreatePathWidget(FString Parameter)
{
    TSharedRef<SFilePathWidget> PathPicker = SNew(SFilePathWidget)
        .Path(Parameter);
    return  PathPicker;
}

TSharedRef<SWidget> FDeadlineCloudJobDetails::CreateNameWidget(FString Parameter)
{
    return  SNew(SHorizontalBox)
        + SHorizontalBox::Slot()
        .Padding(FMargin(5, 5, 5, 5))
        .AutoWidth()
        [
            SNew(STextBlock)
                .Text(FText::FromString(Parameter))
        ];
};

class  SConsistencyUpdateWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SConsistencyUpdateWidget) {}
        SLATE_ARGUMENT(FString, CheckResult)
        SLATE_EVENT(FSimpleDelegate, OnFixButtonClicked)
    SLATE_END_ARGS()
    void Construct(const FArguments& InArgs) {

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

                    //update?
                    + SHorizontalBox::Slot()
                    .AutoWidth()
                    [
                        SNew(SButton)
                            .Text(FText::FromString("OK"))
                            .OnClicked(this, &SConsistencyUpdateWidget::HandleButtonClicked)
                    ]
            ];
    };


private:
    FSimpleDelegate OnFixButtonClicked;
    FReply HandleButtonClicked()
    {
        if (OnFixButtonClicked.IsBound())
        {
            OnFixButtonClicked.Execute();  // 
        }

        return FReply::Handled();
    }
};

TSharedRef<SWidget> CreateConsistencyUpdateWidget(FString ResultString)
{
    TSharedRef<SConsistencyUpdateWidget> ConsistensyWidget = SNew(SConsistencyUpdateWidget)
        .CheckResult(ResultString)
        .Visibility(EVisibility::Collapsed);
    return  ConsistensyWidget;
}

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

    TSharedPtr<SConsistencyUpdateWidget> ConsistencyUpdateWidget;
    FParametersConsistencyCheckResult result;

    /* Consistency check */
    if (Settings.IsValid())
    {
        UDeadlineCloudJob* MyObject = Settings.Get();
        CheckConsidtensyPassed = CheckConsistency(MyObject);
    }

    /* If passed - Open job file*/
    if (CheckConsidtensyPassed)
    {
        Settings->OpenJobFile(Settings->PathToTemplate.FilePath);
    }

    /* EditCategory*/
    {
        IDetailCategoryBuilder& PropertiesCategory = MyDetailLayout->EditCategory("DeadlineCloudJobParameters");
      
        PropertiesCategory.AddCustomRow(FText::FromString("Consistency"))
            .WholeRowContent()
            [
                SAssignNew(ConsistencyUpdateWidget, SConsistencyUpdateWidget)
                    .Visibility(this, &FDeadlineCloudJobDetails::GetWidgetVisibility)
                    .OnFixButtonClicked(FSimpleDelegate::CreateSP(this, &FDeadlineCloudJobDetails::OnButtonClicked))
            ];


        for (auto& parameter : Settings->GetJobParameters()) {

            EValueType CurrentType = parameter.Type;

            if (CurrentType == EValueType::PATH)
            {
                PropertiesCategory.AddCustomRow(LOCTEXT("Parameter Definitions", "Parameter Definitions"))
                    .NameContent()
                    [CreateNameWidget(parameter.Name)]
                    .ValueContent()
                    [CreatePathWidget(parameter.PathValue)];
            }
            else
            {
                PropertiesCategory.AddCustomRow(LOCTEXT("Parameter Definitions", "Parameter Definitions"))
                    .NameContent()
                    [CreateNameWidget(parameter.Name)]
                    .ValueContent()
                    [CreateStringWidget(&parameter)];
            }
        }

    }
  //  else
   // {
   //     UE_LOG(LogTemp, Error, TEXT("PARAMETERS PARSING ERROR"));
  //  }
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

void FDeadlineCloudJobDetails::OnButtonClicked()
{
    Settings->FixJobParametersConsistency(Settings.Get());
    UE_LOG(LogTemp, Warning, TEXT("FixJobParametersConsistency"));
}

#undef LOCTEXT_NAMESPACE

