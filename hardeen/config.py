import os

# Default paths and settings
DEFAULT_FOLDER = '/mnt/Data/active_jobs/'
DEFAULT_OUTNODE = '/out/Redshift_ROP1'
DEFAULT_LOG = DEFAULT_FOLDER + 'hardeen.log'
VERSION_NUM = 'v1.0'

# UI Colors
DISABLED_TEXT_COLOR = "#ff4c00"
COMPLETED_COLOR = "#22adf2"
CURRENT_COLOR = "#ff4c00"
PLACEHOLDER_COLOR = "#444444"
SKIPPED_COLOR = "#666666"

# Application settings
APP_NAME = "Hardeen"
APP_ORGANIZATION = "RenderUtility"
APP_VERSION = "1.0.0"

# File patterns
HIP_FILE_PATTERN = "*.hip"
EXR_FILE_PATTERN = "*.exr"
PNG_FILE_PATTERN = "*.png"

# Notification settings
DEFAULT_NOTIFICATION_INTERVAL = 10

# Shutdown delay options
SHUTDOWN_DELAYS = [
    "No delay",
    "1 minute",
    "5 minutes",
    "10 minutes",
    "30 minutes",
    "1 hour"
]

# Debug settings
DEBUG = os.environ.get('HARDEEN_DEBUG', '0') == '1'
