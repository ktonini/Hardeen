#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Starting Hardeen - Houdini CLI/GUI Render Manager"
echo "================================================="
echo "Working directory: $(pwd)"

# Check if virtual environment exists, create if not
if [ ! -d "hardeen_env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv hardeen_env
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source hardeen_env/bin/activate

# Check and install dependencies
echo "Checking dependencies..."
# Redirect pip upgrade output to null and handle potential broken pipe
python -m pip install --upgrade pip >/dev/null 2>&1 || true

# Install required packages if they're not already installed
for package in PySide6 Pillow numpy openimageio requests
do
    if ! pip list 2>/dev/null | grep -q "$package"; then
        echo "Installing $package..."
        # Handle pip install output more gracefully
        pip install "$package" 2>&1 | grep -v "WARNING:" || true
    fi
done

echo "Starting application..."
# Launch the application
python "$SCRIPT_DIR/hardeen.py"

# Deactivate the virtual environment when done
deactivate
echo "Hardeen closed. Environment deactivated."
