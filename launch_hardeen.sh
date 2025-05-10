#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Starting Hardeen - Houdini CLI/GUI Render Manager"
echo "================================================="
echo "Working directory: $(pwd)"

# Name of the virtual environment directory
VENV_DIR="hardeen_env"
PYTHON_BIN="python3"

# Check if Python is available
if ! command -v $PYTHON_BIN &>/dev/null; then
    echo "Error: $PYTHON_BIN is not installed or not in PATH."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PYTHON_BIN -m venv "$VENV_DIR"
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Use venv's own Python path
VENV_PY="$VENV_DIR/bin/python"

# Upgrade pip silently
echo "Checking and upgrading pip..."
$VENV_PY -m pip install --upgrade pip >/dev/null 2>&1 || true

# List of required packages
REQUIRED_PACKAGES=(PySide6 Pillow numpy openimageio requests)

# Install missing packages
for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! pip show "$package" >/dev/null 2>&1; then
        echo "Installing $package..."
        pip install "$package" 2>&1 | grep -v "WARNING:" || true
    fi
done

# Launch the application
echo "Starting application..."
$VENV_PY "$SCRIPT_DIR/hardeen.py"

# Deactivate the virtual environment when done
deactivate
echo "Hardeen closed. Environment deactivated."
