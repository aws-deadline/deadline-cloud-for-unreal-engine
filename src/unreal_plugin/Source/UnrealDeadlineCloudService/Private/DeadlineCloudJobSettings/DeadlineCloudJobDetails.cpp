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
#include "UnrealDeadlineCloudServiceModule.h"
#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"


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
                .Padding(10)
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

TSharedRef<SWidget> FDeadlineCloudJobDetails::CreateStringWidget(FString Parameter)
{
    return  SNew(SHorizontalBox)
        + SHorizontalBox::Slot()
        .Padding(FMargin(5, 5, 5, 5))
        .AutoWidth()
        [
            SNew(SEditableTextBox)
                .Text(FText::FromString(Parameter))
        ];
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
                        [CreatePathWidget(CurrentName)];
                }
                else
                {
                    PropertiesCategory.AddCustomRow(LOCTEXT("Parameter Definitions", "Parameter Definitions"))
                        .NameContent()
                        [CreateNameWidget(CurrentName)]
                        .ValueContent()
                        [CreateStringWidget("")];
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
        UE_LOG(LogTemp, Warning, TEXT("Empty job path string"));
    }

}


#undef LOCTEXT_NAMESPACE

