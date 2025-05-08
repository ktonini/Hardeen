# Hardeen - Houdini CLI/GUI Render Manager

Hardeen is a GUI and CLI tool for managing and monitoring Houdini renders, with a focus on Redshift renders.

## Features

- Intuitive GUI for setting up and monitoring renders
- Support for rendering multiple ROPs via merge nodes
- Frame range overrides
- Skip already rendered frames option
- Pushover notifications for render progress and completion
- Image preview for rendered frames including EXR/AOV support
- Shutdown computer after rendering

## Requirements

- Python 3.6+
- PySide6
- Pillow (PIL)
- NumPy
- OpenImageIO
- Houdini (hython must be in your PATH)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/houdini_CLI_GUI.git
cd houdini_CLI_GUI
```

2. Run the launcher script:
```bash
./launch_hardeen.sh
```

The launcher script will:
- Create a virtual environment if it doesn't exist
- Install all required dependencies
- Launch the application

## Usage

### GUI Mode

1. Select a Houdini (.hip) file
2. Select an output node (ROP)
3. Optionally override frame range
4. Click "Render"

### Batch Rendering

For batch rendering multiple ROPs:
1. In Houdini, create a merge node and connect multiple ROPs to it
2. In Hardeen, point to the merge node
3. Each ROP will render with its own frame range

### Shutdown after rendering

Enable the "Shut down computer after render completes" option to automatically power off your computer when rendering is finished.

### Pushover Notifications

To receive mobile notifications:
1. Sign up for a Pushover account (https://pushover.net/)
2. Enter your API key and user key in the notification settings
3. Enable notifications and set the notification interval
