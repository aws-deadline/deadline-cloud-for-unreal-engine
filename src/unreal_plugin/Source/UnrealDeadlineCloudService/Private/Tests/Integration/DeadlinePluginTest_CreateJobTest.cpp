#include "AssetRegistry/AssetRegistryModule.h"
#include "CoreMinimal.h"
#include "DeadlineCloudJobSettings/DeadlineCloudDeveloperSettings.h"
#include "HAL/PlatformTime.h"
#include "Misc/AutomationTest.h"
#include "Tests/AutomationCommon.h"
#include "LevelSequence.h"
#include "MoviePipelineQueueSubsystem.h"
#include "MoviePipelineQueue.h"
#include "MovieScene.h"
#include "MovieRenderPipelineSettings.h"
#include "MoviePipelineEditorBlueprintLibrary.h"
#include "MovieRenderPipeline/DeadlineCloudRenderStepSetting.h"
#include "MovieRenderPipeline/MoviePipelineDeadlineCloudExecutorJob.h"
#include "Modules/ModuleManager.h"

DEFINE_LOG_CATEGORY_STATIC(LogCreateJobTest, Log, All);

class WaitForJobCreationLogCommand : public IAutomationLatentCommand, public FOutputDevice
{
    // Test command for registering/deregistering log listeners, running a render job using the provided queue and executor, and
    // listening for expected logging output to indicate success
public:
    WaitForJobCreationLogCommand(FAutomationTestBase* testInstance, UMoviePipelineQueueSubsystem* queueSubsystem, UMoviePipelineExecutorBase* executorBase)
        : m_startTime(FPlatformTime::Seconds())
        , m_renderStarted(false)
        , m_testInstance(testInstance)
        , m_queueSubsystem(queueSubsystem)
        , m_executor(executorBase)
    {
        GLog->AddOutputDevice(this);
        UE_LOG(LogCreateJobTest, Display, TEXT("Registered log listener"));
    }

    virtual ~WaitForJobCreationLogCommand()
    {
        GLog->RemoveOutputDevice(this);
        UE_LOG(LogCreateJobTest, Display, TEXT("Deregistered log listener"));
    }

    virtual void Serialize(const TCHAR* msg, ELogVerbosity::Type verbosity, const FName& category) override
    {
        // FOutputDevice Log Message handler

        // Check for Python job creation message
        if (category == TEXT("LogPython") && FCString::Stristr(msg, TEXT("Job creation result: job-")))
        {
            // Extract the job ID from the log message
            FString LogMessage(msg);
            FString JobId;

            // Find the job ID in the message (format: "Job creation result: job-xxxxxxxx")
            if (LogMessage.Contains(TEXT("Job creation result: ")))
            {
                int32 StartPos = LogMessage.Find(TEXT("Job creation result: ")) + FCString::Strlen(TEXT("Job creation result: "));
                JobId = LogMessage.Mid(StartPos).TrimEnd();

                // Remove any trailing characters like newlines or quotes
                JobId = JobId.TrimEnd().TrimQuotes();
            }

            if (!JobId.IsEmpty())
            {
                UE_LOG(LogCreateJobTest, Display, TEXT("Found job creation log message with job ID: %s"), *JobId);
            }
            else
            {
                UE_LOG(LogCreateJobTest, Display, TEXT("Found job creation log message but couldn't extract job ID"));
            }

            m_jobCreationFound = true;
        }

        // Check for dialog message
        if (category == TEXT("None") &&
            FCString::Stristr(msg, TEXT("Message dialog closed")) &&
            FCString::Stristr(msg, TEXT("Submitted jobs (1)")))
        {
            UE_LOG(LogCreateJobTest, Display, TEXT("Found dialog confirmation message"));
            m_dialogConfirmationFound = true;
        }
    }

