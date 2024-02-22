#!/bin/bash
set -xeuo pipefail

python depsBundle.py

rm -f dependency_bundle/deadline_cloud_for_unreal_engine_submitter-deps-windows.zip

cp dependency_bundle/deadline_cloud_for_unreal_engine_submitter-deps.zip dependency_bundle/deadline_cloud_for_unreal_engine_submitter-deps-windows.zip
