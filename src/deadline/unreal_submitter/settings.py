#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os


JOB_TEMPLATE_VERSION = os.getenv("OPEN_JOB_TEMPLATE_VERSION", "jobtemplate-2023-09")
ENVIRONMENT_VERSION = os.getenv("OPEN_JOB_ENVIRONMENT_TEMPLATE_VERSION", "environment-2023-09")

OPENJD_TEMPLATES_DIRECTORY = os.getenv("OPENJD_TEMPLATES_DIRECTORY")

RENDER_JOB_TEMPLATE_DEFAULT_PATH = "render_job.yml"
RENDER_STEP_TEMPLATE_DEFAULT_PATH = "render_step.yml"
LAUNCH_ENVIRONMENT_TEMPLATE_DEFAULT_PATH = "launch_ue_environment.yml"

UGS_RENDER_JOB_TEMPLATE_DEFAULT_PATH = "ugs/ugs_render_job.yml"
UGS_RENDER_STEP_TEMPLATE_DEFAULT_PATH = "ugs/ugs_render_step.yml"
UGS_LAUNCH_ENVIRONMENT_TEMPLATE_DEFAULT_PATH = "ugs/ugs_launch_ue_environment.yml"
UGS_SYNC_CMF_ENVIRONMENT_TEMPLATE_DEFAULT_PATH = "ugs/ugs_sync_cmf_environment.yml"
UGS_SYNC_SMF_ENVIRONMENT_TEMPLATE_DEFAULT_PATH = "ugs/ugs_sync_smf_environment.yml"

P4_RENDER_JOB_TEMPLATE_DEFAULT_PATH = "p4/p4_render_job.yml"
P4_RENDER_STEP_TEMPLATE_DEFAULT_PATH = "p4/p4_render_step.yml"
P4_LAUNCH_ENVIRONMENT_TEMPLATE_DEFAULT_PATH = "p4/p4_launch_ue_environment.yml"
P4_SYNC_CMF_ENVIRONMENT_TEMPLATE_DEFAULT_PATH = "p4/p4_sync_cmf_environment.yml"
P4_SYNC_SMF_ENVIRONMENT_TEMPLATE_DEFAULT_PATH = "p4/p4_sync_smf_environment.yml"
