// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

#pragma once
#include "Misc/AutomationTest.h"
#include "CoreMinimal.h"
#include "Misc/Paths.h"
#include "PythonAPILibraries/DeadlineCloudJobBundleLibrary.h"

BEGIN_DEFINE_SPEC(FDeadlinePluginDependenciesSpec, "DeadlineCloud.Offline",
    EAutomationTestFlags::ProductFilter | EAutomationTestFlags::EditorContext);
END_DEFINE_SPEC(FDeadlinePluginDependenciesSpec);

void FDeadlinePluginDependenciesSpec::Define()
{
    Describe("PluginDependencies", [this]()
    {
        It("GetPluginsDependencies should return valid directories", [this]()
        {
            auto Library = UDeadlineCloudJobBundleLibrary::Get();
            if (!Library)
            {
                AddError(TEXT("Failed to get DeadlineCloudJobBundleLibrary"));
                return;
            }

            TArray<FString> PluginDirs = Library->GetPluginsDependencies();

            // Verify each returned path is a valid directory on disk
            for (const FString& Dir : PluginDirs)
            {
                TestTrue(
                    FString::Printf(TEXT("Plugin dir should exist: '%s'"), *Dir),
                    FPaths::DirectoryExists(Dir)
                );
            }
        });

        It("GetPluginsDependencies should not include stock engine plugins", [this]()
        {
            auto Library = UDeadlineCloudJobBundleLibrary::Get();
            if (!Library)
            {
                AddError(TEXT("Failed to get DeadlineCloudJobBundleLibrary"));
                return;
            }

            TArray<FString> PluginDirs = Library->GetPluginsDependencies();
            FString EnginePluginsDir = FPaths::ConvertRelativePathToFull(FPaths::EnginePluginsDir());

            for (const FString& Dir : PluginDirs)
            {
                FString NormalizedDir = FPaths::ConvertRelativePathToFull(Dir);

                // If it's under engine plugins, it must be under Marketplace/
                if (NormalizedDir.StartsWith(EnginePluginsDir))
                {
                    FString Relative = NormalizedDir.Mid(EnginePluginsDir.Len());
                    TestTrue(
                        FString::Printf(TEXT("Engine plugin dir '%s' should be under Marketplace/"), *Dir),
                        Relative.StartsWith(TEXT("Marketplace"))
                    );
                }
            }
        });

        It("GetPluginsDependencies should not include UnrealDeadlineCloudService", [this]()
        {
            auto Library = UDeadlineCloudJobBundleLibrary::Get();
            if (!Library)
            {
                AddError(TEXT("Failed to get DeadlineCloudJobBundleLibrary"));
                return;
            }

            TArray<FString> PluginDirs = Library->GetPluginsDependencies();

            for (const FString& Dir : PluginDirs)
            {
                TestFalse(
                    FString::Printf(TEXT("Should not contain DeadlineCloudService: '%s'"), *Dir),
                    Dir.Contains(TEXT("UnrealDeadlineCloudService"))
                );
            }
        });
    });
}
