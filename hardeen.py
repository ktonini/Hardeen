#!/usr/bin/python3

import datetime
import os
import re
import signal
import subprocess
import sys
import threading
import time
import json
import traceback
from pathlib import Path
import tempfile
import select

# TEMP
import traceback

import PIL.Image
import OpenImageIO as oiio
import numpy as np

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

try:
    import hou  # Only needed if running inside Houdini
    RUNNING_IN_HOUDINI = True
except ImportError:
    RUNNING_IN_HOUDINI = False

DEFAULT_FOLDER = '/mnt/Data/active_jobs/'
DEFAULT_OUTNODE = '/out/Redshift_ROP1'
DEFAULT_LOG = DEFAULT_FOLDER + 'hardeen.log'
VERSION_NUM = 'v1.0'
disabledTextColor = "#ff4c00"
icon_browse = b'iVBORw0KGgoAAAANSUhEUgAAADkAAABDCAYAAAAmoa0iAAAACXBIWXMAAC4jAAAuIwF4pT92AAAI0ElEQVRogdWbXWwU1xXH/zMeGxPWsFVcyQ+V7AeQ+hCqSSnhI6HYSgmV0sZ2Fbm1AduAQxwCxHy0SSqUpE6NKA9F5KFtqsZ2FFBphETaqm0ekIaShNCoDzR9MXaqAmqLCcG2anuBnbnn9GF2vmfXO+OddfqXRt6dnTszvznnnnvuuWMJOR09NtCImGJm+y8xg3Mb7M8Amd+v9r/y46txrxNXEgAcPTYwBKA77kksKPKAOYD2ZwBVlcqwJEn7D//w5akSMcwp6eixgeMA+uI09oDACweXBWVZglJRAVmWIYhAgi4Loqb+l18tC6gMQI3TMGApym0uqxITmBmViuIGhCBSiYT24uEX0iXmCZUcp5HXHcn73QfLTCBiNyBICAhBKgnSDj1/KHFQxb9j86bNl+vrG0rqRm+feVu9efNmWpBwgToWfe7Ac00nfnoiMdeNZcmoIiIEAQVEzqKCSNu999nELFo2SAtQ2ICUgyeQIFWQ0J7q3ZUIaJkg2YQTBCKB2vtrhQMoLCurgkjr7tlRctAyuqsJKARhxfIV+rcefzxjAroCEpEqhNA6OreVFLR87upyUWLGqge/mm1+ojnjuLHTR4lIa+toLxloAJJLdWaXiMjpg4LATACA1atWZb/T2poRQviOESoRl6yPeiCtHLTUMi3pBB0m5zprVq/Otj35ZMYFCCKCIQx1YnJK27mrZ96gNqSTjs33lEFZN28NI+R7mOvWrMm2f7fNsWiun969d0+9dXti3sFIdmcrxAxOgNKf8YR5zMPr1mW3dnRkrChsDTN3795TP731mda5ozs2qMzMIDK3RN1VWAmByHudDQ+vz3Zt25pxBykhCHfu3FVvjN/StnZ3xgKV/XlnEu4q/BkPUd5jN254JLujqyvjBCJzmLlz54767//c1Do6t0YGVQJzvxJTKoqS8mc8n92+LY9cGVUA57rmZ/P6X6ytpfXr1mb/fOG9KqsNCUJWz6jX/3VD+97WLU2nT54qOtdVvBPd0oBJkqwsXrz4S5WVVXWyLFevWL7CuHrtmm2ZS3/5qOrih5eqhMeNHSvbFvTlukSE2dmMemP80+MAthd7P7Iz90OudDE/wPvuW9KwbFl67aJF1Q2yLFcDwJb2DqX520/A39fCAYUddAIPIde29v4vtES5J9mZ+1mD9PwoFUVJS5IUmMK1NrdgV89TtsuafU14E3d/mhfyEGpqUpAkKVK/lO2JLicXXS1t3PB17H661w4mwgYU9j7PxNoHyMxYWpOK7G2+wFO6fplPTRs34pH168ZnZqZHim3zt4//nv7Z66+r7mpDFMnkg0wme/WqsrKqrqZm6QOSJAfcOkwMK27E8zhX4LFKirHuO7IUpbK2pmapWjSop0AWA9KzxbrlwhofHw/dX1FRkSoKlBEokEWRHGxcesw//On3+ODi+6G/FQPqqenm7jeKZKs2ajdOIq0zBH77u7M4/Ztfh/5ugSqKkgo9wB7DY/dJ3wkiI8wtwzCg6wY+vHQRJ0+9FXpMRUVFKpXKD+ruj7ECj7dDlx7ThNSh6zre/+A9DL85FHqcJElKGKjpruQJPlEkByrgSbirEDakoeu4cOE8fvXGL5HJZALHhoLai0YUfwiJ27hYuS2p66brapqG/ld/hNnMbOB4C7SqalGttc+/QhZFsjlZRqLR1TBEzopuWB2f/GMML710GLOz4aBLlqQeqK6urmNYE/t5WJJcuWEi7poLPG5Ay6pjY2N44cXnMTs7E9p28eIlX06laurs/kjmAlIUeWs8ERsXK0MYMHxwuu7sGx29goOHDuZNGtY+tKbuG48+6nHZKJLdAYcTKmRZ7ups2YBFR0ZGsGPndoyNjYWe41BfH7Z1dNjxI4pckLn5ZGLu6rWiruvQs9Z3E3pychLP7O7F6Oho6Hm2bdmC7x84EG8WEje7L1aGPYT4+qWhB/ZPTkyip2cnrlwJn4lt3rQJPzh4MNL1A8lAEqBGSOAxwqBz28TEBDq7unDu3LnQ833zscfAzOEZRYhk79J3OcbJoPUccMMFehtP9+7CmTNn8p22m5nPMvOcpRBvZSChyaTIBR5rqLKGK3PJgJwx0PqdyV5O2L+/D0SEtra2sFO3AGhg5iZJkvKWKJWwd29KLcuSNiBxDo68+2xIB1oQYc+eZyGEQHt7e9jpVQBaIVC7MlC+wOOOrGGua0DPZgN9t7e3F0eOHMl3CQs01HXtBN0OPAlAujOeQkmBe7+h68j6HkB/fz96enrmAg28l6QEEt/E3DVrLiq5XTLXJ+19lsuG7cttg4ODEEJgaCg0uLpd97ILEmWIrgK6brhu3BVsOBzGBPXm1ZaGh4cBIB9o2g8quzP7pCoDQviHC8OXDAQ3QzdgGAZEnqW+4eFhtLa2YmoqNNZYoCrgGUKA3Oy05JCGYfYxv8XcVly5ciX27duH+vr6oj2qoaEB6XTeYdIC3R7skwnI8IyTXrdkZnR2dmJwcDCJS6cBTAXXJxMpf1jjpH/uymhubk4KEACuSpJ0PrAWcu369RTDKk2y9QeubwV/W/21h5RlS5d6rmQFHv/MXlXVfMGjVDoBAIrzroBpyT++++7yQFXdP+d0pYH+334yICvrFzpgzSDiFvpdBqaphXqU6XQO0DYqhZ8Q4q7cmDNygu0KUaFAEfHPsHx115zHhyct6CthwoAb/zi500AptzjYT4pzPwmMzcGLOZ73TownrqmaFGD1tDQEFQ1+ML09MwMevfuxfT0dP7rmhqWJOl8sdeTT588NczM2wMnDXkD2V/g9ZfurcrfXIAtLcHV8OmZGTyzZy+m/zsN//TPD/jxXz8q+n2BRMTMGvvU2NjIALi7u9v/k1uR3gNYUOWDbGlpKQTYvdD3HUlhkH19fTw5OZkPMNExJBGFQRbQ2XLcU1le6s2jy4jwwtF8tFCQUwAK1mVKqYWALCsgsDCQ+4vJUj7XmiPwxPrHt8+dCkD+/w0V+cTMDcz8CjP/0wWoLfR9JSZmVnPAZfkXwnz6Hwz9HLxOWD5rAAAAAElFTkSuQmCC'
checkerboard = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00@\x00\x00\x00@\x08\x02\x00\x00\x00\x15\x0bg\x00\x00\x00\x04sBIT\x08\x08\x08\xdb\xe5O\xe7\x00\x00\x00\xaeIDATx\x9c\xed\x9d;\x0e\xc20\x10\xbd\xf7\xbf\xd9\xff\x1e\xc5\xa2j\xf9"\x17\x15\x8d\x81L\r\xd9\x9a\x1aP\x00\x00\x00\x00IEND\xaeB`\x82'
renderedImage = None

dir_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(dir_path)

if os.path.exists('houdini_cli_temp.py'):
    os.remove('houdini_cli_temp.py')
else:
    pass

def create_temp_python_file():
    """Create the temporary Python file for Houdini"""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    temp_file = os.path.join(dir_path, 'hardeen_temp.py')

    if os.path.exists(temp_file):
        os.remove(temp_file)

    with open(temp_file, 'w') as f:
        f.write('''#!/usr/bin/env python3

import os
import stat
import signal
import sys
from optparse import OptionParser

# Global flag to indicate if we should stop rendering
STOP_RENDERING = False

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    global STOP_RENDERING
    if sig == signal.SIGUSR1:
        print("Received interrupt signal. Will stop after current frame completes.")
        STOP_RENDERING = True
    elif sig == signal.SIGTERM:
        print("Received termination signal. Exiting.")
        sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGUSR1, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def initRender(out, sframe, eframe, userange, useskip, step=1):
    global STOP_RENDERING
    import hou
    rnode = hou.node(out)

    # Set Redshift log verbosity for Alfred-style progress
    if rnode.parm('prerender') is not None:
        rnode.parm('prerender').set('Redshift_setLogLevel -L 5')

    def dataHelper(rop_node, render_event_type, frame):
        if render_event_type == hou.ropRenderEventType.PostFrame:
            output_file = rnode.evalParm("RS_outputFileNamePrefix")
            print(f"hardeen_outputfile: {output_file}")

    rnode.addRenderEventCallback(dataHelper)

    parm_skip = rnode.parm("RS_outputSkipRendered")
    if parm_skip is not None:
        # Convert useskip string to boolean
        skip_enabled = useskip.lower() == "true"
        if skip_enabled:
            parm_skip.set(1)
        else:
            parm_skip.set(0)

    if "merge" in str(rnode.type()).lower():
        rnode.render()
        if userange == "True":
            print("hardeen_note: Out Path leads to a merge node, but you have selected to override the frame range. "
                  "Defaulting to the frame range that was set from within Houdini for each ROP.")
    else:
        if userange == "True":
            # Create a list of frames to render based on step
            frames = list(range(int(sframe), int(eframe) + 1, int(step)))

            # Set the frame range parameters to match our actual frame list
            rnode.parm("f1").set(frames[0])  # First frame in our list
            rnode.parm("f2").set(frames[-1])  # Last frame in our list
            rnode.parm("f3").set(int(step))  # Set frame step

            # Render each frame individually to ensure proper stepping
            for frame in frames:
                # Check if we should stop rendering
                if STOP_RENDERING:
                    print("Interrupt detected - stopping render after current frame.")
                    break

                rnode.render(frame_range=(frame, frame))
        else:
            rnode.render(frame_range=(rnode.parm("f1").eval(), rnode.parm("f2").eval()))

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-i", "--hip", dest="hipfile", help="path to .hip file")
    parser.add_option("-o", "--out", dest="outnode", help="path to out node")
    parser.add_option("-s", "--sframe", dest="startframe", help="start frame to render")
    parser.add_option("-e", "--eframe", dest="endframe", help="end frame to render")
    parser.add_option("-u", "--userange", dest="userange", help="toggle to enable frame range")
    parser.add_option("-r", "--useskip", dest="useskip", help="toggle to skip rendering of already rendered frames")
    parser.add_option("-t", "--step", dest="step", help="render every Nth frame", default="1")

    (options, args) = parser.parse_args()

    # Convert hip file path to absolute and verify it exists
    hip_file = os.path.abspath(options.hipfile.strip())  # Strip whitespace and newlines
    hip_dir = os.path.dirname(hip_file)

    print(f"Current working directory: {os.getcwd()}")
    print(f"Hip file path: {hip_file}")
    print(f"Hip directory: {hip_dir}")

    # Detailed file checks
    exists = os.path.exists(hip_file)
    print(f"File exists: {exists}")

    if exists:
        st = os.stat(hip_file)
        print(f"File mode: {stat.filemode(st.st_mode)}")
        print(f"File owner: {st.st_uid}")
        print(f"File group: {st.st_gid}")
        print(f"File size: {st.st_size}")
    else:
        print("Checking parent directory...")
        parent_dir = os.path.dirname(hip_file)
        if os.path.exists(parent_dir):
            print(f"Parent directory exists")
            try:
                files = os.listdir(parent_dir)
                print(f"Directory contents: {files}")
            except Exception as e:
                print(f"Error listing directory: {e}")
        else:
            print(f"Parent directory does not exist")

    print(f"File is readable: {os.access(hip_file, os.R_OK)}")
    print(f"Current user ID: {os.getuid()}")
    print(f"Current group ID: {os.getgid()}")

    try:
        with open(hip_file, 'rb') as f:
            print("Successfully opened file for reading")
            print(f"First few bytes: {f.read(10)}")
    except Exception as e:
        print(f"Error opening file: {e}")

    # Change to the hip file directory before loading
    os.chdir(hip_dir)

    import hou
    hou.hipFile.load(hip_file)

    initRender(options.outnode.strip(),  # Strip other arguments too
              int(options.startframe),
              int(options.endframe),
              options.userange,
              options.useskip,
              int(options.step))
''')

