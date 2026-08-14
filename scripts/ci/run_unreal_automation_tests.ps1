param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,

    [string]$UEVersion = "",

    [string]$EngineRoot = "",

    [int]$TestTimeoutMinutes = 20
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

if (-not $UEVersion) {
    $UEVersion = if ($env:UE_VERSION) { $env:UE_VERSION } else { "5.7" }
}
if (-not $EngineRoot) {
    $EngineRoot = "C:\Program Files\Epic Games\UE_$UEVersion"
}

$editor = Join-Path $EngineRoot "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
$fixtureRoot = Join-Path $SourceRoot "scripts\ci\fixtures\UnrealAutomationTest"
$buildToken = if ($env:CODEBUILD_BUILD_ID) {
    $env:CODEBUILD_BUILD_ID -replace "[^A-Za-z0-9_.-]", "-"
} else {
    [guid]::NewGuid().ToString("N")
}
$runRoot = Join-Path "C:\UnrealCI\automation" $buildToken
$projectRoot = Join-Path $runRoot "UnrealAutomationTest"
$stdoutPath = Join-Path $runRoot "UnrealEditor.stdout.log"
$stderrPath = Join-Path $runRoot "UnrealEditor.stderr.log"
$ueLog = $null
$runFailure = $null
$editorExitCode = $null
$processFailure = $null

function Write-FullLog {
    param(
        [string]$Label,
        [string]$Path
    )

    try {
        if ($Path -and (Test-Path $Path)) {
            Write-Host "=== BEGIN $Label ($Path) ==="
            Get-Content -Path $Path -ErrorAction Stop
            Write-Host "=== END $Label ==="
        }
    }
    catch {
        Write-Host "Unable to print $Label from ${Path}: $($_.Exception.Message)"
    }
}

function Find-LatestUatLog {
    try {
        $uatRoot = Join-Path $env:APPDATA "Unreal Engine\AutomationTool\Logs"
        if (-not (Test-Path $uatRoot)) {
            return $null
        }

        return Get-ChildItem $uatRoot -Filter "Log.txt" -File -Recurse -ErrorAction Stop |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
    }
    catch {
        Write-Host "Unable to locate the latest AutomationTool log: $($_.Exception.Message)"
        return $null
    }
}

function Get-TestPaths {
    param([object[]]$LogMatches)

    return @(
        $LogMatches | ForEach-Object {
            if ($_.Line -match "Path=\{([^}]+)\}") {
                $Matches[1]
            }
        }
    )
}

function Get-CapturedOutput {
    param(
        [object]$Task,
        [string]$Label,
        [int]$TimeoutMilliseconds = 5000
    )

    if ($null -eq $Task) {
        return "$Label capture was not started."
    }

    try {
        if ($Task.Wait($TimeoutMilliseconds)) {
            return $Task.Result
        }
        return "$Label capture did not complete within $TimeoutMilliseconds ms."
    }
    catch {
        return "$Label capture failed: $($_.Exception.Message)"
    }
}

function Write-CapturedOutput {
    param(
        [object]$Task,
        [string]$Label,
        [string]$Path
    )

    try {
        $content = Get-CapturedOutput -Task $Task -Label $Label
        [System.IO.File]::WriteAllText($Path, $content)
    }
    catch {
        Write-Host "Unable to write $Label to ${Path}: $($_.Exception.Message)"
    }
}

