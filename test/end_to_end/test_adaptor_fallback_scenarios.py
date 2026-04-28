# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
E2E tests for adaptor fallback scenarios.

Uses a single UE job submission to generate a job bundle on disk, then modifies
and resubmits it twice via the API to test:
- Conda fallback when no bundle attached (mimics old submitter)
- No bundle + no conda → job fails with clear error
"""

import logging
import os
import re

import yaml
import deadline.client.config as config
from deadline.client.api._submit_job_bundle import create_job_from_job_bundle
from conftest import (
    find_latest_job_bundle,
    get_session_log_events,
    wait_for_job_state,
    rename_job,
)

logger = logging.getLogger(__name__)


def _strip_bundle_from_job(bundle_dir):
    """Remove AdaptorSetup env, clear AdaptorBundlePath, remove bundle from asset refs."""
    # Remove AdaptorSetup environment from template
    template_path = os.path.join(bundle_dir, "template.yaml")
    with open(template_path, "r") as f:
        template = yaml.safe_load(f)
    if "jobEnvironments" in template:
        template["jobEnvironments"] = [
            e for e in template["jobEnvironments"] if e.get("name") != "AdaptorSetup"
        ]
    with open(template_path, "w") as f:
        yaml.dump(template, f)

    # Clear AdaptorBundlePath in parameter_values
    param_values_path = os.path.join(bundle_dir, "parameter_values.yaml")
    with open(param_values_path, "r") as f:
        param_values = yaml.safe_load(f)
    for p in param_values.get("parameterValues", []):
        if p["name"] == "AdaptorBundlePath":
            p["value"] = ""
    with open(param_values_path, "w") as f:
        yaml.dump(param_values, f)

    # Remove adaptor_bundle from asset_references
    asset_refs_path = os.path.join(bundle_dir, "asset_references.yaml")
    if os.path.exists(asset_refs_path):
        with open(asset_refs_path, "r") as f:
            asset_refs = yaml.safe_load(f) or {}
        input_dirs = asset_refs.get("assetReferences", {}).get("inputs", {}).get("directories", [])
        asset_refs.setdefault("assetReferences", {}).setdefault("inputs", {})["directories"] = [
            d for d in input_dirs if "adaptor_bundle" not in d
        ]
        with open(asset_refs_path, "w") as f:
            yaml.dump(asset_refs, f)

    return param_values_path


def test_adaptor_fallback_scenarios(
    deadline_client,
    build_plugin,
    create_readonly_test_project,
    run_unreal_test,
    deadline_worker_agent,
):
    """
    Single UE submission generates a job bundle, then resubmit modified versions:
    1. With unrealengine-openjd in CondaPackages, no bundle → conda fallback
    2. No unrealengine-openjd, no bundle → job fails
    """
    _, uproject_file = create_readonly_test_project

    # Generate job bundle via normal UE submission
    logger.info("Submitting job to generate job bundle on disk")
    success, output_lines = run_unreal_test("DeadlineCloud.Integration.CreateJob", uproject_file)
    assert success, "Create job test failed"

    bundle_dir = find_latest_job_bundle()
    logger.info(f"Using job bundle: {bundle_dir}")

    farm_id = config.get_setting("defaults.farm_id")
    queue_id = config.get_setting("defaults.queue_id")

    # --- Conda fallback (mimics old submitter) ---
    logger.info("Testing conda fallback (no bundle, with unrealengine-openjd)")
    param_values_path = _strip_bundle_from_job(bundle_dir)

    # Add unrealengine-openjd to CondaPackages
    with open(param_values_path, "r") as f:
        param_values = yaml.safe_load(f)
    for p in param_values.get("parameterValues", []):
        if p["name"] == "CondaPackages":
            val = p.get("value", "")
            if "unrealengine-openjd" not in val:
                p["value"] = val + " unrealengine-openjd=0.6.*"
    with open(param_values_path, "w") as f:
        yaml.dump(param_values, f)

    job_id = create_job_from_job_bundle(job_bundle_dir=bundle_dir, max_retries_per_task=0)
    rename_job(deadline_client, farm_id, queue_id, job_id, "E2E: Conda Fallback")
    success, status, message = wait_for_job_state(
        deadline_client=deadline_client,
        farm_id=farm_id,
        job_id=job_id,
        queue_id=queue_id,
        expected_states=["SUCCEEDED"],
        max_wait_time=600,
        wait_interval=10,
    )
    assert success, f"Job did not succeed: {message}"

    log_messages = get_session_log_events(deadline_client, farm_id, queue_id, job_id)
    conda_used = any(
        re.search(r"Adaptor found on PATH via conda, using as fallback", msg)
        for msg in log_messages
    )
    assert conda_used, "Expected conda fallback but log message not found"
    logger.info(f"PASSED: Job {job_id} used conda fallback")

    # --- No bundle, no conda → clear error ---
    logger.info("Testing no adaptor available (no bundle, no conda)")

    # Remove unrealengine-openjd from CondaPackages
    with open(param_values_path, "r") as f:
        param_values = yaml.safe_load(f)
    for p in param_values.get("parameterValues", []):
        if p["name"] == "CondaPackages":
            p["value"] = " ".join(
                tok
                for tok in p.get("value", "").split()
                if not tok.startswith("unrealengine-openjd")
            )
    with open(param_values_path, "w") as f:
        yaml.dump(param_values, f)

    try:
        job_id = create_job_from_job_bundle(job_bundle_dir=bundle_dir, max_retries_per_task=0)
    except Exception as e:
        logger.info(f"PASSED: Submission failed as expected: {e}")
        return

    rename_job(deadline_client, farm_id, queue_id, job_id, "E2E: No Adaptor Available")
    success, status, message = wait_for_job_state(
        deadline_client=deadline_client,
        farm_id=farm_id,
        job_id=job_id,
        queue_id=queue_id,
        expected_states=["FAILED"],
        max_wait_time=300,
        wait_interval=10,
    )
    assert status == "FAILED", f"Expected FAILED but got: {status}"
    logger.info(f"PASSED: Job {job_id} failed when no adaptor available")
