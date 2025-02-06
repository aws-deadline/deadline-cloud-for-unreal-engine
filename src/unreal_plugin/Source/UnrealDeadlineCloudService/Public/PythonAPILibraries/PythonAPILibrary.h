// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once

/**
 * Base class for singleton uobject implemented in python.
 * See @ref UDeadlineCloudDeveloperSettings, @ref UDeadlineCloudJobBundleLibrary, @ref UPythonGameThreadExecutor
 * @tparam T uobject class type 
 */
template<typename T>
class UNREALDEADLINECLOUDSERVICE_API TPythonAPILibraryBase
{
public:
    static T* Get()
	{
		TArray<UClass*> PythonAPIClasses;
		GetDerivedClasses(T::StaticClass(), PythonAPIClasses);
		if (PythonAPIClasses.Num() > 0)
		{
			return Cast<T>(PythonAPIClasses[PythonAPIClasses.Num() - 1]->GetDefaultObject());
		}
		return nullptr;
	}
};
