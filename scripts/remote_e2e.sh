#!/bin/bash
# Remote E2E test runner: push code from Linux, pull and run tests on Windows EC2 via SSM
#
# Usage:
#   ./scripts/remote_e2e.sh [test_filter]
#
# Examples:
#   ./scripts/remote_e2e.sh                                    # Run all E2E tests
#   ./scripts/remote_e2e.sh test_adaptor_bundle_priority       # Run specific test

set -euo pipefail

INSTANCE_ID="i-0e113a9b34dc58cf2"
BRANCH=$(git branch --show-current)
TEST_FILTER="${1:-}"

export PATH="/usr/local/bin:$PATH"

echo "=== Remote E2E Test Runner ==="
echo "Branch: $BRANCH"
echo "Test filter: ${TEST_FILTER:-all tests}"
echo ""

# Step 1: Commit and push
echo "--- Pushing code ---"
if ! git diff --quiet || ! git diff --cached --quiet; then
    git add -A
    git commit -s -m "wip: auto-commit for remote E2E testing"
fi
git push origin "$BRANCH" 2>&1 || { echo "ERROR: git push failed"; exit 1; }
echo "Push complete."
echo ""

# Step 2: Build SSM command
# Set USERPROFILE so deadline config is found (SSM runs as SYSTEM)
if [ -n "$TEST_FILTER" ]; then
    HATCH_CMD="hatch run e2e -s -k \\\"$TEST_FILTER\\\""
else
    HATCH_CMD="hatch run e2e -s"
fi

cat > /tmp/ssm_params.json << JSONEOF
{
  "commands": [
    "\$env:USERPROFILE = 'C:\\\\Users\\\\Administrator'",
    "\$env:HOME = 'C:\\\\Users\\\\Administrator'",
    "\$env:HOMEPATH = '\\\\Users\\\\Administrator'",
    "\$env:APPDATA = 'C:\\\\Users\\\\Administrator\\\\AppData\\\\Roaming'",
    "\$env:LOCALAPPDATA = 'C:\\\\Users\\\\Administrator\\\\AppData\\\\Local'",
    "cd C:\\\\Users\\\\Administrator\\\\deadline-cloud-for-unreal-engine-cheriech",
    "git fetch origin",
    "git reset --hard origin/${BRANCH}",
    "${HATCH_CMD} *> C:\\\\Users\\\\Administrator\\\\e2e_test.log 2>&1",
    "\$exitCode = \$LASTEXITCODE",
    "Write-Output '=== LAST 200 LINES ==='",
    "Get-Content C:\\\\Users\\\\Administrator\\\\e2e_test.log -Tail 200",
    "Write-Output \"EXIT_CODE=\$exitCode\"",
    "exit \$exitCode"
  ],
  "executionTimeout": ["3600"]
}
JSONEOF

echo "--- Running tests on Windows EC2 ---"
COMMAND_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunPowerShellScript" \
    --parameters file:///tmp/ssm_params.json \
    --timeout-seconds 3600 \
    --query 'Command.CommandId' \
    --output text 2>&1)

echo "SSM Command ID: $COMMAND_ID"
echo "Polling..."
echo ""

# Step 3: Poll for completion
while true; do
    sleep 30
    STATUS=$(aws ssm get-command-invocation \
        --command-id "$COMMAND_ID" \
        --instance-id "$INSTANCE_ID" \
        --query 'Status' \
        --output text 2>&1)

    echo "  $(date +%H:%M:%S) - $STATUS"

    if [ "$STATUS" != "InProgress" ] && [ "$STATUS" != "Pending" ] && [ "$STATUS" != "Delayed" ]; then
        echo ""
        echo "=== Result: $STATUS ==="
        echo ""
        aws ssm get-command-invocation \
            --command-id "$COMMAND_ID" \
            --instance-id "$INSTANCE_ID" \
            --query 'StandardOutputContent' \
            --output text 2>&1

        STDERR=$(aws ssm get-command-invocation \
            --command-id "$COMMAND_ID" \
            --instance-id "$INSTANCE_ID" \
            --query 'StandardErrorContent' \
            --output text 2>&1)
        if [ -n "$STDERR" ] && [ "$STDERR" != "None" ]; then
            echo ""
            echo "=== STDERR ==="
            echo "$STDERR"
        fi

        echo ""
        echo "Full log: C:\\Users\\Administrator\\e2e_test.log"
        echo "Fetch more: PATH=/usr/local/bin:\$PATH bash scripts/remote_e2e_logs.sh 500"

        if [ "$STATUS" = "Success" ]; then
            exit 0
        else
            exit 1
        fi
    fi
done
