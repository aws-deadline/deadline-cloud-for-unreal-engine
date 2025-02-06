// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "DeadlineCloudJobSettings/DeadlineCloudSettingsDetails.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDeveloperSettings.h"
#include "DetailLayoutBuilder.h"
#include "DetailWidgetRow.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/SBoxPanel.h"

#define LOCTEXT_NAMESPACE "CryptoKeysSettingsDetails"

TSharedRef<IDetailCustomization> FDeadlineCloudSettingsDetails::MakeInstance()
{
    return MakeShareable(new FDeadlineCloudSettingsDetails);
}

/*
FText FDeadlineCloudSettingsDetails::GetCredsState() const
{
    return FText::FromString(Settings->WorkStationConfiguration.State.CredsType);
}
*/

void FDeadlineCloudSettingsDetails::CustomizeDetails(IDetailLayoutBuilder& DetailBuilder)
{
    TArray<TWeakObjectPtr<UObject>> ObjectsBeingCustomized;
    DetailBuilder.GetObjectsBeingCustomized(ObjectsBeingCustomized);
    Settings = Cast<UDeadlineCloudDeveloperSettings>(ObjectsBeingCustomized[0].Get());
    DeadlineCloudStatusHandler = MakeUnique<FDeadlineCloudStatusHandler>(Settings.Get());
    DeadlineCloudStatusHandler->StartDirectoryWatch();

    IDetailCategoryBuilder& LoginCategory = DetailBuilder.EditCategory("Login DeadlineCloud");
    LoginCategory.AddCustomRow(LOCTEXT("DeadlineCloudLogin", "DeadlineCloudLogin"))
        .ValueContent()
    	[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot()
			.Padding(FMargin(5, 5, 5, 5))
			.AutoWidth()
			[
				SNew(SButton)
				.Text(LOCTEXT("DeadlineCloudLogin", "Login"))
				.ToolTipText(LOCTEXT("DeadlineCloudLogin_Tooltip", "Login"))
				.OnClicked_Lambda([this]()
				{
					if (const auto LoginLib = UDeadlineCloudDeveloperSettings::Get())
					{
						LoginLib->Login();
					}
					return(FReply::Handled());
				})
			]
			+ SHorizontalBox::Slot()
			.Padding(5)
			.AutoWidth()
			[
				SNew(SButton)
				.Text(LOCTEXT("DeadlineCloudLogout", "Logout"))
				.ToolTipText(LOCTEXT("DeadlineCloudLogout_Tooltip", "Logout"))
				.OnClicked_Lambda([this]()
				{
					if (const auto LoginLib = UDeadlineCloudDeveloperSettings::Get())
					{
						LoginLib->Logout();
					}
					return(FReply::Handled());
				})
			]
		];
	
	DetailBuilder.HideCategory(TEXT("cache"));

	IDetailCategoryBuilder& StatusCategory = DetailBuilder.EditCategory("DeadlineCloud Status");
	StatusCategory.AddCustomRow(LOCTEXT("DeadlineCloudStatus", "DeadlineCloudStatus"))
		.ValueContent()
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				.Padding(FMargin(5, 5, 5, 5))
				.AutoWidth()
				[
					SNew(STextBlock)
					.Font(IDetailLayoutBuilder::GetDetailFontBold())
					.Text(LOCTEXT("DeadlineCloudCreds", "Creds:"))
				]
				+ SHorizontalBox::Slot()
				.Padding(5)
				.AutoWidth()
				[
					SNew(STextBlock)
					.Text_Lambda([this]() { return FText::FromString(Settings->WorkStationConfiguration.State.CredsType); })
				]
			]
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				.Padding(FMargin(5, 5, 5, 5))
				.AutoWidth()
				[
					SNew(STextBlock)
					.Font(IDetailLayoutBuilder::GetDetailFontBold())
					.Text(LOCTEXT("DeadlineCloudStatus", "Status:"))
				]
				+ SHorizontalBox::Slot()
				.Padding(FMargin(5))
				.AutoWidth()
				[
					SNew(STextBlock)
					.Text_Lambda([this]() { return FText::FromString(Settings->WorkStationConfiguration.State.CredsStatus); })
				]
			]
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot()
				.Padding(FMargin(5, 5, 5, 5))
				.AutoWidth()
				[
					SNew(STextBlock)
					.Font(IDetailLayoutBuilder::GetDetailFontBold())
					.Text(LOCTEXT("DeadlineCloudAPI", "Deadline Cloud API:"))
				]
				+ SHorizontalBox::Slot()
				.Padding(FMargin(5))
				.AutoWidth()
				[
					SNew(STextBlock)
					.Text_Lambda([this]() { return FText::FromString(Settings->WorkStationConfiguration.State.ApiAvailability); })
				]
			]
		];

	const auto WorkStationProperty = DetailBuilder.GetProperty(
		FName("WorkStationConfiguration"), UDeadlineCloudDeveloperSettings::StaticClass());

	const auto StateProperty = WorkStationProperty->GetChildHandle("State");
	StateProperty->MarkHiddenByCustomization();
}

#undef LOCTEXT_NAMESPACE
