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

void FDeadlineCloudJobDetails::SetCurrentFilePath(const FString& PickedPath)
{
        CurrentFilePath = PickedPath;
}

FString FDeadlineCloudJobDetails::GetCurrentFilePath() const
{
    return CurrentFilePath;
}

/*Functions to construct Slate name-value widgets pair*/
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
    TSharedRef<SFilePathPicker> PPicker = SNew(SFilePathPicker)
        .BrowseButtonImage(FAppStyle::GetBrush("PropertyWindow.Button_Ellipsis"))

        .BrowseButtonStyle(FAppStyle::Get(), "HoverHintOnly")
        .BrowseButtonToolTip(LOCTEXT("FileButtonToolTipText", "Choose a file from this computer"))
        .BrowseDirectory(FEditorDirectories::Get().GetLastDirectory(ELastDirectory::GENERIC_OPEN))
        .BrowseTitle(LOCTEXT("OpenFile", "OpenFile"));

 
       // .FilePath(this, &FDeadlineCloudJobDetails::GetCurrentFilePath)
       // .OnPathPicked(this, &FDeadlineCloudJobDetails::OnCurrentPathPicked);


        return  PPicker;

}

void FDeadlineCloudJobDetails::OnCurrentPathPicked(const FString& PickedPath) 
{
        SetCurrentFilePath(PickedPath);
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

