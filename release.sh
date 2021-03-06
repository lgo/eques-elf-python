#!/bin/sh
# Pushes a new version to PyPi.

# Stop on errors
set -e

python -m build
python -m twine upload dist/* --skip-existing