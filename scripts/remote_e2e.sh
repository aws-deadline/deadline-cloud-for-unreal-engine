#!/bin/bash
# Remote E2E test runner: push code from Linux, pull and run tests on Windows EC2 via SSM
#
# Usage:
#   ./scripts/remote_e2e.sh [test_filter]
#
# Examples:
#   ./scripts/remote_e2e.sh                                    # Run all E2E tests
#   ./scripts/remote_e2e.sh test_adaptor_bundle_priority       # Run specific test
#   ./scripts/remote_e2e.sh "test_create_job or test_worker"   # Run multiple tests

set -euo pipefail

INSTANCE_ID="i-0e113a9b34dc58cf2"
REMOTE_REPO="C:\\Users\\Administrator\\deadline-cloud-for-unreal-engine-cheriech"
REMOTE_LOG="C:\\Users\\Administrator\\e2e_test.log"
BRANCH=$(git branch --show-current)
TEST_FILTER="${1:-}"
LOCAL_LOG="/tmp/e2e_result_$(date +%Y%m%d_%H%M%S).log"

# Ensure session-manager-plugin is on PATH
export PATH="/usr/local/bin:$PATH"

echo "=== Remote E2E Test Runner ==="
echo "Branch: $BRANCH"
echo "Instance: $INSTANCE_ID"
echo "Test filter: ${TEST_FILTER:-all tests}"
echo ""

# Step 1: Commit and push any uncommitted changes
echo "--- Step 1: Pushing code to origin ---"
if ! git diff --quiet || ! git diff --cached --quiet; then
    git add -A
    git commit -s -m "wip: auto-commit for remote E2E testing"
fi
git push origin "$BRANCH" 2>&1 || { echo "ERROR: git push failed"; exit 1; }
echo "Push complete."
echo ""

# Step 2: Build the test command — write all output to a log file on Windows
if [ -n "$TEST_FILTER" ]; then
    TEST_CMD="hatch run e2e -s -k \\\"$TEST_FILTER\\\" *> $REMOTE_LOG 2>&1"
else
    TEST_CMD="hatch run e2e -s *> $REMOTE_LOG 2>&1"
fi

# Step 3: Send command to Windows via SSM
# The command: pull latest code, run tests, write output to log file
echo "--- Step 2: Running tests on Windows EC2 ---"
REMOTE_SCRIPT="cd $REMOTE_REPO; git fetch origin; git reset --hard origin/$BRANCH; $TEST_CMD; Write-Output \"EXIT_CODE=\$LASTEXITCODE\"; Get-Content $REMOTE_LOG -Tail 200"

COMMAND_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunPowerShellScript" \
    --parameters "{\"commands\":[\"$REMOTE_SCRIPT\"],\"executionTimeout\":[\"3600\"]}" \
    --timeout-seconds 3600 \
    --output json 2>&1 | python3 -c "import sys,json; print(json.load(sys.stdin)['Command']['CommandId'])")

echo "SSM Command ID: $COMMAND_ID"
echo "Waiting for test completion (this may take 10+ minutes)..."
echo "Full log will be at $REMOTE_LOG on the Windows machine"
echo ""

# Step 4: Poll for completion
while true; do
    sleep 15
    RESULT=$(aws ssm get-command-invocation \
        --command-id "$COMMAND_ID" \
        --instance-id "$INSTANCE_ID" \
        --output json 2>&1)

    STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['Status'])")

    if [ "$STATUS" = "InProgress" ] || [ "$STATUS" = "Pending" ] || [ "$STATUS" = "Delayed" ]; then
        echo "  Status: $STATUS ($(date +%H:%M:%S))"
        continue
    fi

    # Terminal state reached
    echo ""
    echo "--- Test Result: $STATUS ---"
    echo ""

    # The SSM output contains the last 200 lines of the log
    STDOUT=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('StandardOutputContent',''))")
    STDERR=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('StandardErrorContent',''))")

    # Save locally
    {
        echo "=== E2E Test Results (last 200 lines) ==="
        echo "Date: $(date)"
        echo "Branch: $BRANCH"
        echo "Test filter: ${TEST_FILTER:-all}"
        echo "Status: $STATUS"
        echo "Full log on Windows: $REMOTE_LOG"
        echo ""
        echo "$STDOUT"
        if [ -n "$STDERR" ]; then
            echo ""
            echo "=== STDERR ==="
            echo "$STDERR"
        fi
    } > "$LOCAL_LOG"

    # Print the tail output (errors are at the end)
    echo "$STDOUT"
    if [ -n "$STDERR" ]; then
        echo ""
        echo "=== STDERR ==="
        echo "$STDERR"
    fi

    echo ""
    echo "Local log: $LOCAL_LOG"
    echo "Full log on Windows: $REMOTE_LOG"

    if [ "$STATUS" = "Success" ]; then
        exit 0
    else
        exit 1
    fi
done