    virtual bool Update() override
    {
        if (!m_renderStarted)
        {
            UE_LOG(LogCreateJobTest, Display, TEXT("Starting render queue"));
            m_queueSubsystem->RenderQueueWithExecutorInstance(m_executor);
            m_renderStarted = true;
        }

        if (m_jobCreationFound && m_dialogConfirmationFound)
        {
            UE_LOG(LogCreateJobTest, Display, TEXT("Both conditions met, marking test as successful"));
            m_testInstance->TestTrue("Job creation succeeded", true);

            return true;
        }

        if (FPlatformTime::Seconds() - m_startTime > TimeoutSeconds)
        {
            UE_LOG(LogCreateJobTest, Error, TEXT("Timed out after %d seconds. Job Creation: %d, Dialog: %d"),
                TimeoutSeconds, m_jobCreationFound, m_dialogConfirmationFound);
            m_testInstance->TestTrue("Job creation succeeded", false);
            return true;
        }
        return false;
    }

private:
    const int TimeoutSeconds = 300;
    double m_startTime = {};
    bool m_jobCreationFound = false;
    bool m_dialogConfirmationFound = false;
    bool m_renderStarted = false;
    FAutomationTestBase* m_testInstance;
    UMoviePipelineQueueSubsystem* m_queueSubsystem;
    UMoviePipelineExecutorBase* m_executor;
};

class RestoreQueueCommand : public IAutomationLatentCommand
{
    // Test command for restoring the "original" provided queue to the queue subsystem
public:
    RestoreQueueCommand(UMoviePipelineQueueSubsystem* queueSubsystem, UMoviePipelineQueue* originalQueue)
        : m_queueSubsystem(queueSubsystem)
        , m_originalQueue(originalQueue)
    {
    }

    virtual bool Update() override
    {
        UE_LOG(LogCreateJobTest, Display, TEXT("Restoring original queue"));
        m_queueSubsystem->LoadQueue(m_originalQueue);
        return true;
    }

private:
    UMoviePipelineQueueSubsystem* m_queueSubsystem;
    UMoviePipelineQueue* m_originalQueue;
};

// Settings helper class
class FSettingsHelper
{
public:
    static FProperty* ResolvePropertyByPath(UObject* RootObject, const FString& PropertyPath)
    {
	    if (!RootObject)
	    {
		    UE_LOG(LogCreateJobTest, Error, TEXT("RootObject is null"));
		    return nullptr;
	    }

	    TArray<FString> PathSegments;
	    PropertyPath.ParseIntoArray(PathSegments, TEXT("."));
	    if (PathSegments.Num() == 0)
	    {
		    UE_LOG(LogCreateJobTest, Error, TEXT("Property path is empty"));
		    return nullptr;
	    }

	    UStruct* CurrentStruct = RootObject->GetClass();
	    void* CurrentContainer = RootObject;

	    for (int32 i = 0; i < PathSegments.Num(); ++i)
	    {
		    const FName SegmentName(*PathSegments[i]);
		    FProperty* FoundProperty = CurrentStruct->FindPropertyByName(SegmentName);
		    if (!FoundProperty)
		    {
			    UE_LOG(LogCreateJobTest, Error, TEXT("Property '%s' not found in '%s'"), *SegmentName.ToString(), *CurrentStruct->GetName());
			    return nullptr;
		    }

		    if (i == PathSegments.Num() - 1)
		    {
			    return FoundProperty;
		    }

		    if (FStructProperty* StructProp = CastField<FStructProperty>(FoundProperty))
		    {
			    CurrentContainer = StructProp->ContainerPtrToValuePtr<void>(CurrentContainer);
			    CurrentStruct = StructProp->Struct;
		    }
		    else if (FObjectProperty* ObjectProp = CastField<FObjectProperty>(FoundProperty))
		    {
			    UObject* InnerObject = ObjectProp->GetObjectPropertyValue_InContainer(CurrentContainer);
			    if (!InnerObject)
			    {
				    UE_LOG(LogCreateJobTest, Error, TEXT("Nested object '%s' is null"), *SegmentName.ToString());
				    return nullptr;
			    }
			    CurrentContainer = InnerObject;
			    CurrentStruct = InnerObject->GetClass();
		    }
		    else
		    {
			    UE_LOG(LogCreateJobTest, Error, TEXT("Unsupported property '%s' (not struct or object)"), *SegmentName.ToString());
			    return nullptr;
		    }
	    }

	    return nullptr;
    }

