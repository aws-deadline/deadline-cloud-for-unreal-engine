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


#define LOCTEXT_NAMESPACE "StepDetails"

//TODO: widgets library

class  SFileStepPathWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SFileStepPathWidget) {}
        SLATE_ARGUMENT(FString, Path)
    SLATE_END_ARGS()
    void Construct(const FArguments& InArgs);
private:
    FString SelectedFilePath;
    FString GetSelectedFilePath() const;
    void OnPathPicked(const FString& PickedPath);
};

void SFileStepPathWidget::Construct(const FArguments& InArgs)
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
                        .FilePath(this, &SFileStepPathWidget::GetSelectedFilePath)
                        .OnPathPicked(this, &SFileStepPathWidget::OnPathPicked)
                ]
        ];
}

void SFileStepPathWidget::OnPathPicked(const FString& PickedPath)
{
    SelectedFilePath = PickedPath;
}

FString SFileStepPathWidget::GetSelectedFilePath() const
{
    return SelectedFilePath;
}



/* Editable string widget to structure */
/*
class SStepStringWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SStepStringWidget) {}
        SLATE_ARGUMENT(FStepTaskParameterDefinition*, Parameter)
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

                    .OnTextChanged(this, &SStepStringWidget::HandleTextChanged)
                    .Text(FText::FromString(EditableString))
            ];
    }

private:
    void HandleTextChanged(const FText& NewText)
    {

        EditableString = NewText.ToString();
        UE_LOG(LogTemp, Warning, TEXT("Parameter changed "), *EditableString);

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


    }
    EValueType type;
    FStepTaskParameterDefinition* Parameter;
    FString EditableString;
};*/


/*
TSharedRef<SWidget> FDeadlineCloudStepDetails::CreateStepStringWidget(FStepTaskParameterDefinition* Parameter_)
{

    TSharedRef<SStepStringWidget> StringWidget = SNew(SStepStringWidget)
        .Parameter(Parameter_);
    return  StringWidget;
}*/

TSharedRef<SWidget> FDeadlineCloudStepDetails::CreateStepPathWidget(FString Parameter)
{
    TSharedRef<SFileStepPathWidget> PathPicker = SNew(SFileStepPathWidget)
        .Path(Parameter);
    return  PathPicker;
}

TSharedRef<SWidget> FDeadlineCloudStepDetails::CreateStepNameWidget(FString Parameter)
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



TSharedRef<SWidget> FDeadlineCloudStepDetails::GenerateStringsArrayContent(const TArray<FString>& StringArray)
{

    TSharedRef<SVerticalBox> VBox = SNew(SVerticalBox);
    if (StringArray.Num() > 0)
    {
        for (const FString& Str : StringArray)
        {
            VBox->AddSlot()
                .AutoHeight()
                .Padding(5)
                [
                    SNew(SEditableTextBox)
                        .Text(FText::FromString(Str))
                ];
        }
    }

    return VBox;
}

TSharedRef<SWidget> FDeadlineCloudStepDetails::GenerateTasksContent(const TArray<FStepTaskParameterDefinition> tasks)
{

    TSharedRef<SVerticalBox> VBox = SNew(SVerticalBox);
    if (tasks.Num() > 0)
    {
        for (auto& task : tasks)
        {
            VBox->AddSlot()
                .AutoHeight()
                .HAlign(HAlign_Fill)
                .Padding(2)
                [
                    SNew(SHorizontalBox)

                        + SHorizontalBox::Slot()
                        .AutoWidth()
                        .VAlign(VAlign_Top)
                        .Padding(2)
                        [
                            SNew(STextBlock)
                                .Text(FText::FromString(task.Name))
                        ]

                        + SHorizontalBox::Slot()
                        //.FillWidth(1.0f)
                        .VAlign(VAlign_Top)
                        .Padding(2)
                        [
                            SNew(SEditableTextBox)
                                .Text(FText::FromString(""))
                        ]

                        + SHorizontalBox::Slot()
                        .AutoWidth()
                        .VAlign(VAlign_Top)
                        .Padding(2)
                        [
                            SNew(SVerticalBox)
                                + SVerticalBox::Slot()
                                .AutoHeight()
                                [
                                    this->GenerateStringsArrayContent(task.Range)
                                ]
                        ]
                ];
        }
    }

    return VBox;
}

/*Details*/
TSharedRef<IDetailCustomization> FDeadlineCloudStepDetails::MakeInstance()
{
    return MakeShareable(new FDeadlineCloudStepDetails);
}

void FDeadlineCloudStepDetails::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{

    TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
    DetailBuilder.GetObjectsBeingCustomized(ObjectsBeingCustomized);
    Settings = Cast<UDeadlineCloudStep>(ObjectsBeingCustomized[0].Get());

    FString CurrentName;

    if (Settings->PathToTemplate.FilePath.Len() > 0)
    {
        TArray <FStepTaskParameterDefinition> Parameters;
        Settings->OpenStepFile(Settings->PathToTemplate.FilePath);
        Parameters = Settings->GetStepParameters();
        if (Parameters.Num() > 0) {

            IDetailCategoryBuilder& PropertiesCategory = DetailBuilder.EditCategory("DeadlineCloudStepParameters");

            for (auto& StepParameter : Parameters) {

                CurrentName = StepParameter.Name;

                {
                    PropertiesCategory.AddCustomRow(LOCTEXT("Parameter Definitions", "Parameter Definitions"))
                        .NameContent()
                        [CreateStepNameWidget(StepParameter.Name)]
                        .ValueContent()
                        [GenerateStringsArrayContent(StepParameter.Range)];
                }

            }
        }
        else
        {
            UE_LOG(LogTemp, Error, TEXT("PARAMETERS PARSING ERROR"));
        }
    }

    else
    {
        UE_LOG(LogTemp, Warning, TEXT("Empty step path string"));
    }

}


#undef LOCTEXT_NAMESPACE