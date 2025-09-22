#!/bin/sh
# Set the -e option
set -e

pip install --upgrade pip
pip install --upgrade hatch "click<8.3"
pip install --upgrade twine
hatch -v run codebuild:lint
hatch run codebuild:test
hatch -v run codebuild:build