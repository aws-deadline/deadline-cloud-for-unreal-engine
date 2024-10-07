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


#define LOCTEXT_NAMESPACE "JobDetails"

/* SFilePathPicker widget wrapper with selected path */

class  SFilePathWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SFilePathWidget) {}
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

private:
    FString SelectedFilePath;
    FString GetSelectedFilePath() const;
    void OnPathPicked(const FString& PickedPath);
};

void SFilePathWidget::Construct(const FArguments& InArgs)
{
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

            //  default:
              //    EditableString = "";
              //    break;
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

        //  EValueType CurrentType = Parameter->Type;


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
    TSharedRef<SFilePathWidget> PathPicker = SNew(SFilePathWidget);
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



/*Details*/
TSharedRef<IDetailCustomization> FDeadlineCloudJobDetails::MakeInstance()
{
    return MakeShareable(new FDeadlineCloudJobDetails);
}

void FDeadlineCloudJobDetails::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
    TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
    DetailBuilder.GetObjectsBeingCustomized(ObjectsBeingCustomized);
    Settings = Cast<UDeadlineCloudJob>(ObjectsBeingCustomized[0].Get());

    TSharedPtr<FDelegateHandle> Handle = MakeShared<FDelegateHandle>();

    //  Dispatcher handle remove
    { Settings->OnSomethingChanged.Remove(*Handle); }

    Settings->OpenJobFile(Settings->PathToTemplate.FilePath);


    /* Load new parameters from yaml*/
    if (Settings->GetJobParameters().Num() > 0)
    {

        IDetailCategoryBuilder& PropertiesCategory = DetailBuilder.EditCategory("DeadlineCloudJobParameters");

        for (auto& parameter : Settings->JobParameters) {

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
    else
    {
        UE_LOG(LogTemp, Error, TEXT("PARAMETERS PARSING ERROR"));
    }
    //  Dispatcher handle bind
    if (Settings.IsValid() && (&DetailBuilder) && !(Settings->OnSomethingChanged.IsBound()))
    {
        {
            *Handle = Settings->OnSomethingChanged.AddLambda([this, &DetailBuilder]()
                {
                    DetailBuilder.ForceRefreshDetails();
                });
        }
    };
}


#undef LOCTEXT_NAMESPACE

