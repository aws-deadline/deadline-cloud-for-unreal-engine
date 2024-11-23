// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "DeadlineCloudStatusHandler.h"
#include "DetailLayoutBuilder.h"
#include "IDetailCustomization.h"

class UDeadlineCloudDeveloperSettings;

/**
 * Deadline Cloud settings details UI customization
 */
class FDeadlineCloudSettingsDetails : public IDetailCustomization
{
private:
	TWeakObjectPtr<UDeadlineCloudDeveloperSettings> Settings;
	TUniquePtr<FDeadlineCloudStatusHandler> DeadlineCloudStatusHandler;
public:
	/** Makes a new instance of this detail layout class for a specific detail view requesting it */
	static TSharedRef<IDetailCustomization> MakeInstance();


	/** IDetailCustomization interface */
	virtual void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override;
};
