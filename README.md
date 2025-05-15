# Hardeen - Houdini Render Manager

A modern, user-friendly render manager for Houdini that provides a graphical interface for managing and monitoring renders.

## Features

- **Modern GUI**: Clean and intuitive interface built with PySide6
- **Real-time Progress Visualization**: Live frame-by-frame status with visual indicators
- **AOV/Layer Support**: View and navigate through EXR layers and AOVs
- **Image Preview**: Real-time preview of rendered images
- **Pushover Notifications**: Get notified when renders start, complete, or fail
- **Frame Skipping**: Automatically skip already rendered frames
- **Houdini Integration**: Seamless integration with Houdini's file history and node system
- **Auto Shutdown**: Configure system shutdown after render completion

## Requirements

- Python 3.8+
- Houdini 18.0+
- PySide6 6.4.0+
- requests 2.28.0+
- typing-extensions 4.5.0+

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/hardeen.git
cd hardeen
```

2. Install dependencies:
```bash
pip install .
```

3. (Optional) Set up Pushover notifications:
   - Create a Pushover account at https://pushover.net
   - Create an application to get your API token
   - Enter your API token and user key in the settings window:
     - Open Settings (gear icon)
     - Navigate to "Notifications" tab
     - Enter your Pushover API token and user key

## Usage

1. Run the application:
```bash
python -m hardeen
```

2. Select a Houdini file:
   - The app automatically finds and displays your recently opened Houdini (.hip) files in the dropdown
   - Or browse to select a file

3. Select an output node:
   - The dropdown will show available ROP nodes
   - Frame range will be automatically set from the node

4. Configure render settings:
   - Adjust frame range if needed
   - Enable/disable frame skipping option
   - Configure notification settings
   - Set up shutdown options if desired
   - Click "Render" to begin

5. Monitor progress:
   - View frame-by-frame progress in the visualization
   - Check estimated time remaining
   - Preview rendered images and AOVs in real-time
   - Receive notifications for:
     - Render start
     - Render completion
     - Every N frames (configurable)

## Development

### Project Structure

```
hardeen/
├── __init__.py
├── __main__.py           # Package entry point
├── main.py               # Main application logic
├── config.py             # Configuration settings
├── resources/            # Application resources
│   └── icon.png          # Application icon
├── gui/
│   ├── __init__.py
│   ├── main_window.py    # Main GUI window class
│   ├── settings_dialog.py
│   ├── settings_manager.py
│   ├── notification_manager.py
│   ├── ui_components.py  # Reusable UI components
│   ├── widgets/          # Custom widgets
│   ├── window_components/
│   ├── managers/
│   └── dialogs/
├── core/
│   ├── houdini.py        # Houdini-specific functionality
│   ├── renderer.py       # Render process handling
│   ├── render_manager.py # Manage multiple renders
│   └── notifications.py  # Pushover notification handling
└── utils/
    ├── __init__.py
    ├── time_utils.py     # Time formatting utilities
    ├── settings.py       # Settings management
    └── image_utils.py    # Image processing utilities
```

### Building from Source

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest
```

3. Build distribution packages:
```bash
python -m build
```

This will create distribution packages in the `dist/` directory:
- `.tar.gz`: Source distribution
- `.whl`: Wheel distribution (binary package)

### Creating a Standalone Executable

To create a standalone executable that users can run without installing Python:

1. Install development dependencies as shown above, or install PyInstaller directly:
```bash
pip install pyinstaller
```

2. Create the executable:
```bash
pyinstaller --onefile --windowed --icon=hardeen/resources/icon.png --name=hardeen hardeen/__main__.py
```

This will create a standalone executable in the `dist/` directory.

### TO DO
- Web server UI for remote control
- Drag and drop EXR layer inspection
- Add EXR metadata to track cumulative render time across multiple start/stop cycles for accurate render time reporting
