#!/bin/bash
# Fetch E2E test logs from the Windows EC2 via SSM
#
# Usage:
#   ./scripts/remote_e2e_logs.sh [num_lines]  # Default: last 200 lines
#   ./scripts/remote_e2e_logs.sh 500          # Last 500 lines
#   ./scripts/remote_e2e_logs.sh all          # Full log

set -euo pipefail

INSTANCE_ID="i-0e113a9b34dc58cf2"
REMOTE_LOG="C:\\Users\\Administrator\\e2e_test.log"
LINES="${1:-200}"

export PATH="/usr/local/bin:$PATH"

if [ "$LINES" = "all" ]; then
    CMD="Get-Content $REMOTE_LOG"
else
    CMD="Get-Content $REMOTE_LOG -Tail $LINES"
fi

COMMAND_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunPowerShellScript" \
    --parameters "{\"commands\":[\"$CMD\"]}" \
    --output json 2>&1 | python3 -c "import sys,json; print(json.load(sys.stdin)['Command']['CommandId'])")

sleep 5

RESULT=$(aws ssm get-command-invocation \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    --output json 2>&1)

echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('StandardOutputContent',''))"
