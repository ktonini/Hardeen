import os
import datetime
from typing import Optional, List, Dict, Callable, Any
from PySide6.QtCore import QObject, Signal, QDateTime, Slot
from ...utils.time_utils import format_time

class RenderStatusManager(QObject):
    """
    Manages the render status and progress tracking.
    This class separates the render status logic from the UI.
    """
    # Define signals for status updates
    progress_signal = Signal(int, int)  # current_frame, total_frames
    frame_progress_signal = Signal(int, int)  # frame_number, percent
    frame_completed_signal = Signal(int, float)  # frame_number, render_time
    frame_skipped_signal = Signal(int)  # frame_number
    image_update_signal = Signal(str)  # image_path
    time_labels_signal = Signal(float, float, float, float, QDateTime, bool)  # elapsed, avg, total, remaining, eta, show_eta
    render_finished_signal = Signal()  # Signal to safely handle render completion
    output_signal = Signal(str)  # For formatted output messages

    def __init__(self, output_callback: Callable = None, raw_output_callback: Callable = None):
        """Initialize the render status manager."""
        super().__init__()

        # Render state variables
        self.render_start_time = None
        self.total_frames = 0
        self.current_frame = 0
        self.rendered_image_path = None
        self.output_folder = None

        # Callback functions
        self.output_callback = output_callback
        self.raw_output_callback = raw_output_callback

    def setup_callbacks(self, render_manager):
        """Set up callbacks for the render manager."""
        render_manager.register_callbacks(
            output_callback=self.append_output_safe,
            raw_output_callback=self.append_raw_output_safe,
            progress_callback=self.update_progress,
            frame_progress_callback=self.frame_progress_signal.emit,
            frame_completed_callback=self.frame_completed_signal.emit,
            frame_skipped_callback=self.frame_skipped_signal.emit,
            image_update_callback=self.image_update_signal.emit,
            render_finished_callback=self.on_render_finished_from_thread,
            time_labels_callback=self.time_labels_signal.emit
        )

    def set_total_frames(self, total: int, frame_range: Optional[List[int]] = None):
        """Set the total number of frames to be rendered."""
        self.total_frames = total

    def start_render(self):
        """Initialize render state variables when a render starts."""
        self.render_start_time = datetime.datetime.now()
        self.current_frame = 0
        self.rendered_image_path = None

    def update_progress(self, current: int, total: int):
        """Update overall progress."""
        if current is not None:
            self.current_frame = current
            # If total has changed, update our total_frames
            if total != self.total_frames:
                self.total_frames = total

            # Always emit the progress signal to ensure UI is updated
            self.progress_signal.emit(current, self.total_frames)

    def get_elapsed_time(self) -> float:
        """Calculate the elapsed time since render started."""
        if self.render_start_time:
            return (datetime.datetime.now() - self.render_start_time).total_seconds()
        return 0

    def on_render_finished_from_thread(self):
        """Called from render thread when render is finished."""
        # Forward the signal
        self.render_finished_signal.emit()

    def update_image(self, image_path: str):
        """Update the image path when a new image is rendered."""
        if not image_path or not os.path.exists(image_path):
            return

        # Store the image path
        self.rendered_image_path = image_path

        # Store the output folder from the image path
        self.output_folder = os.path.dirname(image_path)

    def append_output_safe(self, text: str, color: Optional[str] = None, bold: bool = False, center: bool = False):
        """Safe way to append formatted output."""
        if self.output_callback:
            self.output_callback(text, color, bold, center)
        # Don't emit signal - this causes duplication
        # self.output_signal.emit(text)

    def append_raw_output_safe(self, text: str):
        """Safe way to append raw output."""
        if self.raw_output_callback:
            self.raw_output_callback(text)

    def get_status_summary(self) -> Dict[str, Any]:
        """Get a summary of the current render status."""
        elapsed = self.get_elapsed_time()
        return {
            'current_frame': self.current_frame,
            'total_frames': self.total_frames,
            'elapsed_time': elapsed,
            'elapsed_time_formatted': format_time(elapsed),
            'rendered_image_path': self.rendered_image_path,
            'output_folder': self.output_folder
        }

    def get_notification_data(self, job_name: str) -> Dict[str, Any]:
        """Get data for notifications about render status."""
        elapsed = self.get_elapsed_time()
        return {
            'job_name': job_name,
            'current_frame': self.current_frame,
            'total_frames': self.total_frames,
            'elapsed_time': elapsed,
            'elapsed_time_formatted': format_time(elapsed),
            'rendered_image_path': self.rendered_image_path
        }