    static void ApplyTestSettings()
    {
        UE_LOG(LogCreateJobTest, Display, TEXT("Applying test settings"));
        // Get settings
        UDeadlineCloudDeveloperSettings* Settings = UDeadlineCloudDeveloperSettings::GetMutable();
        if (!Settings)
        {
            UE_LOG(LogCreateJobTest, Error, TEXT("Failed to get Python implementation of settings"));
            return;
        }
        
        // Cache original values
        OriginalFarmId = Settings->WorkStationConfiguration.Profile.DefaultFarm;
        OriginalQueueId = Settings->WorkStationConfiguration.Farm.DefaultQueue;

        UE_LOG(LogCreateJobTest, Display, TEXT("Updating settings, original farm %s queue %s"), *OriginalFarmId, *OriginalQueueId);
        // Parse command line parameters
        FString ParamsString;
        if (FParse::Value(FCommandLine::Get(), TEXT("testparams="), ParamsString))
        {
            UE_LOG(LogCreateJobTest, Display, TEXT("Got ParamsString: '%s'"), *ParamsString);

            // Debug the full command line
            UE_LOG(LogCreateJobTest, Display, TEXT("Full command line: '%s'"), FCommandLine::Get());

            // Split using semicolon delimiter
            TArray<FString> KeyValuePairs;
            ParamsString.ParseIntoArray(KeyValuePairs, TEXT(";"), true);

            UE_LOG(LogCreateJobTest, Display, TEXT("Split into %d key-value pairs"), KeyValuePairs.Num());

            bool farmChanged = false;
            bool queueChanged = false;

            for (int32 i = 0; i < KeyValuePairs.Num(); ++i)
            {
                UE_LOG(LogCreateJobTest, Display, TEXT("Pair %d: '%s'"), i, *KeyValuePairs[i]);

                FString Key, Value;
                if (KeyValuePairs[i].Split(TEXT("="), &Key, &Value))
                {
                    UE_LOG(LogCreateJobTest, Display, TEXT("Split into key='%s', value='%s'"), *Key, *Value);

                    if (Key == TEXT("farm_id") && !Value.IsEmpty())
                    {
                        // If the value looks like an ID (starts with "farm-"), try to find the farm by ID
                        if (!Value.StartsWith(TEXT("farm-")))
                        {
                            UE_LOG(LogCreateJobTest, Warning, TEXT("Farm id not properly formatted '%s'"), *Value);
                            continue;
                        }

                        // Find farm by ID and use its name
                        FString FarmName = Value;

                        // In a real implementation, we would look up the farm name from the ID
                        // For now, we'll just use a placeholder
                        UE_LOG(LogCreateJobTest, Display, TEXT("Converting farm ID '%s' to name"), *Value);

                        // Look up the farm name from the ID using the Settings object
                        FString FoundName = Settings->FindFarmById(Value, true).Name;
                        if (!FoundName.IsEmpty())
                        {
                            FarmName = FoundName;
                            UE_LOG(LogCreateJobTest, Display, TEXT("Found farm name: '%s'"), *FarmName);
                        }
                        else
                        {
                            UE_LOG(LogCreateJobTest, Warning, TEXT("Could not find farm with ID: '%s'"), *Value);
                        }
                        UE_LOG(LogCreateJobTest, Display, TEXT("Found farm name: '%s'"), *FarmName);

                        // Check if the farm value is actually changing
                        if (Settings->WorkStationConfiguration.Profile.DefaultFarm != FarmName)
                        {
                            UE_LOG(LogCreateJobTest, Display, TEXT("Setting farm to '%s'"), *FarmName);
                            Settings->WorkStationConfiguration.Profile.DefaultFarm = FarmName;
                            farmChanged = true;
                        }
                        else
                        {
                            UE_LOG(LogCreateJobTest, Display, TEXT("Farm value unchanged (already '%s'), skipping update"), *FarmName);
                        }
                    }
                    else if (Key == TEXT("queue_id") && !Value.IsEmpty())
                    {
                        // If the value looks like an ID (starts with "queue-"), try to find the queue by ID
                        if (!Value.StartsWith(TEXT("queue-")))
                        {
                            UE_LOG(LogCreateJobTest, Warning, TEXT("Queue id not properly formatted '%s'"), *Value);
                            continue;
                        }

                        // Find queue by ID and use its name
                        FString QueueName = Value;

                        // In a real implementation, we would look up the queue name from the ID
                        // For now, we'll just use a placeholder
                        UE_LOG(LogCreateJobTest, Display, TEXT("Converting queue ID '%s' to name"), *Value);

                        // Look up the queue name from the ID using the Settings object
                        FString FoundName = Settings->FindQueueById(Value, true).Name;
                        if (!FoundName.IsEmpty())
                        {
                            QueueName = FoundName;
                            UE_LOG(LogCreateJobTest, Display, TEXT("Found queue name: '%s'"), *QueueName);
                        }
                        else
                        {
                            UE_LOG(LogCreateJobTest, Warning, TEXT("Could not find queue with ID: '%s'"), *Value);
                        }
                        UE_LOG(LogCreateJobTest, Display, TEXT("Found queue name: '%s'"), *QueueName);


                        // Check if the queue value is actually changing
                        if (Settings->WorkStationConfiguration.Farm.DefaultQueue != QueueName)
                        {
                            UE_LOG(LogCreateJobTest, Display, TEXT("Setting queue to '%s'"), *QueueName);
                            Settings->WorkStationConfiguration.Farm.DefaultQueue = QueueName;
                            queueChanged = true;
                        }
                        else
                        {
                            UE_LOG(LogCreateJobTest, Display, TEXT("Queue value unchanged (already '%s'), skipping update"), *QueueName);
                        }
                    }
                }
                else
                {
                    UE_LOG(LogCreateJobTest, Warning, TEXT("Failed to split pair '%s' on '='"), *KeyValuePairs[i]);
                }
            }

            // Save the settings
            Settings->SaveConfig();

            // Trigger the Python implementation's on_settings_modified method with the exact property name it expects
            if (farmChanged)
            {
                UE_LOG(LogCreateJobTest, Display, TEXT("Triggering OnSettingsModified for DefaultFarm"));
				FProperty* Property = ResolvePropertyByPath(Settings, TEXT("WorkStationConfiguration.Profile.DefaultFarm"));
                FPropertyChangedEvent PropertyEvent(Property);
                Settings->PostEditChangeProperty(PropertyEvent);
            }

            if (queueChanged)
            {
                UE_LOG(LogCreateJobTest, Display, TEXT("Triggering OnSettingsModified for DefaultQueue"));
				FProperty* Property = ResolvePropertyByPath(Settings, TEXT("WorkStationConfiguration.Farm.DefaultQueue"));
                FPropertyChangedEvent PropertyEvent(Property);
                Settings->PostEditChangeProperty(PropertyEvent);
            }
        }
    }