try {
    if (-not (Test-Path $editor)) {
        throw "UE $UEVersion editor was not found at $editor"
    }
    if (-not (Test-Path (Join-Path $fixtureRoot "UnrealAutomationTest.uproject"))) {
        throw "The stripped automation fixture was not found at $fixtureRoot"
    }

    New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
    Copy-Item $fixtureRoot $projectRoot -Recurse -Force
    $project = Get-Item (Join-Path $projectRoot "UnrealAutomationTest.uproject")
    $logDirectory = Join-Path $project.DirectoryName "Saved\Logs"

    $testSelection = "DeadlineCloud.Offline"
    $arguments = @(
        "`"$($project.FullName)`"",
        "-RenderOffScreen",
        "-ForceRes",
        "-ResX=3840",
        "-ResY=2160",
        "-Maximized",
        "-unattended",
        "-nosplash",
        "-NoSound",
        "-nocef",
        "-SCCProvider=None",
        "`"-LogCmds=LogPython off`"",
        "`"-ExecCmds=Automation RunTests $testSelection`"",
        "`"-testexit=Automation Test Queue Empty`"",
        "-log"
    )

    Write-Host "Running offline Unreal automation tests with UE $UEVersion"
    Write-Host "Source revision: $env:CODEBUILD_RESOLVED_SOURCE_VERSION"
    Write-Host "Test selection: $testSelection"

    $previousMetadataDisabled = $env:AWS_EC2_METADATA_DISABLED
    try {
        $env:AWS_EC2_METADATA_DISABLED = "true"
        $startInfo = New-Object System.Diagnostics.ProcessStartInfo
        $startInfo.FileName = $editor
        $startInfo.Arguments = $arguments -join " "
        $startInfo.UseShellExecute = $false
        $startInfo.CreateNoWindow = $true
        $startInfo.RedirectStandardOutput = $true
        $startInfo.RedirectStandardError = $true

        $process = New-Object System.Diagnostics.Process
        $stdoutTask = $null
        $stderrTask = $null
        try {
            $process.StartInfo = $startInfo
            if (-not $process.Start()) {
                throw "Failed to start UnrealEditor-Cmd"
            }
            $stdoutTask = $process.StandardOutput.ReadToEndAsync()
            $stderrTask = $process.StandardError.ReadToEndAsync()
            $exited = $process.WaitForExit($TestTimeoutMinutes * 60 * 1000)
            if ($exited) {
                $process.WaitForExit()
                $editorExitCode = $process.ExitCode
                $processFailure = $null
            }
            else {
                $process.Kill()
                $process.WaitForExit()
                $editorExitCode = "TIMEOUT"
                $processFailure = "UnrealEditor-Cmd exceeded the $TestTimeoutMinutes minute test timeout"
            }
        }
        finally {
            try {
                Write-CapturedOutput -Task $stdoutTask -Label "Standard output" -Path $stdoutPath
                Write-CapturedOutput -Task $stderrTask -Label "Standard error" -Path $stderrPath
            }
            finally {
                $process.Dispose()
            }
        }
    }
    finally {
        if ($null -eq $previousMetadataDisabled) {
            Remove-Item Env:\AWS_EC2_METADATA_DISABLED -ErrorAction SilentlyContinue
        }
        else {
            $env:AWS_EC2_METADATA_DISABLED = $previousMetadataDisabled
        }
    }

    $ueLog = Get-ChildItem $logDirectory -Filter "*.log" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    $started = @()
    $completed = @()
    $queueSummary = $null
    if ($ueLog) {
        $started = @(
            Select-String -Path $ueLog.FullName -Pattern "Test Started\..*DeadlineCloud"
        )
        $completed = @(
            Select-String -Path $ueLog.FullName -Pattern "Test Completed\. Result=\{[^}]+\}.*DeadlineCloud"
        )
        $queueSummary = Select-String -Path $ueLog.FullName `
            -Pattern "Automation Test Queue Empty ([0-9]+) tests performed\." |
            Select-Object -Last 1
    }
    $failed = @(
        $completed | Where-Object { $_.Line -notmatch "Result=\{Success\}" }
    )
    $startedPaths = Get-TestPaths $started
    $completedPaths = Get-TestPaths $completed
    $identityDifferences = if ($startedPaths.Count -gt 0 -and $completedPaths.Count -gt 0) {
        @(
            Compare-Object `
                -ReferenceObject @($startedPaths | Sort-Object) `
                -DifferenceObject @($completedPaths | Sort-Object)
        )
    } else {
        @()
    }
    $queueDrained = $null -ne $queueSummary
    $performedCount = if ($queueDrained) {
        [int]$queueSummary.Matches[0].Groups[1].Value
    } else {
        0
    }

    Write-Host "=== BEGIN UNREAL AUTOMATION RESULTS ==="
    $started | ForEach-Object { Write-Host $_.Line }
    $completed | ForEach-Object { Write-Host $_.Line }
    Write-Host (
        "Automation summary: started={0}; completed={1}; performed={2}; failed={3}; queueDrained={4}; editorExitCode={5}" -f `
            $started.Count, $completed.Count, $performedCount, $failed.Count, $queueDrained, $editorExitCode
    )
    Write-Host "=== END UNREAL AUTOMATION RESULTS ==="

    if ($null -eq $editorExitCode) {
        throw "UnrealEditor-Cmd exit code was never captured"
    }
    if ($processFailure) {
        throw $processFailure
    }
    if ($editorExitCode -ne 0) {
        throw "UnrealEditor-Cmd exited with code $editorExitCode"
    }
    if (-not $ueLog) {
        throw "No Unreal Editor log was produced in $logDirectory"
    }
    if ($started.Count -eq 0) {
        throw "No DeadlineCloud automation tests started"
    }
    if ($started.Count -ne $completed.Count) {
        throw "$($started.Count) tests started but $($completed.Count) completed"
    }
    if ($startedPaths.Count -ne $started.Count -or $completedPaths.Count -ne $completed.Count) {
        throw "Unable to extract a test identity from every start and completion record"
    }
    if ($identityDifferences.Count -gt 0) {
        throw "Started and completed test identities do not match"
    }
    $requiredTests = @(
        "DeadlineCloud.Offline.MRQAttachmentOverrides.RoundTrip",
        "DeadlineCloud.Offline.DeadlineCloudMRQJobUI.MRQJobUI",
        "DeadlineCloud.Offline.DeadlineCloudMRQJobUI.MRQJobUIHiddenSelectorCoverage",
        "DeadlineCloud.Offline.DeadlineCloudJobUI.JobUI",
        "DeadlineCloud.Offline.DeadlineCloudStepUI.StepUI",
        "DeadlineCloud.Offline.DeadlineCloudEnvironmentUI.EnvironmentUI",
        "DeadlineCloud.Offline.DeadlineCloudHostRequirementsUI.HostRequirementsUI",
        "DeadlineCloud.Offline.DeadlineCloudSavePresetWidget.DeadlineCloudSavePresetWidget"
    )
    foreach ($requiredTest in $requiredTests) {
        if ($startedPaths -notcontains $requiredTest) {
            throw "Required automation test did not run: $requiredTest"
        }
    }
    if (-not $queueDrained) {
        throw "The Unreal automation queue did not report that it drained"
    }
    if ($performedCount -ne $completed.Count) {
        throw "The queue reported $performedCount tests performed but $($completed.Count) completed"
    }
    if ($failed.Count -gt 0) {
        throw "$($failed.Count) DeadlineCloud automation tests did not succeed"
    }

    Write-Host "OFFLINE UNREAL AUTOMATION TESTS SUCCEEDED"
}
catch {
    $runFailure = $_
    Write-Host "OFFLINE UNREAL AUTOMATION TESTS FAILED: $($_.Exception.Message)"
}
finally {
    try {
        if ($runFailure) {
            if ($ueLog) {
                Write-FullLog -Label "UNREAL EDITOR LOG" -Path $ueLog.FullName
            }
            Write-FullLog -Label "UNREAL EDITOR STDOUT" -Path $stdoutPath
            Write-FullLog -Label "UNREAL EDITOR STDERR" -Path $stderrPath
            $uatLog = Find-LatestUatLog
            if ($uatLog) {
                Write-FullLog -Label "UNREAL AUTOMATIONTOOL LOG" -Path $uatLog.FullName
            }
        }
    }
    finally {
        Remove-Item $runRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if ($runFailure) {
    throw $runFailure
}
