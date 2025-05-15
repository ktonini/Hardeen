from PySide6.QtWidgets import QWidget, QToolTip, QApplication
from PySide6.QtCore import Qt, QEvent, QRectF, QTimer, QPoint
from PySide6.QtGui import QPainter, QColor
from ...utils.time_utils import format_time
from ..widgets.custom_tooltip import CustomToolTip
import sys

class FrameProgressWidget(QWidget):
    """Custom widget to display frame progress with variable-height bars"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(50)  # Set minimum height for the bar graph
        self.setMinimumWidth(100)

        # Ensure proper rendering
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        # Set update behavior
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)

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

        # Transitions
        self.recently_completed = set()  # Set of recently completed frames
        self.transition_timer = QTimer(self)
        self.transition_timer.timeout.connect(self.clear_transitions)
        self.transition_timer.setSingleShot(True)

        # Tooltip handling
        self.tooltip = CustomToolTip.instance()
        self.hover_widget_pos = -1
        self.setMouseTracking(True)  # Enable mouse tracking to detect hover

        # Debug flag
        self.debug_paint = False

        # Colors
        self.completed_color = QColor("#22adf2")  # Blue for completed frames
        self.current_color = QColor("#ff4c00")    # Orange for current frame
        self.placeholder_color = QColor("#444444")  # Dark gray for placeholder
        self.skipped_color = QColor("#666666")    # Lighter gray for skipped frames

        # Set background color and important styling for visibility
        self.setStyleSheet("""
            border: 0px solid #555555;
            border-radius: 4px;
        """)

        # Current position for tooltips
        self.hover_position = -1

        # Create update timer to force regular repaints
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.forceRepaint)
        self.update_timer.start(500)  # Update every 500ms

    def clear_transitions(self):
        """Clear the recently completed transitions list"""
        if self.recently_completed:
            self.recently_completed.clear()
            self.update()  # Update once more after clearing

    def forceRepaint(self):
        """Force a repaint even if no explicit updates have been triggered"""
        if self.isVisible() and self.total_frames > 0:
            self.update()

    def showEvent(self, event):
        """Handle show event to ensure widget is properly displayed"""
        super().showEvent(event)
        # Schedule a deferred update
        QTimer.singleShot(100, self.update)

    def paintEvent(self, event):
        """Paint the frame progress bars"""
        try:
            if self.debug_paint:
                print(f"DEBUG: paintEvent triggered in FrameProgressWidget, visible={self.isVisible()}, total_frames={self.total_frames}")
                if self.current_frame is not None:
                    print(f"DEBUG: Current frame in progress: {self.current_frame}, progress: {self.current_frame_progress}%")
                print(f"DEBUG: Frame times: {self.frame_times}")

            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # Make background transparent
            painter.fillRect(self.rect(), Qt.transparent)

            if self.total_frames <= 0:
                if self.debug_paint:
                    print("DEBUG: No frames to draw")
                return

            # Calculate bar width
            bar_width = self.width() / self.total_frames
            # Ensure there's a minimum width
            bar_width = max(3, bar_width)
            # Allow for tiny 1px spacing between bars if they're wide enough
            spacing = 1 if bar_width >= 5 else 0

            # Use full height for bars since we removed the text
            available_height = self.height()

            # Draw placeholder bars first (lowest priority)
            for widget_pos in range(self.total_frames):
                x = widget_pos * bar_width

                # Skip this frame position if it would be too small to see
                if x + bar_width <= 0 or x >= self.width():
                    continue

                # Skip positions that will be drawn in later phases
                if (widget_pos == self.current_frame or
                    widget_pos in self.frame_times or
                    widget_pos in self.recently_completed):
                    continue

                # Draw placeholder bar with rounded corners
                painter.setPen(Qt.NoPen)
                painter.setBrush(self.placeholder_color)
                painter.drawRoundedRect(
                    QRectF(x, self.height() - self.placeholder_height, bar_width - spacing, self.placeholder_height),
                    2, 2
                )

            # Draw completed and skipped frames (middle priority)
            for widget_pos, time in self.frame_times.items():
                # Skip if it's the current frame (will be drawn later) or not a valid position
                if widget_pos == self.current_frame or widget_pos >= self.total_frames:
                    continue

                x = widget_pos * bar_width

                if time > 0:
                    # Completed frame - blue bar with height based on render time
                    height = min((time / self.max_time) * available_height, available_height)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(self.completed_color)
                    painter.drawRoundedRect(
                        QRectF(x, self.height() - height, bar_width - spacing, height),
                        2, 2
                    )
                else:
                    # Skipped frame - small placeholder bar with lighter color
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(self.skipped_color)
                    painter.drawRoundedRect(
                        QRectF(x, self.height() - self.placeholder_height, bar_width - spacing, self.placeholder_height),
                        2, 2
                    )

            # Draw current frame (highest priority)
            if self.current_frame is not None and self.current_frame < self.total_frames:
                x = self.current_frame * bar_width

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

                painter.setPen(Qt.NoPen)
                painter.setBrush(self.current_color)
                painter.drawRoundedRect(
                    QRectF(x, self.height() - height, bar_width - spacing, height),
                    2, 2
                )

            if self.debug_paint:
                print(f"DEBUG: Drew {self.total_frames} frame bars")
        except Exception as e:
            print(f"ERROR in FrameProgressWidget.paintEvent: {str(e)}")
            # Try to finish the paint event gracefully
            if 'painter' in locals():
                painter.end()

    def event(self, event):
        """Handle various events including tooltips"""
        if event.type() == QEvent.Type.ToolTip:
            # Ignore standard tooltip events since we're using custom tooltips
            event.ignore()
            return True

        return super().event(event)

    def mouseMoveEvent(self, event):
        """Handle mouse movement to show tooltips"""
        if self.total_frames <= 0:
            return

        # Calculate which frame bar is under the cursor
        bar_width = self.width() / self.total_frames
        widget_pos = int(event.pos().x() / bar_width)

        # If moved to a different bar, update tooltip
        if widget_pos != self.hover_widget_pos:
            self.hover_widget_pos = widget_pos

            if 0 <= widget_pos < self.total_frames:
                # Get tooltip text for this position
                tooltip_text = self.get_frame_info_at_position(event.pos())
                if tooltip_text:
                    # Show tooltip slightly above the bar to avoid obscuring it
                    bar_center_x = (widget_pos + 0.5) * bar_width
                    # Position the tooltip 15 pixels above the widget
                    global_pos = self.mapToGlobal(QPoint(int(bar_center_x), self.height() + 15))
                    # Use a shorter delay for a more responsive feel
                    self.tooltip.show_tooltip(tooltip_text, global_pos, delay=200, timeout=4000)
                else:
                    self.tooltip.hide_tooltip()
            else:
                self.tooltip.hide_tooltip()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Hide tooltip when mouse leaves the widget"""
        self.hover_widget_pos = -1
        self.tooltip.hide_tooltip()
        super().leaveEvent(event)

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
            tooltip = f"<b>Frame {frame_number}</b> - <span style='color:#ff4c00;'>In progress</span><br>"
            tooltip += f"Progress: <b>{self.current_frame_progress}%</b>"
            if self.estimated_current_frame_time > 0:
                tooltip += f"<br>Estimated time: <b>{format_time(self.estimated_current_frame_time)}</b>"
            return tooltip

        elif widget_pos in self.frame_times:
            # Completed or skipped frame
            time = self.frame_times[widget_pos]
            if time > 0:
                # Completed frame
                return f"<b>Frame {frame_number}</b><br>Render time: <b>{format_time(time)}</b>"
            else:
                # Skipped frame
                return f"<b>Frame {frame_number}</b> - <span style='color:#ffa500;'>Skipped</span><br>File already exists"
        else:
            # Not yet rendered
            return f"<b>Frame {frame_number}</b> - <span style='color:#aaaaaa;'>Pending</span>"

    def set_total_frames(self, total, frame_range=None):
        """Set the total number of frames and optionally the frame range"""
        print(f"DEBUG: Set total frames to {total}, ensuring progress_frame is visible")
        self.total_frames = total
        if frame_range:
            self.frame_range = frame_range
            # Create bidirectional mappings
            self.frame_to_index = {frame: i for i, frame in enumerate(frame_range)}
            self.index_to_frame = {i: frame for i, frame in enumerate(frame_range)}
            print(f"DEBUG: Frame range: {frame_range}")
            print(f"DEBUG: Frame to index mapping: {self.frame_to_index}")
        else:
            self.frame_range = None
            self.frame_to_index = {}
            self.index_to_frame = {}
            print(f"DEBUG: No frame range specified")
        self.update()

    def update_frame_progress(self, frame, progress, estimated_time=None):
        """Update the progress of the current frame (0-100%)"""
        # Convert frame number to widget position
        widget_pos = self._get_widget_position(frame)
        print(f"DEBUG: Updating frame progress for frame {frame} (widget position {widget_pos}) to {progress}%")

        # Store the widget position as the current frame
        self.current_frame = widget_pos
        self.current_frame_progress = progress

        # If progress is 100%, move this frame to completed frames
        if progress >= 100:
            # Use the estimated time if provided, otherwise use our current estimate
            if estimated_time is not None:
                time_value = estimated_time
            elif self.estimated_current_frame_time > 0:
                time_value = self.estimated_current_frame_time
            else:
                # Default to average time if we have no estimate
                times = [t for t in self.frame_times.values() if t > 0]
                time_value = sum(times) / len(times) if times else 1.0

            # Set the frame as completed by storing its time directly
            self.frame_times[widget_pos] = time_value
            self.max_time = max(self.max_time, time_value)  # Update max time for scaling

            # Add to recently completed frames for smooth transition
            self.recently_completed.add(widget_pos)

            # Clear current frame markers - this frame is now complete
            self.current_frame = None  # Clear current frame
            self.current_frame_progress = 0
            print(f"DEBUG: Frame {frame} is complete with time {time_value}")

            # Start transition timer to clear transitions after a delay
            self.transition_timer.start(500)  # 500ms delay
        # If we have an estimated time, update it
        elif estimated_time is not None:
            self.estimated_current_frame_time = estimated_time
            if estimated_time > self.max_time:
                self.max_time = estimated_time
            print(f"DEBUG: Estimated time for frame {frame}: {estimated_time}")

        self.update()

    def add_frame_time(self, frame, time):
        """Add a completed frame and its render time"""
        # Convert frame number to widget position
        widget_pos = self._get_widget_position(frame)
        print(f"DEBUG: Adding frame time for frame {frame} (widget position {widget_pos}): {time}")

        # Store frame time and update max time
        self.frame_times[widget_pos] = time
        self.max_time = max(self.max_time, time)  # Update max time for scaling

        # Add to recently completed frames for smooth transition
        self.recently_completed.add(widget_pos)

        # If this was the current frame, we need to handle the transition carefully
        # First update the frame_times dictionary, then clear the current frame state
        # This ensures the completed frame bar will be drawn immediately without showing a placeholder
        if widget_pos == self.current_frame:
            # Just clear the current frame markers after setting the frame time
            self.current_frame = None
            self.current_frame_progress = 0
            print(f"DEBUG: Current frame {frame} completed with time {time}")

        # Start transition timer to clear transitions after a delay
        self.transition_timer.start(500)  # 500ms delay

        # Force an immediate update to prevent any visual gaps
        self.update()

    def set_frame_skipped(self, frame):
        """Mark a frame as skipped (will use a placeholder bar)"""
        # Convert frame number to widget position
        widget_pos = self._get_widget_position(frame)
        print(f"DEBUG: Marking frame {frame} (widget position {widget_pos}) as skipped")

        self.frame_times[widget_pos] = 0  # Skipped frames get 0 time

        # Clear current frame if this was the current frame
        if widget_pos == self.current_frame:
            self.current_frame = None
            self.current_frame_progress = 0

        self.update()

    def _get_widget_position(self, frame):
        """Convert a frame number to a widget position"""
        # If we have a frame range, use the mapping
        if self.frame_to_index and frame in self.frame_to_index:
            return self.frame_to_index[frame]
        # Otherwise, adjust for 0-based widget positions vs 1-based frame numbers
        return frame - 1 if frame is not None else None

    def clear(self):
        """Clear all frame data"""
        print("DEBUG: Clearing all frame data")
        self.frame_times.clear()
        self.current_frame = None  # Changed to None
        self.current_frame_progress = 0
        self.max_time = 1.0
        self.estimated_current_frame_time = 0.0
        self.frame_range = None
        self.frame_to_index = {}
        self.index_to_frame = {}

        # Clear transition tracking
        self.recently_completed.clear()
        if self.transition_timer.isActive():
            self.transition_timer.stop()

        self.update()

    def format_time(self, seconds):
        """Format time in seconds to human readable string"""
        return format_time(seconds)
