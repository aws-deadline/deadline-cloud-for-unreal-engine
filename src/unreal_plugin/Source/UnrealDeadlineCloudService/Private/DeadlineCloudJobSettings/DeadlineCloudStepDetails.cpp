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
    if (Settings->PathToTemplate.FilePath.Len() > 0)
    {
        StepParameters = Settings->OpenStepFile(Settings->PathToTemplate.FilePath);
        if (StepParameters.Num() > 0) {

            IDetailCategoryBuilder& PropertiesCategory = DetailBuilder.EditCategory("DeadlineCloudStepParameters");

            for (auto& parameter : StepParameters) {

                FString CurrentName = parameter.Name;

                    
                PropertiesCategory.AddCustomRow(LOCTEXT("Task Parameter Definitions", "Task Parameter Definitions"))
                    .NameContent()
                    [
                        SNew(SHorizontalBox)
                            + SHorizontalBox::Slot()
                            .Padding(FMargin(5, 5, 5, 5))
                            .AutoWidth()
                            [
                                SNew(STextBlock)
                                    .Text(FText::FromString(CurrentName))
                            ]]
                         .ValueContent()
                            [
                                SNew(SHorizontalBox)
                                    + SHorizontalBox::Slot()
                                    .Padding(FMargin(5, 5, 5, 5))
                                    .AutoWidth()
                                    [
                                        SNew(STextBlock)//create properties array
                                            .Text(FText::FromString("taskParameterDefinitions"))
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
        UE_LOG(LogTemp, Warning, TEXT("Empty job path string"));
    }

}




#undef LOCTEXT_NAMESPACE