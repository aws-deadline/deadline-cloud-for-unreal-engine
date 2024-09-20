#include "DeadlineCloudJobSettings/DeadlineCloudJobDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudJob.h"
#include "PropertyEditorModule.h"
#include "Modules/ModuleManager.h"
#include "DetailLayoutBuilder.h"
#include "DetailWidgetRow.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/SBoxPanel.h"
#include "DesktopPlatformModule.h"
#include "Widgets/Input/SFilePathPicker.h"


#define LOCTEXT_NAMESPACE "JobDetails"

/*Custom file picker widget*/
class SFilePathPickerWidget : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SFilePathPickerWidget) {}
        SLATE_ARGUMENT(FString, DefaultPath) // Аргумент для пути по умолчанию

    SLATE_END_ARGS()

        void Construct(const FArguments& InArgs)
        {
            FilePath = InArgs._DefaultPath; // Получаем путь по умолчанию

            ChildSlot
                [
                    SNew(SHorizontalBox) 
                        + SHorizontalBox::Slot()
                        .AutoWidth()
                        [
                            SNew(SEditableTextBox)
                                .Text(FText::FromString(FilePath)) 
                                .OnTextChanged(this, &SFilePathPickerWidget::OnTextChanged)
                        ]

                        + SHorizontalBox::Slot()
                        .AutoWidth() 
                        [
                            SNew(SButton)
                                .Text(FText::FromString(TEXT("...")))
                                .OnClicked(this, &SFilePathPickerWidget::OnBrowseClicked)
                        ]
                ];
        }

private:
    FString FilePath;

    void OnTextChanged(const FText& NewText)
    {
        FilePath = NewText.ToString();
    }

    FReply OnBrowseClicked()
    {
        const FString DefaultPath = "";
        IDesktopPlatform* DesktopPlatform = FDesktopPlatformModule::Get();
        if (DesktopPlatform)
        {

           // FString OutPath;
            TArray<FString> OutFilenames;

            bool bOpened = DesktopPlatform->OpenFileDialog(
                nullptr,
                TEXT("Open file"),
                FPaths::ProjectContentDir(),
                TEXT(""),
                TEXT(".yaml Files"),
                EFileDialogFlags::None,
                OutFilenames
            );
           
            if (bOpened)
            {
                 FilePath = OutFilenames[0];

                 if (TSharedPtr<SEditableTextBox> TextBox = StaticCastSharedRef<SEditableTextBox>(GetChildren()->GetChildAt(0)->GetChildren()->GetChildAt(0)))

                {
                     if (TextBox.IsValid())
                     {
                         FString WidgetName = TextBox->GetTypeAsString();
                         UE_LOG(LogTemp, Log, TEXT(": %s"), *WidgetName);
                         TextBox->SetText(FText::FromString(FilePath));
                     }  

                }
            }
        }

        return FReply::Handled();
    }
};

/*Functions to construct Slate name-value widgets pair*/
TSharedRef<SWidget> FDeadlineCloudJobDetails::CreateStringValueWidget(FString Parameter)
{
    return  SNew(SHorizontalBox)
        + SHorizontalBox::Slot()
        .Padding(FMargin(5, 5, 5, 5))
        .AutoWidth()
        [
            SNew(SEditableTextBox)
                .Text(FText::FromString(""))
        ];
}

TSharedRef<SWidget> FDeadlineCloudJobDetails::CreateValuePathWidget(FString Parameter)
{
    return  SNew(SHorizontalBox)
        + SHorizontalBox::Slot()
        .Padding(FMargin(5, 5, 5, 5))
        .AutoWidth()
        [
            SNew(SFilePathPickerWidget)
                .DefaultPath("")
        ];
}

TSharedRef<SWidget> FDeadlineCloudJobDetails::CreateValuePathDefaultWidget(FString Parameter)
{
    return  SNew(SHorizontalBox)
        + SHorizontalBox::Slot()
        .Padding(FMargin(5, 5, 5, 5))
        .AutoWidth()
        [
            SNew(SFilePathPicker)

                .BrowseDirectory(TEXT("C:/"))
                .BrowseTitle(LOCTEXT("BinaryPathBrowseTitle", "File picker..."))
                .FilePath(TEXT("C:/"))
                .BrowseButtonToolTip(NSLOCTEXT("SFilePathPicker", "BrowseButtonToolTip", "Choose a file from this computer"))
                .FileTypeFilter(TEXT("All files (*.*)|*.*"))
                .IsReadOnly(false)
                .DialogReturnsFullPath(true) 
        ];
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
    if (Settings->PathToTemplate.FilePath.Len() > 0)
    {
        Parameters = Settings->OpenJobFile(Settings->PathToTemplate.FilePath);
        if (Parameters.Num() > 0) {

            IDetailCategoryBuilder& PropertiesCategory = DetailBuilder.EditCategory("DeadlineCloudJobParameters");

            for (auto& parameter : Parameters) {
                FString CurrentName = parameter.Name;
                EValueType CurrentType = parameter.Type;
                if (CurrentType == EValueType::PATH)
                {
                    PropertiesCategory.AddCustomRow(LOCTEXT("Parameter Definitions", "Parameter Definitions"))
                        .NameContent()
                        [CreateNameWidget(CurrentName)]
                        .ValueContent()
                        [CreateValuePathWidget(CurrentName)];
                }
                else
                {
                    PropertiesCategory.AddCustomRow(LOCTEXT("Parameter Definitions", "Parameter Definitions"))
                        .NameContent()
                        [CreateNameWidget(CurrentName)]
                        .ValueContent()
                        [CreateStringValueWidget(CurrentName)];
                }
   /*            switch (CurrentType)
                {
                case EValueType::STRING:                  
                    PropertiesCategory.AddCustomRow(LOCTEXT("Parameter Definitions", "Parameter Definitions"))
                        .NameContent()
                        [CreateNameWidget(CurrentName)]
                        .ValueContent()
                        [CreateStringValueWidget(CurrentName)];                
                    break;
                case EValueType::PATH:
                    UE_LOG(LogTemp, Warning, TEXT("path"));
                    PropertiesCategory.AddCustomRow(LOCTEXT("Parameter Definitions", "Parameter Definitions"))
                        .NameContent()
                        [CreateNameWidget(CurrentName)]
                        .ValueContent()
                        [CreateValuePathWidget(CurrentName)];                  
                    break;
                case EValueType::INT:               
                    break;
                case EValueType::FLOAT:
                    break;
                default:
                    UE_LOG(LogTemp, Warning, TEXT("Unknown option selected"));
                    break;
                }*/ 

            }
        }
        else
        {
            UE_LOG(LogTemp, Error, TEXT("PARAMETERS PARSING ERROR"));
        }
    }
    else
    {
        UE_LOG(LogTemp, Warning, TEXT("Empty job path string"));
    }

}


#undef LOCTEXT_NAMESPACE

