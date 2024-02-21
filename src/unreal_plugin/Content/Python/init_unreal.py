# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os
import sys
import unreal

remote_execution = os.getenv("REMOTE_EXECUTION", "False")
if remote_execution != "True":
    unreal.log("INIT DEADLINE CLOUD")

    libraries_path = f"{os.path.dirname(__file__)}/libraries".replace("\\", "/")
    if not os.getenv("DEADLINE_CLOUD") and os.path.exists(libraries_path):
        os.environ["DEADLINE_CLOUD"] = libraries_path

    unreal.log(f'DEADLINE CLOUD PATH: {os.getenv("DEADLINE_CLOUD")}')
    if os.getenv("DEADLINE_CLOUD") and os.environ["DEADLINE_CLOUD"] not in sys.path:
        sys.path.append(os.environ["DEADLINE_CLOUD"])
