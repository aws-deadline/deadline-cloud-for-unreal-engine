# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import sys


remote_execution = os.getenv("REMOTE_EXECUTION", "False")
if remote_execution != "True":
    from deadline.unreal_logger import get_logger

    logger = get_logger()

    logger.info("INIT DEADLINE CLOUD")

    libraries_path = f"{os.path.dirname(__file__)}/libraries".replace("\\", "/")
    if not os.getenv("DEADLINE_CLOUD") and os.path.exists(libraries_path):
        os.environ["DEADLINE_CLOUD"] = libraries_path

    logger.info(f'DEADLINE CLOUD PATH: {os.getenv("DEADLINE_CLOUD")}')
    if os.getenv("DEADLINE_CLOUD") and os.environ["DEADLINE_CLOUD"] not in sys.path:
        sys.path.append(os.environ["DEADLINE_CLOUD"])

    # These unused imports are REQUIRED!!!
    # Unreal Engine loads any init_unreal.py it finds in its search paths.
    # These imports finish the setup for the plugin.
    from settings import DeadlineCloudDeveloperSettingsImplementation  # noqa: F401
    from job_library import DeadlineCloudJobBundleLibraryImplementation  # noqa: F401
    from open_job_template_api import (  # noqa: F401
        PythonYamlLibraryImplementation,
        ParametersConsistencyChecker
    )
    import remote_executor  # noqa: F401




