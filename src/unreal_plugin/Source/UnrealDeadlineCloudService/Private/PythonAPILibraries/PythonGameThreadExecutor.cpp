// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#include "PythonAPILibraries/PythonGameThreadExecutor.h"

void UPythonGameThreadExecutor::Tick(float DeltaTime)
{
    Execute(DeltaTime);
}

bool UPythonGameThreadExecutor::IsTickable() const
{
    return true;
}

TStatId UPythonGameThreadExecutor::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(UICToolsGameThreadExecutor, STATGROUP_Tickables);
}