def format_time(seconds):

    timedelta = datetime.timedelta(seconds=seconds)
    days = timedelta.days
    hours, remainder = divmod(timedelta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not any((days, hours, minutes)):
        parts.append(f"{seconds}s")
    return "".join(parts)


class Settings:
    """Wrapper for QSettings to handle lists and other data types"""
    def __init__(self):
        self.settings = QSettings('HoudiniCLI', 'RenderUtility')

    def get(self, key, default=None):
        """Get a value from settings"""
        value = self.settings.value(key, default)

        # Convert string booleans back to bool
        if isinstance(value, str):
            if value.lower() == 'true':
                return True
            elif value.lower() == 'false':
                return False

        return value if value is not None else default

    def set(self, key, value):
        """Save a value to settings"""
        self.settings.setValue(key, value)

    def get_list(self, key, default=None):
        """Get a list from settings"""
        value = self.settings.value(key, default or [])
        if isinstance(value, str):
            # Handle single string value
            return [value] if value else []
        return value if isinstance(value, list) else []

class LoadingComboBox(QComboBox):
    """Custom ComboBox with loading state"""
    loading_state_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False  # Use private variable
        self.loading_dots = 0
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading_text)

    @property
    def loading(self):
        return self._loading

    def start_loading(self):
        """Start loading animation"""
        self._loading = True
        self.loading_dots = 0
        self.loading_timer.start(300)
        self.setEnabled(False)
        self.update_loading_text()
        self.loading_state_changed.emit(True)

    def stop_loading(self):
        """Stop loading animation"""
        self._loading = False
        self.loading_timer.stop()
        self.setEnabled(True)
        self.loading_state_changed.emit(False)

    def update_loading_text(self):
        """Update the loading animation dots"""
        self.loading_dots = (self.loading_dots + 1) % 4
        dots = "." * self.loading_dots
        self.setEditText(f"Loading{dots}")

class HipFilesLoader(QThread):
    """Thread for loading hip files"""
    finished = Signal(list)

    def run(self):
        hip_files = refresh_hip_files()
        self.finished.emit(hip_files)

