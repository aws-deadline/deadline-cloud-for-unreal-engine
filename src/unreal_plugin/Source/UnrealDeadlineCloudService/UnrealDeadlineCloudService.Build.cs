// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

using UnrealBuildTool;
using UnrealBuildTool.Rules;

public class UnrealDeadlineCloudService : ModuleRules
{
    public UnrealDeadlineCloudService(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicIncludePaths.AddRange(
            new string[] {
            }
            );


        PrivateIncludePaths.AddRange(
            new string[] {
            }
            );


        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                    "UnrealEd",
    "EditorSubsystem",
             "Slate",
             "SlateCore",
             "EditorWidgets",
             "Core",
             "CoreUObject",
             "Engine",
             "MovieRenderPipelineCore",
                 "MovieRenderPipelineEditor",
             "InputCore",
             "DesktopWidgets",
            }
            );


        PrivateDependencyModuleNames.AddRange(
            new string[]
            {
                "Core",
                "CoreUObject",
                "Engine",
                "Slate",
                "SlateCore",
                "InputCore",
                "EditorFramework",
                "EditorStyle",
                "EditorWidgets",
                "DesktopWidgets",
                "DesktopPlatform",
                "UnrealEd",
                "LevelEditor",
                "InteractiveToolsFramework",
                "EditorInteractiveToolsFramework",
                "MovieRenderPipelineCore",
                "PropertyEditor",
                "DeveloperSettings",
                "JsonUtilities",
                "AssetTools",
                "Projects",
                "AssetRegistry",
                "LevelSequence"
            }
            );


        DynamicallyLoadedModuleNames.AddRange(
            new string[]
            {
            }
            );
    }
}
