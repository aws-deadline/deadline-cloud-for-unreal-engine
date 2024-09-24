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
                        .FillWidth(1.0f)
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

        StepParameters = Settings->OpenStepFile(Settings->PathToTemplate.FilePath);
        if (StepParameters.Num() > 0) {

            IDetailCategoryBuilder& PropertiesCategory = DetailBuilder.EditCategory("DeadlineCloudStepParameters");

            for (auto& StepParameter : StepParameters) {

                CurrentName = StepParameter.Name;

                PropertiesCategory.AddCustomRow(LOCTEXT("Task Parameter Definitions", "Task Parameter Definitions"))
                    //  .NameContent()
                    .WholeRowContent()
                    [
                        SNew(SHorizontalBox)
                            + SHorizontalBox::Slot()
                            .Padding(FMargin(5, 5, 5, 5))
                            .FillWidth(1.0f)
                            .HAlign(HAlign_Left)
                            .VAlign(VAlign_Center)
                            [
                                SNew(STextBlock)
                                    .Text(FText::FromString(CurrentName))
                            ]
                            + SHorizontalBox::Slot()
                            .Padding(FMargin(5, 5, 5, 5))
                            .HAlign(HAlign_Fill)
                            .FillWidth(1.0f)[
                                SNew(SVerticalBox) 
                                    + SVerticalBox::Slot()
                                    .AutoHeight()
                                    .HAlign(HAlign_Fill)
                                    .Padding(2)
                                    [GenerateTasksContent(StepParameter.StepTaskParameterDefinition)]
                            ]
                    ];

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