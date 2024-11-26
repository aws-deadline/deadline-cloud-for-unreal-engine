# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
from pathlib import Path


remote_execution = os.getenv("REMOTE_EXECUTION", "False")
if remote_execution != "True":
    from deadline.unreal_logger import get_logger

    logger = get_logger()

    logger.info("INIT DEADLINE CLOUD")

    if "OPENJD_TEMPLATES_DIRECTORY" not in os.environ:
        os.environ["OPENJD_TEMPLATES_DIRECTORY"] = (
            f"{Path(__file__).parent.as_posix()}/openjd_templates"
        )

    # These unused imports are REQUIRED!!!
    # Unreal Engine loads any init_unreal.py it finds in its search paths.
    # These imports finish the setup for the plugin.
    from settings import DeadlineCloudDeveloperSettingsImplementation  # noqa: F401
    from job_library import DeadlineCloudJobBundleLibraryImplementation  # noqa: F401
    from open_job_template_api import (  # noqa: F401
        PythonYamlLibraryImplementation,
        ParametersConsistencyCheckerImplementation,
    )
    import remote_executor  # noqa: F401

    logger.info("DEADLINE CLOUD INITIALIZED")