class FrameProgressWidget(QWidget):
    """Custom widget to display frame progress with variable-height bars"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(50)  # Set minimum height for the bar graph
        self.setMinimumWidth(100)

        # Frame data
        self.frame_times = {}  # Dictionary mapping frame numbers to render times
        self.total_frames = 0
        self.current_frame = None  # Changed to None to indicate no current frame
        self.current_frame_progress = 0  # 0-100%
        self.max_time = 1.0  # To normalize bar heights
        self.placeholder_height = 5  # Height of placeholder bars
        self.estimated_current_frame_time = 0.0  # Estimated time for current frame
        self.frame_range = None  # Store the frame range when using step frames
        self.frame_to_index = {}  # Mapping from frame numbers to widget positions
        self.index_to_frame = {}  # Reverse mapping from widget positions to frame numbers

        # Colors
        self.completed_color = QColor("#22adf2")  # Blue for completed frames
        self.current_color = QColor("#ff4c00")    # Orange for current frame
        self.placeholder_color = QColor("#444444")  # Dark gray for placeholder
        self.skipped_color = QColor("#666666")    # Lighter gray for skipped frames

        # Set background color
        self.setStyleSheet("background-color: #222222; border: 1px solid #555555; border-radius: 3px;")

        # Enable tooltip
        self.setMouseTracking(True)

        # Current position for tooltips
        self.hover_position = -1

    def event(self, event):
        """Custom event handler for tooltips"""
        if event.type() == QEvent.Type.ToolTip:
            # Get mouse position
            pos = event.pos()
            frame_info = self.get_frame_info_at_position(pos)

            if frame_info:
                QToolTip.showText(event.globalPos(), frame_info)
            else:
                QToolTip.hideText()
                event.ignore()

            return True

        return super().event(event)

    def get_frame_info_at_position(self, pos):
        """Get frame information at the given position"""
        if self.total_frames <= 0:
            return "No frames to display"

        # Calculate which frame bar is under the cursor
        bar_width = self.width() / self.total_frames
        widget_pos = int(pos.x() / bar_width)

        if widget_pos < 0 or widget_pos >= self.total_frames:
            return None

        # Get actual frame number if we have frame_range mapping
        if self.frame_range and widget_pos in self.index_to_frame:
            frame_number = self.index_to_frame[widget_pos]
        else:
            # If no frame range mapping, adjust for 1-based frame numbers
            frame_number = widget_pos + 1

        # Create tooltip based on frame status
        if widget_pos == self.current_frame:
            # Current frame in progress
            tooltip = f"Frame {frame_number} - In progress\n"
            tooltip += f"Progress: {self.current_frame_progress}%"
            if self.estimated_current_frame_time > 0:
                tooltip += f"\nEstimated time: {self.format_time(self.estimated_current_frame_time)}"
            return tooltip

        elif widget_pos in self.frame_times:
            # Completed or skipped frame
            time = self.frame_times[widget_pos]
            if time > 0:
                # Completed frame
                return f"Frame {frame_number}\nRender time: {self.format_time(time)}"
            else:
                # Skipped frame
                return f"Frame {frame_number} - Skipped\nFile already exists"
        else:
            # Not yet rendered
            return f"Frame {frame_number} - Pending"

    def set_total_frames(self, total, frame_range=None):
        """Set the total number of frames and optionally the frame range"""
        self.total_frames = total
        if frame_range:
            self.frame_range = frame_range
            # Create bidirectional mappings
            self.frame_to_index = {frame: i for i, frame in enumerate(frame_range)}
            self.index_to_frame = {i: frame for i, frame in enumerate(frame_range)}
        else:
            self.frame_range = None
            self.frame_to_index = {}
            self.index_to_frame = {}
        self.update()

    def update_frame_progress(self, frame, progress, estimated_time=None):
        """Update the progress of the current frame (0-100%)"""
        # Store the frame number directly
        self.current_frame = frame
        self.current_frame_progress = progress

        # If progress is 100%, move this frame to completed frames
        if progress >= 100:
            if estimated_time is not None:
                self.frame_times[frame] = estimated_time
            self.current_frame = None  # Clear current frame
            self.current_frame_progress = 0

        # If we have an estimated time, update it
        elif estimated_time is not None:
            self.estimated_current_frame_time = estimated_time
            if estimated_time > self.max_time:
                self.max_time = estimated_time

        self.update()

    def add_frame_time(self, frame, time):
        """Add a completed frame and its render time"""
        self.frame_times[frame] = time
        self.max_time = max(self.max_time, time)  # Update max time for scaling
        # Clear current frame if this was the current frame
        if frame == self.current_frame:
            self.current_frame = None
            self.current_frame_progress = 0
        self.update()

    def set_frame_skipped(self, frame):
        """Mark a frame as skipped (will use a placeholder bar)"""
        self.frame_times[frame] = 0  # Skipped frames get 0 time
        # Clear current frame if this was the current frame
        if frame == self.current_frame:
            self.current_frame = None
            self.current_frame_progress = 0
        self.update()

    def clear(self):
        """Clear all frame data"""
        self.frame_times.clear()
        self.current_frame = None  # Changed to None
        self.current_frame_progress = 0
        self.max_time = 1.0
        self.estimated_current_frame_time = 0.0
        self.frame_range = None
        self.frame_to_index = {}
        self.index_to_frame = {}
        self.update()

    def paintEvent(self, event):
        """Paint the frame progress bars"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), QColor("#222222"))

        if self.total_frames <= 0:
            return

        # Calculate bar width
        bar_width = self.width() / self.total_frames
        # Ensure there's a minimum width
        bar_width = max(3, bar_width)
        # Allow for tiny 1px spacing between bars if they're wide enough
        spacing = 1 if bar_width >= 5 else 0

        # Use full height for bars since we removed the text
        available_height = self.height()

        # Draw frame bars
        for widget_pos in range(self.total_frames):
            x = widget_pos * bar_width

            # Skip this frame position if it would be too small to see
            if x + bar_width <= 0 or x >= self.width():
                continue

            if widget_pos == self.current_frame:
                # Current frame gets an orange bar that grows with progress
                # If we have an estimated time, use that to determine the height
                if self.estimated_current_frame_time > 0:
                    # Calculate estimated height based on progress and estimated time
                    estimated_height = min((self.estimated_current_frame_time / self.max_time) * available_height, available_height)
                    # Scale the estimated height by the current progress, but start from placeholder height
                    progress_ratio = self.current_frame_progress / 100.0
                    height = self.placeholder_height + (progress_ratio * (estimated_height - self.placeholder_height))
                else:
                    # If no estimated time, fall back to progress-based height starting from placeholder
                    progress_ratio = self.current_frame_progress / 100.0
                    height = self.placeholder_height + (progress_ratio * (available_height - self.placeholder_height))

                painter.fillRect(
                    QRectF(x, self.height() - height, bar_width - spacing, height),
                    self.current_color
                )
            elif widget_pos in self.frame_times:
                time = self.frame_times[widget_pos]
                if time > 0:
                    # Completed frame - blue bar with height based on render time
                    height = min((time / self.max_time) * available_height, available_height)
                    painter.fillRect(
                        QRectF(x, self.height() - height, bar_width - spacing, height),
                        self.completed_color
                    )
                else:
                    # Skipped frame - small placeholder bar with lighter color
                    painter.fillRect(
                        QRectF(x, self.height() - self.placeholder_height, bar_width - spacing, self.placeholder_height),
                        self.skipped_color
                    )
            else:
                # Not yet rendered - tiny placeholder bar
                painter.fillRect(
                    QRectF(x, self.height() - self.placeholder_height, bar_width - spacing, self.placeholder_height),
                    self.placeholder_color
                )

    def format_time(self, seconds):
        """Format time in seconds to human readable string"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            seconds = seconds % 60
            return f"{minutes}m {seconds:.1f}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            seconds = seconds % 60
            return f"{hours}h {minutes}m {seconds:.1f}s"

class HoudiniRenderGUI(QMainWindow):
    # Define signals for thread-safe UI updates
    output_signal = Signal(str)
    raw_output_signal = Signal(str)
    progress_signal = Signal(int, int)
    frame_progress_signal = Signal(int, int)  # New signal for per-frame progress
    frame_completed_signal = Signal(int, float)  # New signal for completed frames
    frame_skipped_signal = Signal(int)  # New signal for skipped frames
    image_update_signal = Signal(str)
    render_finished_signal = Signal()
    time_labels_signal = Signal(float, float, float, float, QDateTime, bool)
    resize_needed_signal = Signal()  # New signal for resize events

    def __init__(self):
        super().__init__()

        # Add text update queues and locks
        self.summary_update_queue = []
        self.raw_update_queue = []
        self.summary_update_lock = threading.Lock()
        self.raw_update_lock = threading.Lock()

        # Create timers for processing updates
        self.summary_update_timer = QTimer()
        self.raw_update_timer = QTimer()
        self.summary_update_timer.timeout.connect(self.process_summary_updates)
        self.raw_update_timer.timeout.connect(self.process_raw_updates)
        self.summary_update_timer.start(50)  # Process updates every 50ms
        self.raw_update_timer.start(50)

        # Set initial window size
        self.resize(1200, 800)  # Set default window size to 1200x800

        # First create all widgets
        self.setWindowTitle("Hardeen")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #3a3a3a;
                color: #d6d6d6;
            }
            QLabel {
                color: #d6d6d6;
            }
            QLineEdit {
                background-color: #131313;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px;
            }
            QComboBox {
                background-color: #131313;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px;
                padding-right: 15px;  /* Make room for arrow */
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
            QComboBox:hover {
                border: 1px solid #ff4c00;
            }
            QComboBox:on {  /* When the combo box is open */
                border: 1px solid #ff4c00;
            }
            QCheckBox {
                color: #d6d6d6;
            }
            QPushButton {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
                color: #ffffff;
            }
            QProgressBar {
                background-color: #222222;
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #D0D0D0;
                border-radius: 2px;
            }
            QTextEdit {
                background-color: #131313;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px;
            }
            QFrame {
                border-radius: 3px;
            }
        """)

        self.settings = Settings()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Create all widgets first
        # Hip input widgets
        self.hip_input = LoadingComboBox()
        self.hip_input.setEditable(True)
        self.hip_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.hip_input.setMinimumWidth(300)
        self.hip_input.setMaxVisibleItems(10)
        self.hip_input.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.hip_input.setDuplicatesEnabled(False)
        self.hip_input.setPlaceholderText("Enter HIP file path")
        self.hip_input.currentIndexChanged.connect(self.on_hip_selection_changed)

        self.refresh_hip_btn = QPushButton()
        self.refresh_hip_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_hip_btn.setToolTip("Refresh recent HIP files")
        self.refresh_hip_btn.clicked.connect(self.refresh_hip_list)
        self.refresh_hip_btn.setFixedWidth(30)

        # Out input widgets
        self.out_input = LoadingComboBox()  # Changed from QComboBox to LoadingComboBox
        self.out_input.setEditable(True)
        self.out_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.out_input.setMinimumWidth(300)
        self.out_input.setMaxVisibleItems(10)
        self.out_input.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.out_input.setDuplicatesEnabled(False)
        self.out_input.setPlaceholderText("Enter out node path")

        self.refresh_out_btn = QPushButton()
        self.refresh_out_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_out_btn.setToolTip("Refresh out nodes from HIP file")
        self.refresh_out_btn.clicked.connect(self.refresh_out_nodes)
        self.refresh_out_btn.setFixedWidth(30)

        # Frame range widgets
        self.range_check = QCheckBox("Frame Range:")
        self.range_check.stateChanged.connect(self.toggle_frame_range)

        self.start_frame = QLineEdit()
        self.start_frame.setPlaceholderText("Start")
        self.start_frame.setFixedWidth(80)
        self.start_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.start_frame.setText("0")

        self.end_frame = QLineEdit()
        self.end_frame.setPlaceholderText("End")
        self.end_frame.setFixedWidth(80)
        self.end_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.end_frame.setText("100")

        # Replace frame step line edit with combo box
        self.frame_step = QComboBox()
        self.frame_step.setEditable(True)
        self.frame_step.setFixedWidth(80)
        self.frame_step.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frame_step.addItems(["1", "2", "3", "4", "5", "10"])
        self.frame_step.setCurrentText("1")
        self.frame_step.setToolTip("Render every Nth frame")

        # Skip frames widget
        self.skip_check = QCheckBox("Skip Rendered Frames")
        self.skip_check.setChecked(False)

        # Now create layouts
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setSpacing(0)

        # Create form layout
        self.form_layout = QFormLayout()
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(6)

        # Create hip layout
        hip_layout = QHBoxLayout()
        hip_layout.addWidget(self.hip_input)
        hip_layout.addWidget(self.refresh_hip_btn)
        self.form_layout.addRow("Hip Path:", hip_layout)

        # Create out layout
        out_layout = QHBoxLayout()
        out_layout.addWidget(self.out_input)
        out_layout.addWidget(self.refresh_out_btn)
        self.form_layout.addRow("Out Path:", out_layout)

        # Add form layout to main layout
        self.layout.addLayout(self.form_layout)

        # Create Overrides group
        overrides_group = QGroupBox("Overrides")
        overrides_group.setStyleSheet("""
            QGroupBox {
                color: #d6d6d6;
                border: 1px solid #555555;
                border-radius: 3px;
                margin-top: 6px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 7px;
                padding: 0 3px;
            }
        """)
        overrides_layout = QVBoxLayout(overrides_group)
        overrides_layout.setSpacing(6)
        overrides_layout.setContentsMargins(6, 6, 6, 6)

        # Add frame range layout to overrides
        frame_range_layout = QHBoxLayout()
        frame_range_layout.setContentsMargins(0, 0, 0, 0)
        frame_range_layout.setSpacing(6)
        frame_range_layout.addWidget(self.range_check)
        frame_range_layout.addWidget(self.start_frame)
        to_label = QLabel("to")
        to_label.setFixedWidth(20)
        to_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_range_layout.addWidget(to_label)
        frame_range_layout.addWidget(self.end_frame)
        by_label = QLabel("by")
        by_label.setFixedWidth(20)
        by_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_range_layout.addWidget(by_label)
        frame_range_layout.addWidget(self.frame_step)
        frame_range_layout.addStretch()
        overrides_layout.addLayout(frame_range_layout)

        # Add skip frames layout to overrides
        skip_frames_layout = QHBoxLayout()
        skip_frames_layout.setContentsMargins(0, 0, 0, 0)
        skip_frames_layout.setSpacing(6)
        skip_frames_layout.addWidget(self.skip_check)
        skip_frames_layout.addStretch()
        overrides_layout.addLayout(skip_frames_layout)

        # Add overrides group to main layout
        self.layout.addWidget(overrides_group)
        self.layout.addSpacing(6)  # Add 6 pixels of space after the overrides group

        # After overrides group and before the buttons layout, add:

        # Create Notifications group
        notifications_group = QGroupBox("Pushover Notifications")
        notifications_group.setStyleSheet("""
            QGroupBox {
                color: #d6d6d6;
                border: 1px solid #555555;
                border-radius: 3px;
                margin-top: 6px;
                padding-top: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 7px;
                padding: 0 3px;
            }
        """)
        notifications_layout = QVBoxLayout(notifications_group)
        notifications_layout.setSpacing(4)  # Reduced spacing
        notifications_layout.setContentsMargins(6, 6, 6, 6)

        # Create horizontal layout for checkbox and frame input
        notify_frame_layout = QHBoxLayout()
        notify_frame_layout.setSpacing(4)  # Add consistent spacing
        self.notify_check = QCheckBox("Enable notifications every")
        self.notify_frames = QLineEdit()
        self.notify_frames.setPlaceholderText("10")
        self.notify_frames.setFixedWidth(60)
        self.notify_frames.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notify_frames.setEnabled(False)
        self.notify_frames_suffix = QLabel("frames")
        notify_frame_layout.addWidget(self.notify_check)
        notify_frame_layout.addWidget(self.notify_frames)
        notify_frame_layout.addWidget(self.notify_frames_suffix)
        notify_frame_layout.addStretch()

        # Add API key input with consistent spacing
        api_key_layout = QHBoxLayout()
        api_key_layout.setSpacing(4)  # Add consistent spacing
        self.api_key_label = QLabel("API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your Pushover API key")
        self.api_key_input.setEnabled(False)
        api_key_layout.addWidget(self.api_key_label)
        api_key_layout.addWidget(self.api_key_input)

        # Add user key input with consistent spacing
        user_key_layout = QHBoxLayout()
        user_key_layout.setSpacing(4)  # Add consistent spacing
        self.user_key_label = QLabel("User Key:")
        self.user_key_input = QLineEdit()
        self.user_key_input.setPlaceholderText("Enter your Pushover user key")
        self.user_key_input.setEnabled(False)
        user_key_layout.addWidget(self.user_key_label)
        user_key_layout.addWidget(self.user_key_input)

        # Add all layouts to notifications group
        notifications_layout.addLayout(notify_frame_layout)
        notifications_layout.addLayout(api_key_layout)
        notifications_layout.addLayout(user_key_layout)

        # Add notifications group to main layout
        self.layout.addWidget(notifications_group)
        self.layout.addSpacing(6)  # Consistent spacing after group

        # Add specific styling for the frame range inputs and frame step combo box
        frame_input_style = """
            QLineEdit {
                background-color: #131313;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px;
            }
            QLineEdit:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #444444;
            }
        """

        frame_step_style = """
            QComboBox {
                background-color: #131313;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px;
            }
            QComboBox:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #444444;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
                background-color: #555555;
            }
            QComboBox::drop-down:disabled {
                background-color: #444444;
            }
            QComboBox QAbstractItemView {
                background-color: #131313;
                color: #ffffff;
                selection-background-color: #ff4c00;
                selection-color: #ffffff;
            }
            QComboBox:hover {
                border: 1px solid #ff4c00;
            }
            QLineEdit:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #444444;
            }
        """

        # Add notifications group to main layout
        self.layout.addWidget(notifications_group)
        self.layout.addSpacing(6)  # Consistent spacing after group

        # Add shutdown after render area below notifications group
        shutdown_layout = QHBoxLayout()
        self.shutdown_check = QCheckBox("Shut down computer after render completes")
        shutdown_layout.addWidget(self.shutdown_check)
        shutdown_layout.addSpacing(10)
        shutdown_layout.addWidget(QLabel("Delay:"))
        self.shutdown_delay = QComboBox()
        self.shutdown_delay.addItems([
            "No delay",
            "1 minute",
            "5 minutes",
            "10 minutes",
            "30 minutes",
            "1 hour"
        ])
        self.shutdown_delay.setCurrentIndex(0)
        # Apply the same style as frame_step
        self.shutdown_delay.setStyleSheet(frame_step_style)
        shutdown_layout.addWidget(self.shutdown_delay)
        shutdown_layout.addWidget(QLabel("after render"))
        shutdown_layout.addSpacing(10)
        self.test_shutdown_btn = QPushButton("Test Shutdown")
        self.test_shutdown_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4c00;
                color: #000000;
                border: 1px solid #ff4c00;
                border-radius: 3px;
                padding: 5px 15px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #ff6b2b;
            }
            QPushButton:pressed {
                background-color: #cc3d00;
            }
        """)
        self.test_shutdown_btn.clicked.connect(self.test_shutdown)
        shutdown_layout.addWidget(self.test_shutdown_btn)
        shutdown_layout.addStretch()
        self.layout.addLayout(shutdown_layout)

        # Then add buttons layout
        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)

        self.switch_btn = QPushButton("View Raw Output")  # Changed from "View Output"
        self.buttons_layout.addWidget(self.switch_btn)
        self.switch_btn.clicked.connect(self.switch_output)

        self.open_folder_btn = QPushButton("Open Output Location")
        self.buttons_layout.addWidget(self.open_folder_btn)
        self.open_folder_btn.clicked.connect(self.open_folder)
        self.open_folder_btn.setEnabled(False)

        self.cancel_btn = QPushButton("Interrupt")
        self.buttons_layout.addWidget(self.cancel_btn)
        self.cancel_btn.clicked.connect(self.cancel_render)
        self.cancel_btn.setStyleSheet("background-color: #ff4c00; color: #000000;")
        self.cancel_btn.hide()

        self.render_btn = QPushButton("Render")
        self.render_btn.clicked.connect(self.start_render)
        self.render_btn.setStyleSheet("background-color: #ff4c00; color: #000000;")
        self.render_btn.setEnabled(False)  # Disabled by default
        self.buttons_layout.addWidget(self.render_btn)  # Add this line back

        # Connect out_input signals before loading settings
        self.out_input.loading_state_changed.connect(self.update_render_button)
        self.out_input.editTextChanged.connect(self.update_render_button)
        self.hip_input.editTextChanged.connect(self.update_render_button)

        # Create text widgets with splitter
        self.text_splitter = QSplitter(Qt.Orientation.Horizontal)  # Horizontal split

        # Set handle width explicitly
        self.text_splitter.setHandleWidth(8)  # Make handle wider for easier grabbing

        # Create text widgets
        self.summary_text = QTextEdit()
        self.summary_text.setStyleSheet("""
            QTextEdit {
                background-color: #212121;
                color: #cccccc;
                border: none;
                padding: 10px;
                font-family: "Courier New", monospace;
            }
            QScrollBar:vertical {
                width: 8px;
                background: #323232;
            }
            QScrollBar::handle:vertical {
                background: #3b3b3b;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical {
                height: 8px;
                background: #323232;
                subcontrol-position: bottom;
            }
            QScrollBar::sub-line:vertical {
                height: 8px;
                background: #323232;
                subcontrol-position: top;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                width: 8px;
                height: 8px;
                background: #555555;
            }
        """)
        self.summary_text.setReadOnly(True)
        self.summary_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.summary_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.summary_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.raw_text = QTextEdit()
        self.raw_text.setStyleSheet("""
            QTextEdit {
                background-color: #212121;
                color: #cccccc;
                border: none;
                padding: 10px;
            }
            QScrollBar:vertical {
                width: 8px;
                background: #323232;
            }
            QScrollBar::handle:vertical {
                background: #3b3b3b;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical {
                height: 8px;
                background: #323232;
                subcontrol-position: bottom;
            }
            QScrollBar::sub-line:vertical {
                height: 8px;
                background: #323232;
                subcontrol-position: top;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                width: 8px;
                height: 8px;
                background: #555555;
            }
        """)
        self.raw_text.setReadOnly(True)
        self.raw_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.raw_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.raw_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.raw_text.hide()  # Hide raw text by default

        # Add text widgets to splitter
        self.text_splitter.addWidget(self.summary_text)
        self.text_splitter.addWidget(self.raw_text)

        # Set initial sizes for the splitter (50-50 split)
        self.text_splitter.setSizes([500, 500])

        # Add splitter to main layout and make it expand
        self.layout.addWidget(self.text_splitter, 1)  # Add stretch factor

        self.progress_frame = FrameProgressWidget()
        self.layout.addWidget(self.progress_frame)

        # For robust per-frame progress tracking
        self.completed_blocks = set()
        self.total_blocks = None

        # Create stats layout with separate labels and values
        self.stats_layout = QHBoxLayout()
        self.layout.addLayout(self.stats_layout)

        # Frames
        self.fc_label = QLabel("Frames:")
        self.stats_layout.addWidget(self.fc_label)
        self.fc_value = QLabel("-")
        self.fc_value.setStyleSheet("color: #ff4c00;")
        self.stats_layout.addWidget(self.fc_value)

        self.tfc_label = QLabel("/")
        self.stats_layout.addWidget(self.tfc_label)
        self.tfc_value = QLabel("-")
        self.tfc_value.setStyleSheet("color: #ff4c00;")
        self.stats_layout.addWidget(self.tfc_value)

        # Average
        self.average_label = QLabel("Average:")
        self.stats_layout.addWidget(self.average_label)
        self.average_value = QLabel("-")
        self.average_value.setStyleSheet("color: #ff4c00;")
        self.stats_layout.addWidget(self.average_value)

        # Elapsed
        self.elapsed_label = QLabel("Elapsed:")
        self.stats_layout.addWidget(self.elapsed_label)
        self.elapsed_value = QLabel("-")
        self.elapsed_value.setStyleSheet("color: #ff4c00;")
        self.stats_layout.addWidget(self.elapsed_value)

        # Est. Total
        self.total_label = QLabel("Est. Total:")
        self.stats_layout.addWidget(self.total_label)
        self.total_value = QLabel("-")
        self.total_value.setStyleSheet("color: #ff4c00;")
        self.stats_layout.addWidget(self.total_value)

        # ETA
        self.eta_label = QLabel("ETA:")
        self.stats_layout.addWidget(self.eta_label)
        self.eta_value = QLabel("--:--:--")
        self.eta_value.setStyleSheet("color: #ff4c00;")
        self.stats_layout.addWidget(self.eta_value)

        # Remaining
        self.remaining_label = QLabel("Remaining:")
        self.stats_layout.addWidget(self.remaining_label)
        self.remaining_value = QLabel("--")
        self.remaining_value.setStyleSheet("color: #ff4c00;")
        self.stats_layout.addWidget(self.remaining_value)

        # Create placeholder message with icon for image frame
        self.placeholder_label = QLabel()

        # Create the icon - a more image-like icon using QPainter
        icon_size = 64  # Make it a bit bigger
        icon = QPixmap(icon_size, icon_size)
        icon.fill(Qt.transparent)
        painter = QPainter(icon)
        painter.setRenderHint(QPainter.Antialiasing)

        # Set up the pen and brush for drawing
        pen = QPen(QColor("#555555"))
        pen.setWidth(2)
        painter.setPen(pen)
        brush = QBrush(QColor("#555555"))
        painter.setBrush(brush)

        # Draw mountains (filled triangles)
        # Back mountain
        points_back = [
            QPoint(icon_size//2, icon_size//4),          # Peak
            QPoint(icon_size-10, icon_size-12),          # Right base
            QPoint(icon_size//3, icon_size-12)           # Left base
        ]
        painter.drawPolygon(QPolygon(points_back))

        # Front mountain
        points_front = [
            QPoint(icon_size//4, icon_size//3),          # Peak
            QPoint(icon_size//2+10, icon_size-12),       # Right base
            QPoint(10, icon_size-12)                     # Left base
        ]
        painter.drawPolygon(QPolygon(points_front))

        # Draw sun (positioned above mountains)
        painter.setBrush(QBrush(QColor("#555555")))
        sun_size = icon_size//6
        painter.drawEllipse(
            icon_size-sun_size-10,  # X position (right side)
            8,                      # Y position (top)
            sun_size,              # Width
            sun_size               # Height
        )
        painter.end()

        # Create layout for placeholder with just the icon
        self.placeholder_widget = QWidget()  # Store as instance variable
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add icon
        icon_label = QLabel()
        icon_label.setPixmap(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(icon_label)

        # Style the placeholder widget
        self.placeholder_widget.setStyleSheet("""
            QWidget {
                background-color: #212121;
                border: 1px solid #555555;
                border-radius: 3px;
            }
        """)

        # Add placeholder to image frame
        self.image_frame = QFrame()
        self.image_frame.setFrameShape(QFrame.StyledPanel)
        self.image_frame.setLineWidth(1)
        self.image_layout = QHBoxLayout(self.image_frame)
        self.image_layout.setSpacing(1)
        self.image_layout.setContentsMargins(1, 1, 1, 1)
        self.image_layout.addWidget(self.placeholder_widget)
        self.layout.addWidget(self.image_frame)

        # Don't hide the image frame anymore, just hide the placeholder when renders start
        # self.image_frame.hide()  # Remove this line

        # Create image widgets list
        self.image_widgets = []
        for i in range(20):
            # Create a container widget for each image+label pair
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(0)
            container_layout.setContentsMargins(0, 0, 0, 0)

            # Create image label
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setStyleSheet("background-color: #212121;")
            image_label.setMinimumSize(100, 100)  # Smaller minimum size
            image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)  # Allow shrinking

            # Create name label
            name_label = QLabel()
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setStyleSheet("""
                QLabel {
                    background-color: #212121;
                    color: #ffffff;
                    padding: 2px;
                    border-top: 1px solid #555555;
                    min-height: 14px;
                    max-height: 14px;
                    font-size: 10px;
                }
            """)

            # Add both labels to container
            container_layout.addWidget(image_label)
            container_layout.addWidget(name_label)

            # Add container to horizontal layout
            self.image_layout.addWidget(container)
            container.hide()  # Hide initially
            self.image_widgets.append((image_label, name_label))

        # After creating all widgets, connect the signals
        self.output_signal.connect(self.append_output_safe)
        self.raw_output_signal.connect(self.append_raw_output_safe)
        self.progress_signal.connect(self.update_progress_safe)
        self.image_update_signal.connect(self.update_image_preview_safe)
        self.render_finished_signal.connect(self.render_finished)
        self.time_labels_signal.connect(self.update_time_labels_safe)
        self.resize_needed_signal.connect(self.adjust_image_sizes_safe)  # Add this line

        # Create the loader thread
        self.hip_loader = HipFilesLoader()
        self.hip_loader.finished.connect(self.on_hip_files_loaded)

        # Load settings last, after all widgets are created
        self.load_settings()

        # Set initial minimum window size
        self.setMinimumWidth(800)  # Or whatever minimum width you prefer

        # Store original image data and dimensions
        self.original_images = [None] * 20  # Will store tuples of (bytes, width, height)

        # Add this to your __init__ before setting the stylesheet:
        self.create_down_arrow_icon()

        # Update the common ComboBox style
        combo_style = """
            QComboBox {
                background-color: #131313;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 2px;
                padding-right: 15px;
            }
            QComboBox:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #444444;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
                background-color: #555555;
            }
            QComboBox::drop-down:disabled {
                background-color: #444444;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            QComboBox::down-arrow:on {
                top: 1px;
                left: 1px;
            }
            QComboBox QAbstractItemView {
                background-color: #131313;
                color: #ffffff;
                selection-background-color: #ff4c00;
                selection-color: #ffffff;
            }
            QComboBox:hover {
                border: 1px solid #ff4c00;
            }
        """

        # Update refresh button style
        refresh_btn_style = """
            QPushButton {
                background-color: #131313;
                border: 1px solid #555555;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #555555;
                border: 1px solid #ff4c00;
            }
            QPushButton:pressed {
                background-color: #ff4c00;
            }
        """

        # Apply styles to hip input and refresh button
        self.hip_input.setStyleSheet(combo_style)
        self.refresh_hip_btn.setStyleSheet(refresh_btn_style)

        # Apply same styles to out input and its refresh button
        self.out_input.setStyleSheet(combo_style)
        self.refresh_out_btn.setStyleSheet(refresh_btn_style)

        # Apply to other combo boxes for consistency
        self.start_frame.setStyleSheet(combo_style)
        self.end_frame.setStyleSheet(combo_style)

        # Initialize render-related variables
        self.total_frames = 0
        self.process = None
        self.canceling = False
        self.renderedImage = None

        # Define button styles
        standard_btn_style = """
            QPushButton {
                background-color: #131313;
                color: #d6d6d6;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 15px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #555555;
                border: 1px solid #ff4c00;
            }
            QPushButton:pressed {
                background-color: #ff4c00;
                color: #000000;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #444444;
            }
        """

        action_btn_style = """
            QPushButton {
                background-color: #ff4c00;
                color: #000000;
                border: 1px solid #ff4c00;
                border-radius: 3px;
                padding: 5px 15px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #ff6b2b;
            }
            QPushButton:pressed {
                background-color: #cc3d00;
            }
            QPushButton:disabled {
                background-color: #662000;
                color: #999999;
                border: 1px solid #662000;
            }
        """

        # Apply styles to all buttons
        self.switch_btn.setStyleSheet(standard_btn_style)
        self.open_folder_btn.setStyleSheet(standard_btn_style)

        # Action buttons (Render and Cancel)
        self.render_btn.setStyleSheet(action_btn_style)
        self.cancel_btn.setStyleSheet(action_btn_style)

        # Add to stylesheet
        self.setStyleSheet(self.styleSheet() + """
            QLineEdit:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #444444;
            }
            QComboBox:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #444444;
            }
        """)

        # Connect auto-save signals
        self.hip_input.editTextChanged.connect(self.save_settings)
        self.out_input.editTextChanged.connect(self.save_settings)
        self.range_check.stateChanged.connect(self.save_settings)
        self.start_frame.textChanged.connect(self.save_settings)
        self.end_frame.textChanged.connect(self.save_settings)
        self.skip_check.stateChanged.connect(self.save_settings)
        self.shutdown_check.stateChanged.connect(self.save_settings)  # Add this line

        # Add specific styling for the frame range inputs and frame step combo box
        frame_input_style = """
            QLineEdit {
                background-color: #131313;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px;
            }
            QLineEdit:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #444444;
            }
        """

        frame_step_style = """
            QComboBox {
                background-color: #131313;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px;
            }
            QComboBox:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #444444;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
                background-color: #555555;
            }
            QComboBox::drop-down:disabled {
                background-color: #444444;
            }
            QComboBox QAbstractItemView {
                background-color: #131313;
                color: #ffffff;
                selection-background-color: #ff4c00;
                selection-color: #ffffff;
            }
            QComboBox:hover {
                border: 1px solid #ff4c00;
            }
            QLineEdit:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border: 1px solid #444444;
            }
        """

        self.start_frame.setStyleSheet(frame_input_style)
        self.end_frame.setStyleSheet(frame_input_style)
        self.frame_step.setStyleSheet(frame_step_style)

        # Update the progress bar style
        self.progress_frame.setStyleSheet("""
            QProgressBar {
                background-color: #222222;
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #22adf2;  /* Changed to blue */
                border-radius: 2px;
            }
        """)

        # After creating the summary_text widget, add the tips
        self.append_output_safe(
            '''TIPS:
    For batch rendering -
        Point the 'Out Path' field to a merge node with multiple ROPs connected to it.
        The 'Frame Range' override will be ignored, instead using the range set up in Houdini.
        Each ROP should have -
            'Non-blocking Current Frame Rendering' unchecked.
            'Valid Frame Range' set to 'Render Frame Range Only (Strict)' if the ROPs have different ranges.''',
            color='#ff804a',
            bold=False,
            center=False
        )
        self.append_output_safe('\n\n')  # Add some space after the tips

        # Connect out_input signals
        self.out_input.loading_state_changed.connect(self.update_render_button)
        self.out_input.editTextChanged.connect(self.update_render_button)

        # Initial render button state
        self.update_render_button()

    def create_down_arrow_icon(self):
        """Create a down arrow icon if it doesn't exist"""
        if not os.path.exists('down_arrow.png'):
            # Create a 12x12 transparent image
            img = PIL.Image.new('RGBA', (12, 12), (0, 0, 0, 0))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)

            # Draw triangle with dark background and light border
            # Draw background triangle
            draw.polygon([(2, 4), (10, 4), (6, 8)], fill='#ffffff')

            img.save('down_arrow.png')

    def toggle_frame_range(self, state=None):
        """Enable/disable frame range inputs and handle value switching"""
        if state is None:
            state = self.range_check.isChecked()

        self.start_frame.setEnabled(state)
        self.end_frame.setEnabled(state)
        self.frame_step.setEnabled(state)

        if not state:
            # Only update values if unchecking - preserve user values when checking
            if hasattr(self, 'node_settings'):
                node_path = self.out_input.currentText()
                if node_path in self.node_settings:
                    settings = self.node_settings[node_path]
                    self.start_frame.setText(str(settings['f1']))
                    self.end_frame.setText(str(settings['f2']))
                    self.frame_step.setCurrentText("1")
        else:
            # When enabling, restore saved values if they exist
            saved_start = self.settings.get('user_start_frame')
            saved_end = self.settings.get('user_end_frame')
            saved_step = self.settings.get('user_step')
            if saved_start is not None and saved_end is not None:
                self.start_frame.setText(str(saved_start))
                self.end_frame.setText(str(saved_end))
            if saved_step is not None:
                self.frame_step.setCurrentText(str(saved_step))

    def load_settings(self):
        """Load saved settings into UI elements"""
        # Start the hip files refresh
        self.refresh_hip_list()

        # Set the last used hip path immediately
        last_hip = self.settings.get('last_hipname', DEFAULT_FOLDER)
        self.hip_input.setEditText(last_hip)

        # Rest of settings loading...
        self.out_input.addItems(self.settings.get_list('outnames', []))
        self.out_input.setEditText(self.settings.get('last_outname', DEFAULT_OUTNODE))

        # Load frame range settings
        use_range = self.settings.get('last_userange', False)
        saved_start = self.settings.get('user_start_frame')
        saved_end = self.settings.get('user_end_frame')
        saved_step = self.settings.get('user_step')

        # Set initial values (these might be overwritten by toggle_frame_range)
        if saved_start is not None and saved_end is not None:
            self.start_frame.setText(str(saved_start))
            self.end_frame.setText(str(saved_end))
        else:
            self.start_frame.setText("1")
            self.end_frame.setText("100")

        if saved_step is not None:
            self.frame_step.setCurrentText(str(saved_step))
        else:
            self.frame_step.setCurrentText("1")

        # Set checkbox state last and let toggle_frame_range handle the field states
        self.range_check.setChecked(use_range)
        self.toggle_frame_range(use_range)

        # Load other settings
        self.skip_check.setChecked(self.settings.get('last_useskip', False))
        self.notify_check.setChecked(self.settings.get('notifications_enabled', False))
        self.notify_frames.setText(str(self.settings.get('notification_interval', 10)))
        self.api_key_input.setText(self.settings.get('pushover_api_key', ''))
        self.user_key_input.setText(self.settings.get('pushover_user_key', ''))
        self.toggle_notification_inputs()

        # In load_settings
        self.shutdown_check.setChecked(self.settings.get('shutdown_after_render', False))
        delay_val = self.settings.get('shutdown_delay', '1 minute')
        idx = self.shutdown_delay.findText(delay_val)
        if idx != -1:
            self.shutdown_delay.setCurrentIndex(idx)
        else:
            self.shutdown_delay.setCurrentIndex(0)

    def save_settings(self):
        """Save current UI state to settings"""
        self.settings.set('hipnames', self._get_unique_items(self.hip_input))
        self.settings.set('last_hipname', self.hip_input.currentText())

        self.settings.set('outnames', self._get_unique_items(self.out_input))
        self.settings.set('last_outname', self.out_input.currentText())

        self.settings.set('last_userange', self.range_check.isChecked())

        # Save the current frame range values if the checkbox is checked
        if self.range_check.isChecked():
            self.settings.set('user_start_frame', self.start_frame.text())
            self.settings.set('user_end_frame', self.end_frame.text())
            self.settings.set('user_step', self.frame_step.currentText())

        self.settings.set('last_useskip', self.skip_check.isChecked())

        self.settings.set('notifications_enabled', self.notify_check.isChecked())
        self.settings.set('notification_interval', self.notify_frames.text())
        self.settings.set('pushover_api_key', self.api_key_input.text())
        self.settings.set('pushover_user_key', self.user_key_input.text())

        # In save_settings
        self.settings.set('shutdown_after_render', self.shutdown_check.isChecked())
        self.settings.set('shutdown_delay', self.shutdown_delay.currentText())

    def _get_unique_items(self, combo):
        """Helper to get unique items from QComboBox"""
        return list(set(combo.itemText(i) for i in range(combo.count())))

    def start_render(self):
        """Start the render process"""
        self.render_btn.hide()
        self.cancel_btn.show()
        self.canceling = False
        self.render_start_time = datetime.datetime.now()  # Store render start time

        # Disable open folder button until we have an output
        self.open_folder_btn.setEnabled(False)

        # Clear previous image previews
        for label, name_label in self.image_widgets:
            label.clear()
            name_label.clear()
            label.parent().hide()

        # Create the temp Python file
        create_temp_python_file()

        # Calculate total frames
        if self.range_check.isChecked():
            start = int(self.start_frame.text())
            end = int(self.end_frame.text())
            step = int(self.frame_step.currentText())
            self.total_frames = len(range(start, end + 1, step))
        else:
            # If no range specified, assume single frame
            self.total_frames = 1

        # Build command list without quotes
        cmd = [
            'hython',
            os.path.join(dir_path, 'hardeen_temp.py'),
            '-i', self.hip_input.currentText(),
            '-o', self.out_input.currentText(),
            '-s', self.start_frame.text(),
            '-e', self.end_frame.text(),
            '-u', str(self.range_check.isChecked()),
            '-r', str(self.skip_check.isChecked()),
            '-t', self.frame_step.currentText()
        ]

        # Start process
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )

        # Start monitoring thread
        self.render_thread = threading.Thread(
            target=self.monitor_render,
            daemon=True
        )
        self.render_thread.start()

        # Log command
        self.append_output_safe(
            '\n\n RENDER STARTED AT ' +
            time.strftime('%l:%M%p %Z on %b %d, %Y ') +
            '\n\n',
            color='#22adf2',
            bold=True,
            center=True
        )
        self.append_output_safe(' '.join(cmd) + '\n', color='#c0c0c0')
        self.append_output_safe('Loading scene...\n', color='#c0c0c0')

        # Save settings
        self.save_settings()

    def cancel_render(self):
        """Cancel the render process"""
        if not self.canceling:
            self.canceling = True
            self.cancel_btn.setText('Kill')
            self.append_output_safe(
                '\n Interrupt requested... Current frame will finish before stopping. \n\n',
                color='#ff7a7a',
                bold=True,
                center=True
            )
            # Send SIGUSR1 signal to indicate graceful shutdown
            try:
                os.kill(self.process.pid, signal.SIGUSR1)
            except AttributeError:
                # If SIGUSR1 is not available, fallback to SIGTERM
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

            # Send cancellation notification
            if self.notify_check.isChecked():
                job_name = os.path.splitext(os.path.basename(self.hip_input.currentText()))[0]
                current_frame = self.fc_value.text()
                total_frames = self.tfc_value.text()
                elapsed = (datetime.datetime.now() - self.render_start_time).total_seconds()

                cancel_message = (
                    f"⚠️ Render Interrupted: {job_name}\n"
                    f"Will stop after frame: {current_frame}/{total_frames}\n"
                    f"Total Time: {format_time(elapsed)}"
                )
                self.send_push_notification(cancel_message)
        else:
            # Force kill the process
            self.append_output_safe(
                '\n Force kill requested... Stopping render immediately. \n\n',
                color='#ff7a7a',
                bold=True,
                center=True
            )
            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            self.process.wait()
            self.append_output_safe(
                '\n Render Killed \n\n',
                color='#ff7a7a',
                bold=True,
                center=True
            )

            # Send kill notification
            if self.notify_check.isChecked():
                job_name = os.path.splitext(os.path.basename(self.hip_input.currentText()))[0]
                current_frame = self.fc_value.text()
                total_frames = self.tfc_value.text()
                elapsed = (datetime.datetime.now() - self.render_start_time).total_seconds()

                kill_message = (
                    f"🛑 Render Force Killed: {job_name}\n"
                    f"Stopped at: {current_frame}/{total_frames}\n"
                    f"Total Time: {format_time(elapsed)}"
                )
                self.send_push_notification(kill_message)

            self.render_btn.show()
            self.cancel_btn.hide()
            self.cancel_btn.setText('Interrupt')

    def monitor_render(self):
        """Monitor the render process and update UI"""
        try:
            # Initialize time tracking variables
            frame_times = []
            frame_total = 0
            frame_count = 0
            average = 0
            recent_average = 0
            remaining_time = 0
            total_time = 0
            last_notified_frame = 0
            current_frame_in_progress = False
            graceful_shutdown_requested = False

            start_time = datetime.datetime.now()
            current_frame_start = None
            current_frame = 0
            current_frame_number = None
            notify_interval = int(self.notify_frames.text() or "10")

            # Track whether we've already displayed scene info
            scene_info_displayed = False

            # Calculate total frames based on range and step
            if self.range_check.isChecked():
                start = int(self.start_frame.text())
                end = int(self.end_frame.text())
                step = int(self.frame_step.currentText())
                frame_range = list(range(start, end + 1, step))
                total_frames = len(frame_range)
                # Pass frame range to progress widget
                self.progress_frame.set_total_frames(total_frames, frame_range)
                # Create frame mappings for easy lookup
                frame_to_index = {frame: i for i, frame in enumerate(frame_range)}
                index_to_frame = {i: frame for i, frame in enumerate(frame_range)}
            else:
                # Get from ROP settings if available
                out_node = self.out_input.currentText()
                if hasattr(self, 'node_settings') and out_node in self.node_settings:
                    settings = self.node_settings[out_node]
                    total_frames = settings['f2'] - settings['f1'] + 1
                else:
                    total_frames = 1
                self.progress_frame.set_total_frames(total_frames)
                frame_to_index = {}
                index_to_frame = {}

            # Update initial frame count display
            self.fc_value.setText("0")
            self.tfc_value.setText(str(total_frames))
            self.progress_signal.emit(0, total_frames)
            self.progress_frame.clear()

            # Track frames we've seen and skipped
            frames_seen = set()
            skipped_frames = set()
            consecutive_skips = []
            last_message_type = None

            # Dictionary to track frame render start times
            frame_start_times = {}

            while self.process and self.process.poll() is None:
                # Add timeout to readline to allow checking cancellation
                ready = select.select([self.process.stdout], [], [], 0.1)[0]
                if not ready:
                    if self.canceling and not current_frame_in_progress:
                        break
                    elif self.canceling and not graceful_shutdown_requested:
                        try:
                            os.kill(self.process.pid, signal.SIGUSR1)
                            graceful_shutdown_requested = True
                        except AttributeError:
                            pass
                    continue

                line = self.process.stdout.readline()
                if not line:
                    break

                line = line.decode(errors='backslashreplace').rstrip()
                line = line.replace('[Redshift] ', '').replace('[Redshift]', '')

                # Update raw output
                self.raw_output_signal.emit(line)

                # Check for saved file messages - handle both single and double quotes
                saved_file_match = re.search(r"Saved file ['\"]([^'\"]+\.(?:exr|png|jpg|jpeg|tif|tiff))['\"]", line)
                if saved_file_match:
                    output_file = saved_file_match.group(1)
                    print(f"Detected saved file: {output_file}")
                    # Store the output path for "Open Output Location" button
                    self.renderedImage = output_file
                    # Trigger image preview update
                    self.image_update_signal.emit(output_file)

                # ===== FRAME DETECTION AND SKIPPING LOGIC =====

                # Track when a frame is about to be rendered
                frame_rendering_match = re.search(r"'([^']+)' rendering frame (\d+)", line)
                if frame_rendering_match:
                    current_frame_number = int(frame_rendering_match.group(2))
                    # Store the start time for this frame
                    frame_start_times[current_frame_number] = datetime.datetime.now()
                    # We now have a current frame number but don't know yet if it will be skipped

                # Check if the frame is being skipped
                if 'Skip rendering enabled. File already rendered' in line or 'Skipped - File already exists' in line:
                    if current_frame_number is not None:
                        # Process frame as skipped
                        if self.range_check.isChecked():
                            if current_frame_number in frame_to_index:
                                skipped_frames.add(current_frame_number)
                                frames_seen.add(current_frame_number)
                                frame_count = len([f for f in frames_seen if f in frame_to_index])
                                # Set skipped using frame index
                                self.progress_frame.set_frame_skipped(frame_to_index[current_frame_number])
                                consecutive_skips.append(current_frame_number)
                        else:
                            skipped_frames.add(current_frame_number)
                            frames_seen.add(current_frame_number)
                            frame_count = len(frames_seen)
                            # Set skipped using frame count
                            self.progress_frame.set_frame_skipped(frame_count - 1)
                            consecutive_skips.append(current_frame_number)

                        # Update UI with skipped frame
                        self.fc_value.setText(str(frame_count))
                        self.progress_signal.emit(frame_count, total_frames)
                        last_message_type = "skipped"
                        # Mark that we're not rendering this frame
                        current_frame_in_progress = False
                        # Clear current frame number to prevent output
                        current_frame_number = None

                # For non-skipped frames, we need to detect when they start actual rendering
                elif 'Loading RS rendering options' in line and current_frame_number is not None:
                    # Only process if we haven't seen this frame in skipped_frames
                    if current_frame_number not in skipped_frames:
                        current_frame_in_progress = True

                        # Get time estimates
                        start_time = frame_start_times[current_frame_number]
                        estimated_time = 0
                        if frame_times:
                            if len(frame_times) >= 2:
                                estimated_time = recent_average
                            else:
                                estimated_time = average

                        # Only output frame header if this isn't part of a consecutive skip sequence
                        if not consecutive_skips:
                            # Format the frame header with estimated time using fixed-width fields
                            frame_header = f"\n Frame {current_frame_number}\n"
                            frame_header += f"   {'Started':<8} {start_time.strftime('%I:%M:%S %p')}\n"
                            if estimated_time > 0:
                                est_finish_time = start_time + datetime.timedelta(seconds=estimated_time)
                                frame_header += f"   {'Estimate':<8} {est_finish_time.strftime('%I:%M:%S %p')} - {self.format_time(estimated_time)}\n"
                            self.output_signal.emit(frame_header)

                        # Calculate frame count based on step
                        if self.range_check.isChecked():
                            # Only count frames that are in our range
                            if current_frame_number in frame_to_index:
                                frame_count = frame_to_index[current_frame_number] + 1
                                # Update progress using frame index
                                self.progress_frame.update_frame_progress(frame_to_index[current_frame_number], 0)
                        else:
                            frame_count += 1
                            # Update progress using actual frame number
                            self.progress_frame.update_frame_progress(frame_count - 1, 0)

                        # Update UI
                        self.fc_value.setText(str(frame_count))
                        self.progress_signal.emit(frame_count, total_frames)

                        current_frame_start = datetime.datetime.now()

                # Check for frame completion
                elif 'ROP node endRender' in line:
                    current_frame_in_progress = False
                    if self.canceling and graceful_shutdown_requested:
                        self.render_finished_signal.emit()
                        break

                # Check for Redshift block progress
                block_match = re.search(r'Block (\d+)/(\d+)', line)
                if block_match and current_frame_number is not None:
                    block_num = int(block_match.group(1))
                    total_blocks = int(block_match.group(2))
                    if self.total_blocks is None or self.total_blocks != total_blocks:
                        self.total_blocks = total_blocks
                    self.completed_blocks.add(block_num)
                    percent = int((len(self.completed_blocks) / self.total_blocks) * 100)

                    # Get the estimated time for this frame
                    estimated_time = 0
                    if frame_times:
                        if len(frame_times) >= 2:
                            estimated_time = recent_average
                        else:
                            estimated_time = average

                    # Update the current frame progress
                    if self.range_check.isChecked():
                        if current_frame_number in frame_to_index:
                            # Update progress using frame index
                            self.progress_frame.update_frame_progress(frame_to_index[current_frame_number], percent, estimated_time)
                    else:
                        # Update progress using frame count
                        self.progress_frame.update_frame_progress(frame_count - 1, percent, estimated_time)
                    continue

                # Check for frame completion (scene extraction time indicates completion)
                elif 'scene extraction time' in line:
                    if current_frame_start and current_frame_number is not None:
                        # Extract render time
                        match = re.search(r"total time (\d+\.\d+) sec", line)
                        if match:
                            render_time = float(match.group(1))
                            frame_times.append(render_time)

                            # Add the frame time to our custom progress widget
                            if self.range_check.isChecked():
                                if current_frame_number in frame_to_index:
                                    # Add frame time using frame index
                                    self.progress_frame.add_frame_time(frame_to_index[current_frame_number], render_time)
                            else:
                                # Add frame time using frame count
                                self.progress_frame.add_frame_time(frame_count - 1, render_time)

                            # Update progress
                            if self.range_check.isChecked():
                                if current_frame_number in frame_to_index:
                                    frame_count = frame_to_index[current_frame_number] + 1
                            else:
                                frame_count += 1

                            self.fc_value.setText(str(frame_count))
                            self.progress_signal.emit(frame_count, total_frames)

                            # Set per-frame progress to 100% at end of frame
                            if self.range_check.isChecked():
                                if current_frame_number in frame_to_index:
                                    # Update progress using frame index
                                    self.progress_frame.update_frame_progress(frame_to_index[current_frame_number], 100)
                            else:
                                # Update progress using frame count
                                self.progress_frame.update_frame_progress(frame_count - 1, 100)

                            # Optionally clear block tracking at end of frame
                            self.completed_blocks = set()
                            self.total_blocks = None

                            # Calculate averages
                            average = sum(frame_times) / len(frame_times)
                            if len(frame_times) >= 2:
                                recent_times = frame_times[-2:]
                                recent_average = (2 * recent_times[1]) - recent_times[0]
                            else:
                                recent_average = average

                            # Calculate elapsed time
                            current_time = datetime.datetime.now()
                            elapsed_time = (current_time - start_time).total_seconds()

                            # Calculate remaining time based on average
                            remaining_frames = total_frames - frame_count
                            remaining_time = remaining_frames * average

                            # Calculate ETA
                            eta_time = current_time + datetime.timedelta(seconds=remaining_time)

                            # Update time labels
                            self.time_labels_signal.emit(
                                elapsed_time,  # Total elapsed time
                                average,       # Average per frame
                                total_frames * average,  # Estimated total time
                                remaining_time,         # Remaining time
                                QDateTime(eta_time),    # ETA time
                                True                    # Show ETA
                            )

                            # Output actual render time for this frame using fixed-width field
                            if not consecutive_skips:
                                finished_str = f"   {'Finished':<8} {current_time.strftime('%I:%M:%S %p')} - {self.format_time(render_time)}\n\n"
                                self.output_signal.emit(finished_str)

                            last_message_type = "completed"

            # Output any remaining skipped frames at the end
            if consecutive_skips:
                consecutive_skips.sort()
                ranges = []
                start = end = consecutive_skips[0]

                for i in range(1, len(consecutive_skips)):
                    if consecutive_skips[i] == end + 1:
                        end = consecutive_skips[i]
                    else:
                        if start == end:
                            ranges.append(f"{start}")
                        else:
                            ranges.append(f"{start}-{end}")
                        start = end = consecutive_skips[i]

                if start == end:
                    ranges.append(f"{start}")
                else:
                    ranges.append(f"{start}-{end}")

                frames_text = ", ".join(ranges)
                self.output_signal.emit(f"Frames {frames_text} skipped - Files already exist\n\n")
                consecutive_skips.clear()
                last_message_type = "skipped"

            # Only send completion notification if not cancelled
            if self.notify_check.isChecked() and not self.canceling:
                job_name = os.path.splitext(os.path.basename(self.hip_input.currentText()))[0]
                elapsed = time.time() - start_time.timestamp()
                avg_time = format_time(average) if average else "N/A"

                end_message = (
                    f"✅ Render Complete: {job_name}\n"
                    f"Total Frames: {total_frames}\n"
                    f"Total Time: {format_time(elapsed)}\n"
                    f"Avg Frame: {avg_time}"
                )
                self.send_push_notification(end_message)

            # After loop ends, make sure UI is updated
            self.render_finished_signal.emit()

        except Exception as e:
            print(f"Error in monitor thread: {str(e)}\n{traceback.format_exc()}")
            self.render_finished_signal.emit()

    def render_finished(self):
        """Handle render completion (called in main thread)"""
        # Stop text update timers before final updates
        self.summary_update_timer.stop()
        self.raw_update_timer.stop()

        # Process any remaining text updates
        self.process_summary_updates()
        self.process_raw_updates()

        # Calculate final elapsed time
        elapsed = (datetime.datetime.now() - self.render_start_time).total_seconds()

        if self.canceling:
            # If we were canceling, show interrupted message
            if self.cancel_btn.text() == 'Kill':
                self.append_output_safe(
                    '\n\n Render killed and stopped. \n\n',
                    color='#ff7a7a',
                    bold=True,
                    center=True
                )
            else:
                self.append_output_safe(
                    '\n\n Render gracefully canceled. \n\n',
                    color='#ff7a7a',
                    bold=True,
                    center=True
                )
        else:
            # Show completion message
            self.append_output_safe(
                '\n\n RENDER COMPLETED \n\n',
                color='#22adf2',
                bold=True,
                center=True
            )

            # Schedule shutdown if enabled
            if self.shutdown_check.isChecked():
                delay = self.get_shutdown_delay_seconds()
                self.schedule_shutdown(delay)

        # Reset UI state
        self.render_btn.show()
        self.cancel_btn.hide()
        self.canceling = False

        # Reset time labels with final elapsed time
        self.time_labels_signal.emit(
            elapsed,  # Total elapsed time
            0,       # Average (reset to 0)
            elapsed, # Est. Total (same as elapsed since we're done)
            0,      # Remaining time (0 since we're done)
            QDateTime(),  # Empty ETA since we're done
            False    # Don't show ETA
        )

        # Show placeholder if no images are visible
        if not any(label.parent().isVisible() for label, _ in self.image_widgets):
            if hasattr(self, 'placeholder_widget'):
                self.placeholder_widget.setParent(self.image_frame)
                self.image_layout.addWidget(self.placeholder_widget)
                self.placeholder_widget.show()

        # Shutdown logic - only trigger if render completed normally (not interrupted)
        if hasattr(self, 'shutdown_check') and self.shutdown_check.isChecked() and not self.canceling:
            # Send pushover notification about pending shutdown
            if self.notify_check.isChecked():
                job_name = os.path.splitext(os.path.basename(self.hip_input.currentText()))[0]
                shutdown_message = (
                    f"⚠️ Render complete: {job_name}\n"
                    f"The computer will shut down in {self.shutdown_delay.currentText()} unless canceled."
                )
                self.send_push_notification(shutdown_message)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Shutdown Confirmation")
            msg_box.setText(f"Render is complete. The computer will shut down in {self.shutdown_delay.currentText()}.")
            msg_box.setInformativeText("Click 'Cancel Shutdown' to prevent the computer from shutting down.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Cancel)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
            msg_box.button(QMessageBox.StandardButton.Cancel).setText("Cancel Shutdown")
            reply = msg_box.exec()
            if reply == QMessageBox.StandardButton.Cancel:
                return
            # Schedule shutdown after selected delay
            import threading
            delay_seconds = self.get_shutdown_delay_seconds()
            threading.Thread(target=self.schedule_shutdown, args=(delay_seconds,), daemon=True).start()

        # Restart text update timers
        self.summary_update_timer.start()
        self.raw_update_timer.start()

    def get_shutdown_delay_seconds(self):
        text = self.shutdown_delay.currentText()
        if text == "No delay": return 5  # 5 second safety delay
        if text.startswith("1 minute"): return 60
        if text.startswith("5 minutes"): return 5*60
        if text.startswith("10 minutes"): return 10*60
        if text.startswith("30 minutes"): return 30*60
        if text.startswith("1 hour"): return 60*60
        return 60  # default

    def schedule_shutdown(self, delay_seconds=60):
        from PySide6.QtWidgets import QMessageBox
        from PySide6.QtCore import QTimer

        # Create a custom message box for countdown
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Shutdown Countdown")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Cancel)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        msg_box.button(QMessageBox.StandardButton.Cancel).setText("Cancel Shutdown")

        # Store remaining time as an attribute so the nested function can access it
        self._shutdown_remaining_time = delay_seconds

        def update_countdown():
            if self._shutdown_remaining_time > 0:
                minutes = self._shutdown_remaining_time // 60
                seconds = self._shutdown_remaining_time % 60
                msg_box.setText(f"Computer will shut down in {minutes:02d}:{seconds:02d}")
                self._shutdown_remaining_time -= 1
            else:
                timer.stop()
                msg_box.done(0)  # Close the dialog
                # Now run the shutdown in a background thread
                import threading
                threading.Thread(target=self.execute_shutdown, daemon=True).start()

        timer = QTimer(msg_box)
        timer.timeout.connect(update_countdown)
        timer.start(1000)

        # Show initial countdown
        msg_box.setText(f"Computer will shut down in {delay_seconds//60:02d}:{delay_seconds%60:02d}")
        # Start the timer immediately
        update_countdown()
        # If user cancels, stop the timer
        if msg_box.exec() == QMessageBox.StandardButton.Cancel:
            timer.stop()
            print("Shutdown cancelled by user.")
            return

    def execute_shutdown(self):
        """Execute the actual shutdown command"""
        try:
            from pydbus import SystemBus
            bus = SystemBus()
            proxy = bus.get('org.freedesktop.login1', '/org/freedesktop/login1')

            # Debug information
            print("Attempting to shut down system...")
            print(f"CanPowerOff response: {proxy.CanPowerOff()}")

            if proxy.CanPowerOff() == 'yes':
                print("System can be powered off, initiating shutdown...")
                try:
                    proxy.PowerOff(False)  # False for 'NOT interactive'
                    print("Shutdown command sent successfully")
                except Exception as e:
                    print(f"Error during PowerOff call: {str(e)}")
                    print(f"Traceback: {traceback.format_exc()}")
                    QMessageBox.critical(self, "Shutdown Error",
                        f"Failed to execute shutdown command: {str(e)}")
            else:
                error_msg = "System cannot be powered off. Please check permissions or system configuration."
                print(f"WARNING: {error_msg}")
                print(f"CanPowerOff returned: {proxy.CanPowerOff()}")
                QMessageBox.critical(self, "Shutdown Error", error_msg)
        except Exception as e:
            error_msg = f"Failed to execute shutdown: {str(e)}"
            print(error_msg)
            print(f"Traceback: {traceback.format_exc()}")
            QMessageBox.critical(self, "Shutdown Error", error_msg)

    def update_progress_safe(self, current, total):
        """Update progress bars (called in main thread)"""
        self.progress_frame.set_total_frames(total)

        # Don't change the current frame progress here -
        # that's updated separately by the block progress tracking

    def update_time_labels_safe(self, elapsed, average, est_total, remaining_time, eta_dt, show_eta):
        """Update time labels with render progress"""
        # Style for time values
        time_style = "color: #ff4c00;"
        label_style = "color: #d6d6d6;"

        # Update elapsed time
        self.elapsed_label.setText("Elapsed:")
        self.elapsed_label.setStyleSheet(label_style)
        self.elapsed_value.setText(format_time(elapsed))
        self.elapsed_value.setStyleSheet(time_style)

        # Update average time
        self.average_label.setText("Average:")
        self.average_label.setStyleSheet(label_style)
        self.average_value.setText(format_time(average))
        self.average_value.setStyleSheet(time_style)

        # Update estimated total time
        self.total_label.setText("Est. Total:")
        self.total_label.setStyleSheet(label_style)
        self.total_value.setText(format_time(est_total))
        self.total_value.setStyleSheet(time_style)

        # Update ETA and remaining time
        if show_eta:
            self.eta_label.setText("ETA:")
            self.eta_label.setStyleSheet(label_style)
            self.remaining_label.setText("Remaining:")
            self.remaining_label.setStyleSheet(label_style)

            # Create value labels with orange time - now using 12-hour format
            eta_str = eta_dt.toString("hh:mm:ss AP")  # Changed to 12-hour format with AM/PM
            remaining = format_time(remaining_time)
            self.eta_value.setText(eta_str)
            self.eta_value.setStyleSheet(time_style)
            self.remaining_value.setText(remaining)
            self.remaining_value.setStyleSheet(time_style)
        else:
            self.eta_label.setText("ETA:")
            self.eta_label.setStyleSheet(label_style)
            self.remaining_label.setText("Remaining:")
            self.remaining_label.setStyleSheet(label_style)
            self.eta_value.setText("--:--:--")
            self.eta_value.setStyleSheet(time_style)
            self.remaining_value.setText("--")
            self.remaining_value.setStyleSheet(time_style)

    def update_image_preview_safe(self, image_path):
        """Update image preview safely (called in main thread)"""
        try:
            print(f"Attempting to update preview with image: {image_path}")
            self.open_folder_btn.setEnabled(True)

            # Store current scroll positions and check if at bottom
            summary_scrollbar = self.summary_text.verticalScrollBar()
            raw_scrollbar = self.raw_text.verticalScrollBar()
            summary_at_bottom = summary_scrollbar.value() == summary_scrollbar.maximum()
            raw_at_bottom = raw_scrollbar.value() == raw_scrollbar.maximum()

            # Remove placeholder widget if it exists
            if hasattr(self, 'placeholder_widget'):
                self.placeholder_widget.hide()
                self.placeholder_widget.deleteLater()
                del self.placeholder_widget

            # Get frame number from path
            frame_num = re.search(r'\.(\d+)\.', image_path)

            if image_path.lower().endswith('.exr'):
                # Load image using OpenImageIO
                buf = oiio.ImageBuf(image_path)
                subCount = 0

                # Clear previous previews
                for label, name_label in self.image_widgets:
                    label.blockSignals(True)  # Block signals during clear
                    label.clear()
                    name_label.clear()
                    label.parent().hide()
                    label.blockSignals(False)

                # Process each subimage/AOV
                while subCount < buf.nsubimages:
                    if subCount >= len(self.image_widgets):
                        break

                    label, name_label = self.image_widgets[subCount]
                    container = label.parent()
                    container.show()

                    spec = buf.spec()
                    subimage = oiio.ImageBuf(image_path, subCount, 0)

                    # Get channel names for this subimage
                    channelnames = subimage.spec().channelnames
                    layers = {}
                    for channelname in channelnames:
                        layername = ".".join(channelname.split(".")[:-1])
                        if layername not in layers:
                            layers[layername] = []
                        layers[layername].append(channelname)

                    # Create label text
                    for layername, channelnames in layers.items():
                        channels = [cn.split(".")[-1].lower() for cn in channelnames]
                        if len(channels) == 1:
                            channel_str = channels[0]
                        else:
                            channel_str = "".join(channels)
                        if layername == "":
                            layer_str = f"{channel_str}"
                        else:
                            layer_str = f"{layername}.{channel_str}"

                        # Just set the layer string without frame number
                        name_label.setText(layer_str)

                    try:
                        # Convert to display format
                        display_buf = oiio.ImageBufAlgo.colorconvert(subimage, "linear", "srgb")
                        pixels = display_buf.get_pixels(oiio.FLOAT)

                        # Handle different channel configurations
                        if len(pixels.shape) == 3:
                            if pixels.shape[2] == 1:  # Single channel
                                pixels = np.repeat(pixels, 3, axis=2)
                            elif pixels.shape[2] not in [3, 4]:  # Not RGB or RGBA
                                if pixels.shape[2] > 3:
                                    pixels = pixels[:, :, :3]
                                else:
                                    padding = np.zeros((*pixels.shape[:2], 3-pixels.shape[2]))
                                    pixels = np.concatenate([pixels, padding], axis=2)
                        elif len(pixels.shape) == 2:  # Single channel
                            pixels = np.stack([pixels] * 3, axis=2)

                        # Normalize the float data to 0-1 range
                        pixels = np.clip(pixels, 0, 1)

                        # Convert to 8-bit
                        pixels = (pixels * 255).astype(np.uint8)

                        # Convert to QPixmap
                        img = PIL.Image.fromarray(pixels)

                        # Store the original image data and dimensions
                        self.original_images[subCount] = (
                            img.tobytes("raw", "RGB"),
                            img.width,
                            img.height
                        )

                        # Block signals during initial pixmap setup
                        label.blockSignals(True)
                        label.setPixmap(QPixmap.fromImage(QImage(
                            self.original_images[subCount][0],  # bytes
                            self.original_images[subCount][1],  # width
                            self.original_images[subCount][2],  # height
                            QImage.Format.Format_RGB888
                        )))
                        label.setScaledContents(False)
                        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        label.blockSignals(False)

                    except Exception as e:
                        print(f"Error processing subimage {subCount}: {str(e)}")
                        continue

                    print(f"Successfully loaded AOV: {layer_str}")
                    subCount += 1

            else:
                self._preview_single_image(image_path)

            # After showing/hiding containers, adjust sizes
            QTimer.singleShot(0, self.resize_needed_signal.emit)

            # After all image updates, restore scroll positions if they were at bottom
            if summary_at_bottom:
                summary_scrollbar.setValue(summary_scrollbar.maximum())
            if raw_at_bottom:
                raw_scrollbar.setValue(raw_scrollbar.maximum())

        except Exception as e:
            print(f"Error updating image preview: {str(e)}")
            traceback.print_exc()

    def _preview_single_image(self, image_path):
        """Helper method to preview a single image"""
        for label, name_label in self.image_widgets:
            if label.pixmap() is None or label.pixmap().isNull():
                label.parent().show()

                frame_num = re.search(r'\.(\d+)\.', image_path)
                if frame_num:
                    name_label.setText(f"Frame {frame_num.group(1)}")

                # Style the name label
                name_label.setStyleSheet("""
                    QLabel {
                        background-color: #212121;
                        color: #ffffff;
                        padding: 2px;
                        border-top: 1px solid #555555;
                        min-height: 14px;
                        max-height: 14px;
                        font-size: 10px;
                    }
                """)

                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    label.setPixmap(scaled)
                break

    def format_time(self, seconds):
        """Format seconds into human readable time"""
        timedelta = datetime.timedelta(seconds=seconds)
        days = timedelta.days
        hours, remainder = divmod(timedelta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if seconds or not any((days, hours, minutes)):
            parts.append(f"{seconds}s")
        return "".join(parts)

    def switch_output(self):
        """Switch between output views"""
        current_text = self.switch_btn.text()

        # Store current scroll positions and check if at bottom
        summary_scrollbar = self.summary_text.verticalScrollBar()
        raw_scrollbar = self.raw_text.verticalScrollBar()
        summary_at_bottom = summary_scrollbar.value() == summary_scrollbar.maximum()
        raw_at_bottom = raw_scrollbar.value() == raw_scrollbar.maximum()

        if current_text == "View Raw Output":
            # Switch to raw output view
            self.summary_text.hide()
            self.raw_text.show()
            self.switch_btn.setText("View Output and Summary")

        elif current_text == "View Output and Summary":
            # Show both views
            self.summary_text.show()
            self.raw_text.show()
            self.switch_btn.setText("View Summary")

        else:  # "View Summary"
            # Show only summary
            self.summary_text.show()
            self.raw_text.hide()
            self.switch_btn.setText("View Raw Output")

        # Use QTimer to restore scroll positions after the views have been updated
        def restore_scroll():
            if summary_at_bottom and self.summary_text.isVisible():
                summary_scrollbar.setValue(summary_scrollbar.maximum())
            if raw_at_bottom and self.raw_text.isVisible():
                raw_scrollbar.setValue(raw_scrollbar.maximum())

        QTimer.singleShot(0, restore_scroll)

    def open_folder(self):
        """Open the output folder in file explorer"""
        if hasattr(self, 'renderedImage') and self.renderedImage:
            folder = os.path.dirname(self.renderedImage)
            if sys.platform == 'win32':
                os.startfile(folder)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', folder])
            else:
                subprocess.Popen(['xdg-open', folder])

    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        # Emit signal instead of direct call
        self.resize_needed_signal.emit()

    def adjust_image_sizes_safe(self):
        """Thread-safe version of adjust_image_sizes"""
        try:
            # Prevent recursive calls
            if hasattr(self, '_resize_in_progress') and self._resize_in_progress:
                return
            self._resize_in_progress = True

            try:
                visible_count = sum(1 for label, _ in self.image_widgets if label.parent().isVisible())
                if visible_count == 0:
                    return

                # Get available width (accounting for margins and spacing)
                available_width = self.image_frame.width() - (self.image_layout.spacing() * (visible_count - 1)) - 2

                # Calculate width for each container
                width = max(100, min(300, available_width // visible_count))

                # Track maximum height to adjust frame
                max_container_height = 0

                # Update size for all visible containers
                for i, (image_label, name_label) in enumerate(self.image_widgets):
                    container = image_label.parent()
                    if not container.isVisible():
                        continue

                    # Set container width
                    container.setFixedWidth(width)

                    # Scale image from original if available
                    if hasattr(self, 'original_images') and self.original_images[i] is not None:
                        image_data, img_width, img_height = self.original_images[i]

                        # Calculate height maintaining aspect ratio
                        aspect_ratio = img_height / img_width
                        target_height = int(width * aspect_ratio)

                        try:
                            # Create QImage from original data
                            qimg = QImage(image_data, img_width, img_height, QImage.Format.Format_RGB888)
                            if not qimg.isNull():
                                pixmap = QPixmap.fromImage(qimg)

                                # Scale the pixmap
                                scaled = pixmap.scaled(
                                    width,
                                    target_height,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation
                                )

                                # Block signals during pixmap update to prevent recursive repaints
                                image_label.blockSignals(True)
                                image_label.setPixmap(scaled)
                                image_label.blockSignals(False)

                                # Calculate total container height (image + label)
                                LABEL_HEIGHT = 14  # Fixed height for labels
                                container_height = target_height + LABEL_HEIGHT
                                container.setFixedHeight(container_height)
                                max_container_height = max(max_container_height, container_height)

                                # Ensure image label has correct size
                                image_label.setFixedSize(width, target_height)

                        except Exception as e:
                            print(f"Error scaling image {i}: {str(e)}")
                            continue

                    # Update container layout
                    container_layout = container.layout()
                    if container_layout:
                        container_layout.setSpacing(0)
                        container_layout.setContentsMargins(0, 0, 0, 0)

                # Set frame height to match tallest container
                if max_container_height > 0:
                    self.image_frame.setFixedHeight(max_container_height)

            finally:
                self._resize_in_progress = False

        except Exception as e:
            print(f"Error in adjust_image_sizes_safe: {str(e)}")
            traceback.print_exc()
            self._resize_in_progress = False

    def refresh_hip_list(self):
        """Refresh the list of recent HIP files"""
        current_text = self.hip_input.currentText()
        self.hip_input.clear()

        # Start loading animation
        self.hip_input.start_loading()

        # Start loading thread
        self.hip_loader.start()

        # Store current text for restoration
        self.last_hip_text = current_text

    def on_hip_files_loaded(self, hip_files):
        """Handle loaded hip files"""
        self.hip_input.stop_loading()
        self.hip_input.clear()

        if hip_files:
            print(f"\nAdding {len(hip_files)} HIP files to dropdown:")
            for hip_file in hip_files:
                print(f"  {hip_file}")
                self.hip_input.addItem(hip_file)

        # Add saved paths from settings
        saved_paths = self.settings.get_list('hipnames', [])
        if saved_paths:
            print(f"\nAdding {len(saved_paths)} saved paths to dropdown:")
            for path in saved_paths:
                print(f"  {path}")
                self.hip_input.addItem(path)

        # Restore text, preferring the current text if it exists
        current_text = self.hip_input.currentText()
        if current_text and current_text != "Loading...":
            self.hip_input.setEditText(current_text)
        elif hasattr(self, 'last_hip_text') and self.last_hip_text:
            self.hip_input.setEditText(self.last_hip_text)
        else:
            # If no text to restore, use the first item in the dropdown if available
            if hip_files:
                self.hip_input.setCurrentIndex(0)

        self.append_output_safe(
            f'\n Recent HIP files refreshed ({len(hip_files)} files found) \n\n',
            color='#7abfff',
            bold=True,
            center=True
        )

    def on_hip_selection_changed(self, index):
        """Handle hip file selection changes"""
        text = self.hip_input.currentText()
        print(f"Selected index {index}: {text}")
        self.append_output_safe(
            f"\nSelected HIP file: {text}\n",
            color='#7abfff'
        )

        # Start loading state before refreshing out nodes
        if os.path.exists(text):
            self.out_input.start_loading()
            self.refresh_out_nodes()

    def refresh_out_nodes(self):
        """Refresh the list of out nodes from current hip file"""
        current_text = self.out_input.currentText()
        self.out_input.clear()

        hip_file = self.hip_input.currentText()
        if os.path.exists(hip_file):
            # Start loading animation
            self.out_input.start_loading()

            # Use QTimer to allow the UI to update before processing
            QTimer.singleShot(100, lambda: self._process_out_nodes(hip_file, current_text))

    def _process_out_nodes(self, hip_file, current_text):
        """Process out nodes after showing loading state"""
        out_nodes, node_settings = parse_out_nodes(hip_file)

        # Stop loading animation
        self.out_input.stop_loading()

        if out_nodes:
            # Reverse the list so latest nodes appear first
            out_nodes.reverse()

            print(f"\nFound {len(out_nodes)} out nodes:")
            for node in out_nodes:
                print(f"  {node}")
                self.out_input.addItem(node)

        # Add saved paths from settings
        saved_paths = self.settings.get_list('outnames', [])
        if saved_paths:
            print(f"\nAdding {len(saved_paths)} saved out paths:")
            for path in saved_paths:
                print(f"  {path}")
                self.out_input.addItem(path)

        # Select the most recent out node (first in the list)
        if out_nodes:
            first_node = out_nodes[0]
            self.out_input.setCurrentText(first_node)

            # Update frame range and skip settings if available
            if first_node in node_settings:
                settings = node_settings[first_node]
                self.start_frame.setText(str(settings['f1']))
                self.end_frame.setText(str(settings['f2']))
                self.skip_check.setChecked(bool(settings['skip_rendered']))
        else:
            # If no new nodes found, restore previous selection
            self.out_input.setEditText(current_text)

        # Store node settings for later use
        self.node_settings = node_settings

        # Connect signal to handle out node changes
        self.out_input.currentTextChanged.connect(self.on_out_node_changed)

        self.append_output_safe(
            f'\n Out nodes refreshed ({len(out_nodes)} nodes found) \n\n',
            color='#7abfff',
            bold=True,
            center=True
        )

    def on_out_node_changed(self, node_path):
        """Handle out node selection changes"""
        if hasattr(self, 'node_settings') and node_path in self.node_settings:
            settings = self.node_settings[node_path]

            # Only update frame range if checkbox is unchecked
            if not self.range_check.isChecked():
                self.start_frame.setText(str(settings['f1']))
                self.end_frame.setText(str(settings['f2']))

            self.skip_check.setChecked(bool(settings['skip_rendered']))

    def append_output_safe(self, text, color=None, bold=False, center=False):
        """Queue summary text updates to be processed in the main thread"""
        with self.summary_update_lock:
            self.summary_update_queue.append((text, color, bold, center))

    def process_summary_updates(self):
        """Process queued summary text updates in the main thread"""
        updates = []
        with self.summary_update_lock:
            updates = self.summary_update_queue.copy()
            self.summary_update_queue.clear()

        if not updates:
            return

        # Check if scrollbar is at the bottom before adding text
        scrollbar = self.summary_text.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()

        # Clear any text selection and move cursor to end
        cursor = self.summary_text.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.summary_text.setTextCursor(cursor)

        for text, color, bold, center in updates:
            # Format and insert new text
            format = QTextCharFormat()

            if color:
                format.setForeground(QColor(color))
            if bold:
                format.setFontWeight(QFont.Weight.Bold)
            if center:
                cursor.insertBlock()
                blockFormat = QTextBlockFormat()
                blockFormat.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cursor.setBlockFormat(blockFormat)

            cursor.insertText(text, format)
            cursor.setBlockFormat(QTextBlockFormat())  # Reset block format to default (left-aligned)

        self.summary_text.setTextCursor(cursor)

        # Only scroll to bottom if we were already at the bottom
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def append_raw_output_safe(self, text):
        """Queue raw text updates to be processed in the main thread"""
        with self.raw_update_lock:
            self.raw_update_queue.append(text)

    def process_raw_updates(self):
        """Process queued raw text updates in the main thread"""
        updates = []
        with self.raw_update_lock:
            updates = self.raw_update_queue.copy()
            self.raw_update_queue.clear()

        if not updates:
            return

        # Check if scrollbar is at the bottom before adding text
        scrollbar = self.raw_text.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()

        # Clear any text selection and move cursor to end
        cursor = self.raw_text.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.raw_text.setTextCursor(cursor)

        for text in updates:
            cursor.insertText(text + '\n')  # Add newline after each line

        self.raw_text.setTextCursor(cursor)

        # Only scroll to bottom if we were already at the bottom
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def update_render_button(self):
        """Update render button enabled state based on paths and loading state"""
        hip_text = self.hip_input.currentText().strip()
        out_text = self.out_input.currentText().strip()

        # Check loading state of both inputs
        is_loading = self.hip_input.loading or self.out_input.loading

        # Enable render button only if we have both paths, they're non-empty, and not loading
        self.render_btn.setEnabled(bool(hip_text) and bool(out_text) and not is_loading)

    def send_push_notification(self, message, image_path=None):
        """Send push notification with optional image"""
        try:
            # Check if API key and user key are provided
            api_key = self.api_key_input.text().strip()
            user_key = self.user_key_input.text().strip()

            if not api_key or not user_key:
                self.append_output_safe(
                    "\nPushover notification error: API key or User key is missing\n",
                    color='#ff7a7a'
                )
                return

            try:
                import requests
            except ImportError:
                self.append_output_safe(
                    "\nPushover notification error: 'requests' module not found. Reinstall using launch script.\n",
                    color='#ff7a7a'
                )
                return

            url = "https://api.pushover.net/1/messages.json"
            files = {}

            data = {
                "token": api_key,
                "user": user_key,
                "message": message,
                "title": "Houdini Render Update"
            }

            if image_path and os.path.exists(image_path):
                # Convert EXR to PNG if needed
                if image_path.lower().endswith('.exr'):
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        buf = oiio.ImageBuf(image_path)
                        display_buf = oiio.ImageBufAlgo.colorconvert(buf, "linear", "srgb")
                        display_buf.write(tmp.name)
                        image_path = tmp.name

                files = {
                    "attachment": ("render.png", open(image_path, "rb"), "image/png")
                }

            response = requests.post(url, data=data, files=files)
            response.raise_for_status()

            self.append_output_safe("\nPushover notification sent successfully\n", color='#7abfff')
            print(f"Push notification sent successfully")

        except ImportError as e:
            self.append_output_safe(
                f"\nPushover notification error: {str(e)}\n",
                color='#ff7a7a'
            )
            print(f"Error sending push notification: {e}")
        except requests.exceptions.HTTPError as e:
            self.append_output_safe(
                f"\nPushover notification error: HTTP Error - {str(e)}\n",
                color='#ff7a7a'
            )
            print(f"Error sending push notification: {e}")
        except requests.exceptions.ConnectionError as e:
            self.append_output_safe(
                f"\nPushover notification error: Connection Error - Check your internet connection\n",
                color='#ff7a7a'
            )
            print(f"Error sending push notification: {e}")
        except Exception as e:
            self.append_output_safe(
                f"\nPushover notification error: {str(e)}\n",
                color='#ff7a7a'
            )
            print(f"Error sending push notification: {e}")

    def toggle_notification_inputs(self, state=None):
        """Enable/disable notification inputs"""
        if state is None:
            state = self.notify_check.isChecked()
        self.notify_frames.setEnabled(state)
        self.api_key_input.setEnabled(state)
        self.user_key_input.setEnabled(state)

    def test_shutdown(self):
        """Test the shutdown functionality with the selected delay"""
        print("Testing shutdown functionality...")
        # Get the delay from the dropdown
        delay_seconds = self.get_shutdown_delay_seconds()
        # Show confirmation message before starting the countdown
        print(f"Starting shutdown test with {delay_seconds} second delay")
        # Run the countdown in the main thread
        self.schedule_shutdown(delay_seconds)

    def closeEvent(self, event):
        """Handle window close event"""
        # Stop text update timers
        self.summary_update_timer.stop()
        self.raw_update_timer.stop()

        # Process any remaining text updates
        self.process_summary_updates()
        self.process_raw_updates()

        # Clear text update queues
        with self.summary_update_lock:
            self.summary_update_queue.clear()
        with self.raw_update_lock:
            self.raw_update_queue.clear()

        # ... rest of existing closeEvent code ...

def get_houdini_history_file():
    """Get the path to the Houdini file.history"""
    home = str(Path.home())
    print(f"Looking for Houdini directories in: {home}")

    # Look for any houdini version directory (e.g. houdini19.5, houdini20.0, etc)
    houdini_dirs = [d for d in os.listdir(home)
                   if d.startswith('houdini') and
                   os.path.isdir(os.path.join(home, d)) and
                   not d.endswith('.py')]

    print(f"Found Houdini directories: {houdini_dirs}")

    if not houdini_dirs:
        print("No Houdini directories found")
        return None

    # Use the latest version if multiple exist
    latest_dir = sorted(houdini_dirs)[-1]
    history_file = os.path.join(home, latest_dir, 'file.history')
    print(f"Checking history file: {history_file}")

    if os.path.exists(history_file):
        print(f"History file exists")
        return history_file
    else:
        print(f"History file does not exist")
        return None

def parse_hip_files(history_file):
    """Parse the file.history and extract HIP files"""
    if not history_file:
        print("No history file provided")
        return []

    try:
        print(f"Reading history file: {history_file}")
        with open(history_file, 'r') as f:
            content = ''.join(f.read().splitlines())

        if not content.startswith('HIP{'):
            print("File doesn't start with HIP{")
            return []

        end = content.find('}', 4)
        if end == -1:
            print("No closing } found")
            return []

        hip_section = content[4:end]
        print(f"Found HIP section length: {len(hip_section)}")

        paths = []
        current_path = ""

        for part in hip_section.split('/'):
            if not part:
                continue

            if not current_path:
                current_path = '/' + part
            else:
                current_path += '/' + part

            if current_path.endswith('.hip'):
                paths.append(current_path)
                current_path = ""

        # Remove duplicates while preserving order
        seen = set()
        hip_files = []
        for path in paths:
            if path not in seen:
                seen.add(path)
                hip_files.append(path)

        # Reverse the list so newest files appear first
        hip_files.reverse()

        print(f"\nFinal list of {len(hip_files)} unique HIP files (newest first):")
        for hip_file in hip_files[:5]:
            print(f"  {hip_file}")

        return hip_files

    except Exception as e:
        print(f"Error reading history file: {e}")
        traceback.print_exc()
        return []

def refresh_hip_files():
    """Refresh the list of recent HIP files"""
    history_file = get_houdini_history_file()
    return parse_hip_files(history_file)

def parse_out_nodes(hip_file):
    """Parse the hip file and extract available ROP nodes and their settings"""
    try:
        import hou
        # Load the hip file
        hou.hipFile.load(hip_file)

        # Find all ROP nodes
        out_nodes = []
        node_settings = {}  # Store settings for each node
        out_context = hou.node("/out")
        if out_context:
            for node in out_context.children():
                # Check if it's a ROP node (render node)
                if node.type().name() in ["rop_geometry", "Redshift_ROP", "opengl"]:
                    node_path = node.path()
                    out_nodes.append(node_path)

                    # Get frame range and skip settings - convert frames to integers
                    settings = {
                        'f1': int(node.parm('f1').eval()) if node.parm('f1') else 1,
                        'f2': int(node.parm('f2').eval()) if node.parm('f2') else 1,
                        'skip_rendered': node.parm('RS_outputSkipRendered').eval() if node.parm('RS_outputSkipRendered') else 0
                    }
                    node_settings[node_path] = settings

        return out_nodes, node_settings

    except ImportError:
        print("Could not import hou module - using hython")
        # Try using hython as fallback
        try:
            import subprocess
            script = """
import hou
import sys
import os
import json

# Completely suppress stdout/stderr
class NullIO:
    def write(self, *args): pass
    def flush(self): pass

# Save original stdout/stderr
old_stdout = sys.stdout
old_stderr = sys.stderr

try:
    # Redirect all output to null
    sys.stdout = NullIO()
    sys.stderr = NullIO()

    # Set environment variables to suppress Redshift output
    os.environ['RS_VERBOSITY_LEVEL'] = '0'

    # Load the hip file silently
    hou.hipFile.load(r"{0}", suppress_save_prompt=True)

    # Restore stdout just to print node paths and settings
    sys.stdout = old_stdout

    # Get out nodes and their settings
    out_context = hou.node("/out")
    node_settings = {{}}

    if out_context:
        for node in out_context.children():
            if node.type().name() in ["rop_geometry", "Redshift_ROP", "opengl"]:
                node_path = node.path()
                print("NODE:{{}}".format(node_path))

                # Get frame range and skip settings - convert frames to integers
                settings = {{
                    'f1': int(node.parm('f1').eval()) if node.parm('f1') else 1,
                    'f2': int(node.parm('f2').eval()) if node.parm('f2') else 1,
                    'skip_rendered': node.parm('RS_outputSkipRendered').eval() if node.parm('RS_outputSkipRendered') else 0
                }}
                print("SETTINGS:{{}}".format(json.dumps(settings)))

finally:
    # Restore original stdout/stderr
    sys.stdout = old_stdout
    sys.stderr = old_stderr
""".format(hip_file)

            # Run hython with environment variables to suppress output
            env = os.environ.copy()
            env['HOU_VERBOSITY'] = '0'
            env['RS_VERBOSITY_LEVEL'] = '0'

            result = subprocess.run(
                ['hython', '-c', script],
                capture_output=True,
                text=True,
                env=env,
                encoding='utf-8'
            )

            # Parse the output to get nodes and settings
            nodes = []
            node_settings = {}

            current_node = None
            for line in result.stdout.splitlines():
                if line.startswith('NODE:'):
                    current_node = line[5:].strip()
                    nodes.append(current_node)
                elif line.startswith('SETTINGS:'):
                    if current_node:
                        settings = json.loads(line[9:])
                        node_settings[current_node] = settings

            if nodes:
                print(f"\nFound {len(nodes)} out nodes with settings:")
                for node in nodes:
                    print(f"  {node}: {node_settings[node]}")
            else:
                print("\nNo out nodes found")
                if result.stderr:
                    print("Error:", result.stderr.split('\n')[0])

            return nodes, node_settings

        except Exception as e:
            print(f"Error running hython: {e}")
            return [], {}

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.png"))

    # Create main window
    window = HoudiniRenderGUI()
    window.show()
    sys.exit(app.exec())
