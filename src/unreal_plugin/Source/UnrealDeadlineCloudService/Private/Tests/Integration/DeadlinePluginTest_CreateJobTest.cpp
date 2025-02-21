#include "AssetRegistry/AssetRegistryModule.h"
#include "CoreMinimal.h"
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
            UE_LOG(LogCreateJobTest, Display, TEXT("Found job creation log message"));
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
    const int TimeoutSeconds = 180;
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

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMovieQueueCreateJobTest, "Deadline.Integration.CreateJob",
    EAutomationTestFlags::EditorContext |
    EAutomationTestFlags::ProductFilter)

    bool FMovieQueueCreateJobTest::RunTest(const FString& Parameters)
{
    UE_LOG(LogCreateJobTest, Display, TEXT("Starting remote render test"));

    // Get and configure project settings
    UMovieRenderPipelineProjectSettings* ProjectSettings = GetMutableDefault<UMovieRenderPipelineProjectSettings>();
    if (!ProjectSettings)
    {
        UE_LOG(LogCreateJobTest, Error, TEXT("Failed to get project settings"));
        return false;
    }

    ProjectSettings->DefaultRemoteExecutor = FSoftClassPath(TEXT("/Engine/PythonTypes.MoviePipelineDeadlineCloudRemoteExecutor"));
    UE_LOG(LogCreateJobTest, Display, TEXT("Configured project settings"));

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

    UMoviePipelineExecutorJob* NewJob = UMoviePipelineEditorBlueprintLibrary::CreateJobFromSequence(ActiveQueue, LevelSequence);
    if (!NewJob)
    {
        UE_LOG(LogCreateJobTest, Error, TEXT("Failed to CreateJobFromSequence"));
        return false;
    }
    UE_LOG(LogCreateJobTest, Display, TEXT("Created job from sequence"));

    // Currently two "expected" warning/error messages which we should try to resolve separately, but don't currently break anything
    // in our underlying functionality
    // The QueueManifest message may appear 1 or 2 times depending on whether you've run the test before.
    AddExpectedError(TEXT("Failed to load '/Engine/MovieRenderPipeline/Editor/QueueManifest': Can't find file"),
        EAutomationExpectedErrorFlags::Contains, 0);
    // The -execcmds message WILL appear twice
    AddExpectedError(TEXT("Appearance of custom '-execcmds' argument on the Render node can cause unpredictable issues"),
        EAutomationExpectedErrorFlags::Contains, 2);

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

    UE_LOG(LogCreateJobTest, Display, TEXT("Test setup complete"));
    return true;
}