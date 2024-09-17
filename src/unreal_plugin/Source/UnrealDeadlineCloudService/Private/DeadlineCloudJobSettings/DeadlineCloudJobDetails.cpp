#include "DeadlineCloudJobSettings/DeadlineCloudJobDetails.h"



TSharedRef<IDetailCustomization> FDeadlineCloudJobDetails::MakeInstance()
{
	return MakeShareable(new FDeadlineCloudJobDetails);
}

void FDeadlineCloudJobDetails::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{

	TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
	DetailBuilder.GetObjectsBeingCustomized(ObjectsBeingCustomized);
	CustomizedSettings = Cast<UDeadlineCloudJob>(ObjectsBeingCustomized[0].Get());//instead for

	//DeadlineCloudStatusHandler = MakeUnique<FDeadlineCloudStatusHandler>(CustomizedSettings.Get());
	//DeadlineCloudStatusHandler->StartDirectoryWatch();

	//test category (edit)
	//IDetailCategoryBuilder& Category = DetailBuilder.EditCategory("TestCategory", FText::GetEmpty());

	/*
	Category.AddCustomRow(LOCTEXT("TestName_", "TestName_"))
		.NameContent()
		[
			SNew(STextBlock)
				.Font(IDetailLayoutBuilder::GetDetailFontBold())
				.Text(LOCTEXT("Name_", "Name_"))
		];
*/
}