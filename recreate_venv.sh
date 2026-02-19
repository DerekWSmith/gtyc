#!/bin/bash

# Recreate virtual environment in current directory
# Usage: ./recreate_venv.sh

# set -e

echo "Removing existing .venv..."
rm -rf .venv

echo "Creating new virtual environment with Python 3.14..."
python3.14 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing requirements..."
pip install -r requirements.txt

echo ""
echo "Done! Virtual environment recreated."
echo "Activate with: source .venv/bin/activate"
