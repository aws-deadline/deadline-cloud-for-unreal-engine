#!/bin/sh
# Set the -e option
set -e

pip install --upgrade pip
pip install --upgrade hatch "click<8.3"
hatch run integ:test