// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "PythonAPILibraries/PythonAPILibrary.h"
#include "UObject/Object.h"
#include "PythonGameThreadExecutor.generated.h"

/**
 * Python Game thread executor. Intended to execute python code in main thread in Unreal on Editor tick.
 * See implementation: OnTickThreadExecutorImplementation
 * in deadline-cloud-for-unreal: src/deadline/unreal_adaptor/UnrealClient/unreal_client.py
 */
UCLASS(Blueprintable)
class UNREALDEADLINECLOUDSERVICE_API UPythonGameThreadExecutor : public UObject, public TPythonAPILibraryBase<UPythonGameThreadExecutor>, public FTickableEditorObject
{
    GENERATED_BODY()
public:

	/** This method is called in Tick method. This way the code it runs will be executed in Editor Main thread */
	UFUNCTION(BlueprintImplementableEvent, Category = Python)
	void Execute(float DeltaTime) const;

private:

	/** FTickableEditorObject interface */
	virtual void Tick(float DeltaTime) override;
	virtual bool IsTickable() const override;
	virtual TStatId GetStatId() const override;
};