    static void RestoreOriginalSettings()
    {
        // Restore original settings
        UDeadlineCloudDeveloperSettings* Settings = UDeadlineCloudDeveloperSettings::GetMutable();
        if (Settings)
        {
            UE_LOG(LogCreateJobTest, Display, TEXT("Restoring settings, original farm %s queue %s"), *OriginalFarmId, *OriginalQueueId);

            // Check if the farm value needs to be restored
            if (Settings->WorkStationConfiguration.Profile.DefaultFarm != OriginalFarmId)
            {
                UE_LOG(LogCreateJobTest, Display, TEXT("Restoring farm from '%s' to '%s'"),
                    *Settings->WorkStationConfiguration.Profile.DefaultFarm, *OriginalFarmId);
                Settings->WorkStationConfiguration.Profile.DefaultFarm = OriginalFarmId;
                Settings->SaveConfig();

                FProperty* Property = ResolvePropertyByPath(Settings, TEXT("WorkStationConfiguration.Profile.DefaultFarm"));
                FPropertyChangedEvent PropertyEvent(Property);
				Settings->PostEditChangeProperty(PropertyEvent);
            }
            else
            {
                UE_LOG(LogCreateJobTest, Display, TEXT("Farm already at original value '%s', no restore needed"), *OriginalFarmId);
            }

            // Check if the queue value needs to be restored
            if (Settings->WorkStationConfiguration.Farm.DefaultQueue != OriginalQueueId)
            {
                UE_LOG(LogCreateJobTest, Display, TEXT("Restoring queue from '%s' to '%s'"),
                    *Settings->WorkStationConfiguration.Farm.DefaultQueue, *OriginalQueueId);
                Settings->WorkStationConfiguration.Farm.DefaultQueue = OriginalQueueId;
                Settings->SaveConfig();

				FProperty* Property = ResolvePropertyByPath(Settings, TEXT("WorkStationConfiguration.Farm.DefaultQueue"));
                FPropertyChangedEvent PropertyEvent(Property);
				Settings->PostEditChangeProperty(PropertyEvent);
            }
            else
            {
                UE_LOG(LogCreateJobTest, Display, TEXT("Queue already at original value '%s', no restore needed"), *OriginalQueueId);
            }
        }
    }

private:
    static FString OriginalFarmId;
    static FString OriginalQueueId;
};

