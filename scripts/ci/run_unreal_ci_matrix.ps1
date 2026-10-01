param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("integration", "e2e")]
    [string]$Suite,

    [string]$SourceRoot = $env:CODEBUILD_SRC_DIR,

    [string[]]$Versions = @()
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

if (-not $SourceRoot) {
    throw "SourceRoot is required"
}

if ($Versions.Count -eq 0) {
    $Versions = if ($env:UE_VERSIONS) {
        @($env:UE_VERSIONS -split "[,;\s]+" | Where-Object { $_ })
    }
    else {
        @("5.6", "5.7", "5.8")
    }
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Description,

        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [string[]]$ArgumentList = @()
    )

    Write-Host "Running: $Description"
    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

function Clear-CmfTestWorkers {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FarmId,

        [Parameter(Mandatory = $true)]
        [string]$FleetId
    )

    $workers = & aws deadline list-workers `
        --farm-id $FarmId `
        --fleet-id $FleetId `
        --region $env:AWS_REGION | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to list existing workers for CMF fleet $FleetId"
    }

    $workersToRemove = @($workers.workers)
    foreach ($worker in $workersToRemove) {
        Write-Host "Removing prior CMF test worker $($worker.workerId) ($($worker.status))"
        if ($worker.status -ne "STOPPED") {
            & aws deadline update-worker `
                --farm-id $FarmId `
                --fleet-id $FleetId `
                --worker-id $worker.workerId `
                --status STOPPED `
                --region $env:AWS_REGION
            if ($LASTEXITCODE -ne 0) {
                throw "Unable to stop prior CMF test worker $($worker.workerId)"
            }
        }

        & aws deadline delete-worker `
            --farm-id $FarmId `
            --fleet-id $FleetId `
            --worker-id $worker.workerId `
            --region $env:AWS_REGION
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to delete prior CMF test worker $($worker.workerId)"
        }
    }

    if ($workersToRemove.Count -eq 0) {
        return
    }

    for ($attempt = 1; $attempt -le 12; $attempt++) {
        Start-Sleep -Seconds 5
        $remaining = & aws deadline list-workers `
            --farm-id $FarmId `
            --fleet-id $FleetId `
            --region $env:AWS_REGION | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to verify worker cleanup for CMF fleet $FleetId"
        }
        if (@($remaining.workers).Count -eq 0) {
            Write-Host "CMF worker records are empty; waiting for fleet capacity to propagate"
            Start-Sleep -Seconds 10
            return
        }
    }

    throw "Timed out waiting for CMF worker cleanup in fleet $FleetId"
}

Push-Location $SourceRoot
try {
    $env:UE_VERSION = $Versions -join " "
    $setupEnvironment = if ($Suite -eq "e2e") { "e2e-ci" } else { "integ-ci" }
    Invoke-Checked `
        -Description "Unreal Engine setup for versions $($Versions -join ', ')" `
        -FilePath "hatch" `
        -ArgumentList @("run", "${setupEnvironment}:setup")

    foreach ($version in $Versions) {
        Write-Host "=== BEGIN UE $version $($Suite.ToUpperInvariant()) ==="
        $env:UE_VERSION = $version

        $buildArgs = @(
            (Join-Path $SourceRoot "scripts\build_plugin.py"),
            "--ueversion=$version",
            "--install",
            "--test"
        )
        if ($Suite -eq "e2e") {
            $buildArgs += "--worker"
        }
        Invoke-Checked `
            -Description "Build and install the plugin for UE $version" `
            -FilePath "python" `
            -ArgumentList $buildArgs

        if ($Suite -eq "integration") {
            Invoke-Checked `
                -Description "Integration tests for UE $version" `
                -FilePath "hatch" `
                -ArgumentList @(
                    "run",
                    "integ-ci:integ",
                    "--",
                    "test/integ",
                    "--ueversion=$version"
                )

            if ($env:RUN_UI_AUTOMATION -eq "true") {
                Invoke-Checked `
                    -Description "Offline Unreal automation tests for UE $version" `
                    -FilePath "powershell.exe" `
                    -ArgumentList @(
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        (Join-Path $SourceRoot "scripts\ci\run_unreal_automation_tests.ps1"),
                        "-SourceRoot",
                        $SourceRoot,
                        "-UEVersion",
                        $version
                    )
            }
        }
        else {
            foreach ($requiredVariable in @(
                "FARM_ID",
                "UNREAL_WORKER_QUEUE_ID",
                "UNREAL_WORKER_FLEET_ID"
            )) {
                if (-not (Get-Item "Env:\$requiredVariable" -ErrorAction SilentlyContinue).Value) {
                    throw "$requiredVariable is required for CMF worker-agent tests"
                }
            }

            Clear-CmfTestWorkers `
                -FarmId $env:FARM_ID `
                -FleetId $env:UNREAL_WORKER_FLEET_ID

            $workerState = Join-Path $SourceRoot "worker-agent-state"
            Remove-Item $workerState -Recurse -Force -ErrorAction SilentlyContinue

            Invoke-Checked `
                -Description "CMF worker-agent tests for UE $version" `
                -FilePath "hatch" `
                -ArgumentList @(
                    "run",
                    "e2e-ci:worker",
                    "--",
                    "test/end_to_end/test_worker_agent.py",
                    "--ueversion=$version",
                    "--farm-id",
                    $env:FARM_ID,
                    "--queue-id",
                    $env:UNREAL_WORKER_QUEUE_ID,
                    "-s"
                )
        }

        Write-Host "=== END UE $version $($Suite.ToUpperInvariant()) ==="
    }
}
finally {
    Pop-Location
}
