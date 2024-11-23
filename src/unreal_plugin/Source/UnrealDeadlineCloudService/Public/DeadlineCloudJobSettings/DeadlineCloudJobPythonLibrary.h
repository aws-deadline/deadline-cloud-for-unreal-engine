// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "CoreMinimal.h"
#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "PythonAPILibraries/PythonYamlLibrary.h"
#include "DeadlineCloudJobPythonLibrary.generated.h"

UCLASS()
class UNREALDEADLINECLOUDSERVICE_API UOpenJobPythonLibrary : public UObject, public TPythonAPILibraryBase<UPythonYamlLibrary>
{
	GENERATED_BODY()
public:

	UOpenJobPythonLibrary() {};
};