// Initialize static members
FString FSettingsHelper::OriginalFarmId;
FString FSettingsHelper::OriginalQueueId;

// Latent command to restore settings after test completes
class FRestoreSettingsLatentCommand : public IAutomationLatentCommand
{
public:
    FRestoreSettingsLatentCommand() {}

    virtual bool Update() override
    {
        UE_LOG(LogCreateJobTest, Display, TEXT("Restoring settings via latent command"));
        FSettingsHelper::RestoreOriginalSettings();
        return true;
    }
};

ULevelSequence* FindFirstLevelSequence()
{
    // Get the asset registry
    FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
    IAssetRegistry& AssetRegistry = AssetRegistryModule.Get();

    // Create filter to search for level sequences
    FARFilter Filter;
    Filter.ClassPaths.Add(ULevelSequence::StaticClass()->GetClassPathName());
    Filter.PackagePaths.Add(TEXT("/Game"));
    Filter.bRecursivePaths = true;

    // Get all assets matching our filter
    TArray<FAssetData> AssetList;
    AssetRegistry.GetAssets(Filter, AssetList);

    // Find the sequence with shortest path
    ULevelSequence* ShortestPathSequence = nullptr;
    int32 ShortestDepth = MAX_int32;

    for (const FAssetData& Asset : AssetList)
    {
        FString Path = Asset.GetObjectPathString();
        TArray<FString> PathSegments;
        Path.ParseIntoArray(PathSegments, TEXT("/"));
        int32 Depth = PathSegments.Num();

        if (Depth < ShortestDepth)
        {
            ShortestDepth = Depth;
            ShortestPathSequence = Cast<ULevelSequence>(Asset.GetAsset());
        }
    }

    return ShortestPathSequence;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMovieQueueCreateJobTest, "DeadlineCloud.Integration.CreateJob",
    EAutomationTestFlags::EditorContext |
    EAutomationTestFlags::ProductFilter)

    bool FMovieQueueCreateJobTest::RunTest(const FString& Parameters)
{
    UE_LOG(LogCreateJobTest, Display, TEXT("Starting remote render test"));
    FSettingsHelper::ApplyTestSettings();

    // Get and configure project settings
    UMovieRenderPipelineProjectSettings* ProjectSettings = GetMutableDefault<UMovieRenderPipelineProjectSettings>();
    if (!ProjectSettings)
    {
        UE_LOG(LogCreateJobTest, Error, TEXT("Failed to get project settings"));
        return false;
    }

    ProjectSettings->DefaultRemoteExecutor = FSoftClassPath(TEXT("/Engine/PythonTypes.MoviePipelineDeadlineCloudRemoteExecutor"));
    TSubclassOf<UMoviePipelineExecutorBase> RemoteClass = ProjectSettings->DefaultRemoteExecutor.TryLoadClass<UMoviePipelineExecutorBase>();
    TestTrue(TEXT("Failed to load remote executor class"), RemoteClass != nullptr);

    ProjectSettings->DefaultExecutorJob = UMoviePipelineDeadlineCloudExecutorJob::StaticClass();
    TestNotNull(TEXT("Failed to set executor job"), ProjectSettings->DefaultExecutorJob.TryLoadClass<UMoviePipelineExecutorJob>());

    UE_LOG(LogCreateJobTest, Display, TEXT("Configured project settings"));

    UE_LOG(LogCreateJobTest, Display, TEXT("DefaultExecutorJob set to: %s"),
        *ProjectSettings->DefaultExecutorJob.ToString());

    TSubclassOf<UMoviePipelineExecutorJob> ExecutorJobClass = ProjectSettings->DefaultExecutorJob.TryLoadClass<UMoviePipelineExecutorJob>();
    UE_LOG(LogCreateJobTest, Display, TEXT("TryLoadClass returned: %s"),
        ExecutorJobClass ? *ExecutorJobClass->GetName() : TEXT("nullptr"));

    // Get the Queue Subsystem
    UMoviePipelineQueueSubsystem* QueueSubsystem = GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>();
    TestNotNull(TEXT("Queue Subsystem should exist"), QueueSubsystem);
    UE_LOG(LogCreateJobTest, Display, TEXT("Got queue subsystem"));

    // Cache our original queue and create one to use specifically for this test
    // We'll restore the queue at the end
    UMoviePipelineQueue* OriginalQueue = QueueSubsystem->GetQueue();
    UMoviePipelineQueue* TestQueue = NewObject<UMoviePipelineQueue>();
    QueueSubsystem->LoadQueue(TestQueue);

    UMoviePipelineQueue* ActiveQueue = QueueSubsystem->GetQueue();
    TestNotNull(TEXT("Active Queue should exist"), ActiveQueue);
    UE_LOG(LogCreateJobTest, Display, TEXT("Got Active Queue"));

    // Find and load level sequence
    ULevelSequence* LevelSequence = FindFirstLevelSequence();

    TestNotNull(TEXT("LevelSequence should not be null"), LevelSequence);
    UE_LOG(LogCreateJobTest, Display, TEXT("Got LevelSequence: %s"), *LevelSequence->GetPathName());

    TSoftClassPtr<UMoviePipelineDeadlineCloudExecutorJob> SoftClassPtr = TSoftClassPtr<UMoviePipelineDeadlineCloudExecutorJob>(ProjectSettings->DefaultExecutorJob);
    UMoviePipelineDeadlineCloudExecutorJob* NewJob = NewObject<UMoviePipelineDeadlineCloudExecutorJob>(GetTransientPackage(), SoftClassPtr.LoadSynchronous());

    NewJob->JobPresetChanged();
    UMoviePipelineEditorBlueprintLibrary::EnsureJobHasDefaultSettings(NewJob);

    TestNotNull(TEXT("JobPreset should not be null"), NewJob->JobPreset.Get());
    UE_LOG(LogCreateJobTest, Display, TEXT("Created JobPreset"));

    FSoftObjectPath CurrentWorld;

    UWorld* EditorWorld = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;

    CurrentWorld = FSoftObjectPath(EditorWorld);

    FSoftObjectPath Sequence(LevelSequence);
    NewJob->Map = CurrentWorld;
    NewJob->SetSequence(Sequence);
    NewJob->JobName = NewJob->Sequence.GetAssetName();

    UMoviePipelineExecutorJob* QueueJob = ActiveQueue->DuplicateJob(NewJob);
    if (!QueueJob)
    {
        UE_LOG(LogCreateJobTest, Error, TEXT("Failed to Duplicate Job into queue"));
        return false;
    }
    UE_LOG(LogCreateJobTest, Display, TEXT("Created job from sequence"));

    // Currently two "expected" warning/error messages which we should try to resolve separately, but don't currently break anything
    // in our underlying functionality
    // The QueueManifest message may appear 1 or 2 times depending on whether you've run the test before.
    AddExpectedError(TEXT("/Engine/MovieRenderPipeline/Editor/QueueManifest"),
        EAutomationExpectedErrorFlags::Contains, 0);
    // The -execcmds message may appear 1 or 2 times depending on whether you've run the test before
    AddExpectedError(TEXT("Appearance of custom '-execcmds' argument on the Render node can cause unpredictable issues"),
        EAutomationExpectedErrorFlags::Contains, 0);

    // Load and use remote executor
    TSubclassOf<UMoviePipelineExecutorBase> ExecutorClass = ProjectSettings->DefaultRemoteExecutor.TryLoadClass<UMoviePipelineExecutorBase>();
    if (!ExecutorClass)
    {
        UE_LOG(LogCreateJobTest, Error, TEXT("Failed to load executor class"));
        return false;
    }

    FAutomationTestBase* testInstance = this;

    UE_LOG(LogCreateJobTest, Display, TEXT("Creating executor"));
    UMoviePipelineExecutorBase* executorBase = NewObject<UMoviePipelineExecutorBase>(GetTransientPackage(), ExecutorClass);

    // Command to set up our log listeners and run our job
    ADD_LATENT_AUTOMATION_COMMAND(WaitForJobCreationLogCommand(testInstance, QueueSubsystem, executorBase));

    // Cleanup command to restore our queue to its original state
    ADD_LATENT_AUTOMATION_COMMAND(RestoreQueueCommand(QueueSubsystem, OriginalQueue));

    // Add a final latent command to restore settings after all other commands complete
    ADD_LATENT_AUTOMATION_COMMAND(FRestoreSettingsLatentCommand());

    UE_LOG(LogCreateJobTest, Display, TEXT("Test setup complete"));
    return true;
}