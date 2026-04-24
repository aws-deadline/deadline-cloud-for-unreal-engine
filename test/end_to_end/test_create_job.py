# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import logging
import os

import yaml
from conftest import (
    extract_job_info_from_test_output,
    find_latest_job_bundle,
    wait_for_job_state,
    cancel_job,
    rename_job,
)

logger = logging.getLogger(__name__)


def test_create_job(deadline_client, build_plugin, create_readonly_test_project, run_unreal_test):
    """Run CreateJob automation test from within Unreal and monitor job status until READY, then cancel it"""

    _, uproject_file = create_readonly_test_project

    logger.info(f"Creating job from project {uproject_file}")
    success, output_lines = run_unreal_test("DeadlineCloud.Integration.CreateJob", uproject_file)
    assert success, "Create job test failed"

    # Extract job ID and farm ID from the output
    job_id, farm_id, queue_id = extract_job_info_from_test_output(output_lines)

    assert job_id
    assert farm_id
    assert queue_id

    rename_job(deadline_client, farm_id, queue_id, job_id, "E2E: Job Bundle Inspection")

    # For checking if a job is in READY state:
    success, status, message = wait_for_job_state(
        deadline_client=deadline_client,
        farm_id=farm_id,
        job_id=job_id,
        queue_id=queue_id,
        expected_states=["READY"],
        max_wait_time=30,
        wait_interval=5,
    )
    assert success

    # --- T8: Job bundle file inspection ---
    bundle_dir = find_latest_job_bundle()
    logger.info(f"Inspecting job bundle: {bundle_dir}")

    # Verify template.yaml contains AdaptorSetup environment
    with open(os.path.join(bundle_dir, "template.yaml"), "r") as f:
        template = yaml.safe_load(f)
    env_names = [e.get("name") for e in template.get("jobEnvironments", [])]
    assert "AdaptorSetup" in env_names, (
        f"AdaptorSetup environment not found in template. Environments: {env_names}"
    )
    logger.info("Confirmed: AdaptorSetup environment in template")

    # Verify parameter_values.yaml has AdaptorBundlePath with a non-empty value
    with open(os.path.join(bundle_dir, "parameter_values.yaml"), "r") as f:
        param_values = yaml.safe_load(f)
    params = {p["name"]: p.get("value") for p in param_values.get("parameterValues", [])}

    assert params.get("AdaptorBundlePath"), (
        f"AdaptorBundlePath is empty or missing. Got: '{params.get('AdaptorBundlePath')}'"
    )
    logger.info(f"Confirmed: AdaptorBundlePath='{params['AdaptorBundlePath']}'")

    # Verify CondaPackages does not contain unrealengine-openjd
    conda_value = params.get("CondaPackages", "")
    assert "unrealengine-openjd" not in conda_value, (
        f"CondaPackages should not contain unrealengine-openjd. Got: '{conda_value}'"
    )
    logger.info(f"Confirmed: CondaPackages='{conda_value}' (no unrealengine-openjd)")

    # Verify asset_references.yaml includes adaptor_bundle in input directories
    asset_refs_path = os.path.join(bundle_dir, "asset_references.yaml")
    with open(asset_refs_path, "r") as f:
        asset_refs = yaml.safe_load(f) or {}
    input_dirs = asset_refs.get("assetReferences", {}).get("inputs", {}).get("directories", [])
    has_bundle = any("adaptor_bundle" in d for d in input_dirs)
    assert has_bundle, (
        f"adaptor_bundle not found in asset_references input directories: {input_dirs}"
    )
    logger.info("Confirmed: adaptor_bundle in asset_references input directories")

    # Once the job is in READY state, cancel it since test_worker_agent.py will handle the full job execution
    logger.info(f"Job {job_id} is in READY state, canceling it...")
    cancel_job(deadline_client, farm_id, queue_id, job_id)
