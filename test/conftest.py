# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os

# Tests trigger error paths on purpose. Opt out before any telemetry client is created so
# those expected errors aren't reported as real client errors.
os.environ["DEADLINE_CLOUD_TELEMETRY_OPT_OUT"] = "true"
