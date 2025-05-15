import os
import sys
import time
import signal
import datetime
import traceback
from pathlib import Path
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QComboBox, QSpinBox, QCheckBox, QLineEdit, QGroupBox,
    QProgressBar, QMessageBox, QFileDialog, QFrame, QSplitter, QTextEdit, QDialog,
    QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QPoint, QSize, QRectF, QPointF, QDateTime, QMetaObject, QThread
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPolygon, QPainterPath, QFont, QTextCursor, QTextBlockFormat, QTextCharFormat, QPalette
import subprocess
import threading
import tempfile
import requests

from ..core.render_manager import RenderManager
from ..core.notifications import (
    NotificationManager,
    NotificationConfig,
    NotificationPriority,
    NotificationSettings
)
from ..gui.widgets.frame_progress import FrameProgressWidget
from ..gui.widgets.loading_combo_box import LoadingComboBox
from ..gui.widgets.image_preview import ImagePreviewWidget
from ..utils.time_utils import format_time
from ..utils.settings import Settings
from ..gui.settings_dialog import SettingsDialog
from ..gui.window_components import RenderStatusManager, ShutdownManager, TextOutputManager, HipFileManager, FrameValidationManager, RenderControlManager
from ..gui.ui_components import UIComponents
from ..gui.settings_manager import SettingsManager
from ..gui.notification_manager import NotificationUIManager
from ..config import (
    DEFAULT_FOLDER, DEFAULT_OUTNODE, DEFAULT_LOG,
    APP_NAME, APP_ORGANIZATION, APP_VERSION
)
from ..utils.image_utils import load_exr_aovs

class Hardeen(QMainWindow):
    """Main window for the Houdini render manager"""

    # Define signals for thread-safe UI updates
    output_signal = Signal(str)

    def __init__(self):
        super().__init__()

        # Set a dark theme for tooltips for the whole app
        from PySide6.QtGui import QPalette, QColor
        from PySide6.QtWidgets import QApplication
        palette = QApplication.palette()
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#232323"))  # dark background
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#ffffff"))  # white text
        QApplication.setPalette(palette)
        app = QApplication.instance()
        app.setStyleSheet(app.styleSheet() + "\nQToolTip { color: #fff; background-color: #232323; border: 1px solid #444; padding: 6px 10px; }")

        # Initialize managers
        self.render_manager = RenderManager()
        self.settings_manager = SettingsManager(self)
        self.notification_ui_manager = NotificationUIManager(self.settings_manager, self)
        self.notification_settings = self.settings_manager.get_notification_settings()

        # Signal connection flags
        self.out_node_signal_connected = False

        # Hip file manager will be initialized after UI setup
        self.hip_file_manager = None

        # Text output manager will be initialized after UI setup
        self.text_output_manager = None

        # Frame validation manager will be initialized after UI setup
        self.frame_validation_manager = None

        # Initialize render status manager
        self.render_status = RenderStatusManager(
            output_callback=self.append_output_safe,
            raw_output_callback=self.append_raw_output_safe
        )

        # Initialize shutdown manager
        self.shutdown_manager = ShutdownManager(
            parent=self,
            settings_manager=self.settings_manager,
            output_callback=self.append_output_safe
        )

        # Flag to track when settings are being loaded
        self._loading_settings = True  # Start in loading state

        # Flag to track initial load to prevent duplicate out node parsing
        self._initial_load_complete = False

        # Create update timer in the main thread
        self.update_timer = QTimer(self)  # Parent to self to ensure main thread ownership
        self.update_timer.timeout.connect(self.update_status)

        # Create debounce timer
        self._save_settings_timer = QTimer(self)  # Parent to self to ensure main thread ownership
        self._save_settings_timer.setSingleShot(True)
        self._save_settings_timer.setInterval(300)  # 300ms debounce
        self._save_settings_timer.timeout.connect(self._debounced_save_settings)

        # Setup UI
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setup_ui()

        # Initialize the text output manager now that UI is set up
        self.text_output_manager = TextOutputManager(
            parent=self,
            summary_text_widget=self.summary_text,
            raw_text_widget=self.raw_text
        )

        # Initialize the frame validation manager now that UI is set up
        self.frame_validation_manager = FrameValidationManager(
            parent=self,
            start_frame=self.start_frame,
            end_frame=self.end_frame,
            frame_step=self.frame_step,
            range_check=self.range_check,
            skip_check=self.skip_check,
            out_input=self.out_input,
            settings_manager=self.settings_manager,
            hip_file_manager=None  # Will be set after hip_file_manager is initialized
        )

        # Initialize the hip file manager - set loading mode first
        self.hip_file_manager = HipFileManager(
            parent=self,
            hip_input=self.hip_input,
            out_input=self.out_input,
            settings_manager=self.settings_manager
        )
        self.hip_file_manager.set_loading_settings_state(True)  # Set loading state

        # Update the frame_validation_manager with the hip_file_manager
        self.frame_validation_manager.hip_file_manager = self.hip_file_manager

        # Initialize the render control manager
        self.render_control_manager = RenderControlManager(
            parent=self,
            render_manager=self.render_manager,
            render_status_manager=self.render_status,
            notification_ui_manager=self.notification_ui_manager,
            settings_manager=self.settings_manager,
            text_output_manager=self.text_output_manager,
            shutdown_manager=self.shutdown_manager,
            ui_components={
                'render_btn': self.render_btn,
                'cancel_btn': self.cancel_btn,
                'open_folder_btn': self.open_folder_btn,
                'hip_input': self.hip_input,
                'out_input': self.out_input,
                'start_frame': self.start_frame,
                'end_frame': self.end_frame,
                'frame_step': self.frame_step,
                'range_check': self.range_check,
                'skip_check': self.skip_check,
                'notify_check': self.notify_check,
                'shutdown_check': self.shutdown_check,
                'shutdown_delay': self.shutdown_delay,
                'progress_frame': self.progress_frame,
                'image_preview': self.image_preview,
                'hip_file_manager': self.hip_file_manager,
                'append_output_safe': self.append_output_safe,
            }
        )

        # Connect render control buttons now that the render_control_manager is initialized
        self.render_btn.clicked.connect(self.render_control_manager.handle_render_button)
        self.cancel_btn.clicked.connect(self.render_control_manager.interrupt_render)

        # Connect hip file manager signals
        self.hip_file_manager.output_update.connect(self.append_output_safe)
        self.hip_file_manager.out_nodes_loaded.connect(self.on_out_nodes_loaded)

        # Connect UI signal handlers for hip file operations
        # Important: Only connect after setting loading state to prevent auto-refresh
        self.hip_input.currentTextChanged.connect(self.hip_file_manager.on_hip_file_changed)
        self.hip_browse_btn.clicked.connect(self.hip_file_manager.browse_hip_file)
        self.hip_refresh_btn.clicked.connect(self.hip_file_manager.load_hip_files)
        self.out_refresh_btn.clicked.connect(self.hip_file_manager.refresh_out_nodes)

        # Start update timer
        self.update_timer.start(1000)  # Update every second

        # Load initial state and settings - all in loading mode
        self.hip_file_manager.load_hip_files()
        self.settings_manager.load_settings(self)

        # Update settings display
        self.settings_manager.update_settings_display(self)

        # Mark initial load as complete and exit loading state
        self._initial_load_complete = True
        self._loading_settings = False
        self.hip_file_manager.set_loading_settings_state(False)

        # Connect render manager callbacks via render status manager
        self.render_status.setup_callbacks(self.render_manager)

        # Connect signals from the render status manager to UI update methods
        self.render_status.progress_signal.connect(self.update_progress)
        self.render_status.frame_progress_signal.connect(self.update_frame_progress)
        self.render_status.frame_completed_signal.connect(self.update_frame_completed)
        self.render_status.frame_skipped_signal.connect(self.update_frame_skipped)
        self.render_status.image_update_signal.connect(self.update_image)
        self.render_status.time_labels_signal.connect(self.update_time_labels)
        self.render_status.render_finished_signal.connect(self.render_control_manager.render_finished)

        # Create image handler instance
        self.image_handler = self.image_preview.image_handler
        self.image_handler.output_callback = self.append_output_safe
        self.image_handler.raw_output_callback = self.append_raw_output_safe

        # Now that loading is complete, do a single refresh of out nodes if a hip file is selected
        # This is the only place where we explicitly call refresh_out_nodes during initialization
        if self.hip_input.currentText():
            QTimer.singleShot(300, self.hip_file_manager.refresh_out_nodes)

    @property
    def notification_manager(self):
        """Property to access the notification manager from notification_ui_manager"""
        return self.notification_ui_manager.notification_manager

    @notification_manager.setter
    def notification_manager(self, value):
        """Setter for notification_manager - this will be ignored as we always use notification_ui_manager's instance"""
        pass

    def setup_ui(self):
        """Setup the main window UI"""
        # Set main window to allow resize in both directions
        self.setMinimumSize(800, 600)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        central_widget = QWidget()
        central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(4)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # --- Hip Path ---
        hip_layout, self.hip_input, self.hip_browse_btn, self.hip_refresh_btn = UIComponents.create_hip_path_section(self)
        main_layout.addLayout(hip_layout)

        # --- Out Path ---
        out_layout, self.out_input, self.out_refresh_btn = UIComponents.create_out_path_section(self)
        main_layout.addLayout(out_layout)

        # --- Overrides Group ---
        self.overrides_group, self.range_check, self.start_frame, self.end_frame, self.frame_step, self.skip_check = UIComponents.create_overrides_group(self)
        # Frame validation signals will be connected by the FrameValidationManager
        main_layout.addWidget(self.overrides_group)

        # --- Advanced Settings Group ---
        (
            self.settings_group, self.notify_check, self.notify_frames,
            self.shutdown_check, self.shutdown_delay, self.help_btn, self.settings_btn
        ) = UIComponents.create_advanced_settings_group(self)

        self.notify_check.stateChanged.connect(self.on_notification_settings_changed)
        self.notify_frames.textChanged.connect(self.on_notification_settings_changed)
        self.shutdown_check.stateChanged.connect(self.on_shutdown_settings_changed)
        self.shutdown_delay.currentIndexChanged.connect(self.on_shutdown_settings_changed)
        self.help_btn.clicked.connect(self.show_help_dialog)
        self.settings_btn.clicked.connect(self.show_settings_dialog)
        main_layout.addWidget(self.settings_group)
        main_layout.addSpacing(2)  # Minimal spacing between groups

        # --- Render Control Buttons ---
        controls_layout, self.open_folder_btn, self.cancel_btn, self.render_btn = UIComponents.create_control_buttons(self)
        self.open_folder_btn.clicked.connect(self.open_output_location)
        main_layout.addLayout(controls_layout)
        main_layout.addSpacing(4)  # Reduced spacing after buttons

        # --- Output/Summary and Raw Output Area ---
        self.text_splitter, self.summary_text, self.raw_text = UIComponents.create_text_output_area(self)
        main_layout.addWidget(self.text_splitter, 1)

        # --- Image Preview Area ---
        self.image_preview = UIComponents.create_image_preview(self)
        main_layout.addWidget(self.image_preview, 2)  # Give it a higher stretch factor (2 instead of 1)

        # --- Frame Progress Widget ---
        self.progress_frame = UIComponents.create_frame_progress_widget(self)
        main_layout.addWidget(self.progress_frame)

        # --- Stats/Info Line ---
        (
            stats_layout,
            self.fc_label, self.fc_value, self.tfc_label, self.tfc_value,
            self.average_label, self.average_value, self.elapsed_label, self.elapsed_value,
            self.total_label, self.total_value, self.eta_label, self.eta_value,
            self.remaining_label, self.remaining_value
        ) = UIComponents.create_stats_layout(self)
        main_layout.addLayout(stats_layout)

        # Apply stylesheet
        UIComponents.apply_stylesheet(self)

        # Initialize the enabled/disabled state of fields
        self.toggle_frame_range()

    def show(self):
        """Show the main window"""
        super().show()

    def toggle_frame_range(self, skip_validation=False):
        """Proxy to the frame_validation_manager's toggle_frame_range method"""
        if self.frame_validation_manager:
            self.frame_validation_manager.toggle_frame_range(skip_validation)

    def on_out_node_changed(self, node_path: str):
        """Handle out node selection changes"""
        # Don't process if loading settings
        if hasattr(self, '_loading_settings') and self._loading_settings:
            return

        # Get node settings from hip file manager
        node_settings = self.hip_file_manager.get_node_settings() if self.hip_file_manager else {}

        # Update frame validation manager with node settings
        if self.frame_validation_manager:
            self.frame_validation_manager.update_from_node_settings(node_path, node_settings)

        # Save the selected out node
        self.settings_manager.save_settings_debounced(self)

    def append_output_safe(self, text, color=None, bold=False, center=False):
        """Queue summary text updates to be processed in the main thread"""
        if self.text_output_manager:
            self.text_output_manager.append_output_safe(text, color, bold, center)

    def process_summary_updates(self):
        """Process queued summary text updates in the main thread (proxy to TextOutputManager)"""
        if self.text_output_manager:
            self.text_output_manager.process_summary_updates()

    def append_raw_output_safe(self, text):
        """Queue raw text updates to be processed in the main thread"""
        if self.text_output_manager:
            self.text_output_manager.append_raw_output_safe(text)

    def process_raw_updates(self):
        """Process queued raw text updates in the main thread (proxy to TextOutputManager)"""
        if self.text_output_manager:
            self.text_output_manager.process_raw_updates()

    def handle_render_button(self):
        """Unified handler for Render/Interrupt/Kill button."""
        self.render_control_manager.handle_render_button()

    def closeEvent(self, event):
        """Handle window close event"""
        # Process any remaining text updates via text output manager
        if self.text_output_manager:
            self.text_output_manager.process_remaining_and_clear()

        # Check if render is in progress and ask user if they want to cancel
        if not self.render_control_manager.handle_render_close(event):
                event.ignore()
                return

        # Save current settings before closing
        self.save_settings()

        event.accept()

    def on_notification_settings_changed(self):
        """Handle changes to notification settings in the main UI"""
        self.settings_manager.on_notification_settings_changed(self)

    def on_shutdown_settings_changed(self):
        """Handle changes to shutdown settings in the main UI"""
        self.settings_manager.on_shutdown_settings_changed(self)

    def show_settings_dialog(self):
        """Show the settings dialog"""
        # The dialog will get access to the shutdown manager through the settings_manager
        dialog = self.settings_manager.show_settings_dialog(self)

        # No need to connect signals manually anymore as the dialog
        # now has direct access to the shutdown manager

    def apply_settings(self, settings_dict):
        """Apply settings from the dialog"""
        self.settings_manager.apply_settings(self, settings_dict)

    def update_settings_display(self):
        """Update the settings display in the main window"""
        self.settings_manager.update_settings_display(self)

    def update_notification_manager(self):
        """Update notification manager with current settings"""
        self.settings_manager.update_notification_manager()

    def test_notification(self):
        """Send a test notification through Pushover"""
        self.notification_ui_manager.test_notification(self, self.append_output_safe)

    def send_push_notification(self, message, image_path=None):
        """Send push notification with optional image"""
        self.notification_ui_manager.send_push_notification(message, image_path, self.append_output_safe)

    def update_status(self):
        """Update UI with current render status"""
        self.render_control_manager.update_status()

    def open_output_location(self):
        """Open the output folder in file explorer"""
        # Get output folder from render status manager
        output_folder = self.render_status.output_folder

        if output_folder:
            folder = output_folder
        else:
            # If no specific folder, use the hip file's directory
            folder = os.path.dirname(self.hip_input.currentText())

        try:
            if sys.platform == 'win32':
                os.startfile(folder)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', folder])
            else:
                subprocess.Popen(['xdg-open', folder])
        except Exception as e:
            print(f"Error opening folder: {e}")
            QMessageBox.warning(self, "Error", f"Could not open folder: {str(e)}")

    def show_help_dialog(self):
        """Show the help dialog with usage tips"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Hardeen - Help & Tips")
        help_dialog.setMinimumWidth(500)
        help_dialog.setMinimumHeight(300)

        layout = QVBoxLayout(help_dialog)

        # Title
        title_label = QLabel("Hardeen Render Manager - Tips & Tricks")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ff6b2b;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Batch rendering tips section
        batch_group = QGroupBox("Batch Rendering")
        batch_layout = QVBoxLayout(batch_group)

        batch_tips = QLabel(
            "<p><b>For batch rendering:</b></p>"
            "<ul>"
            "<li>Point the 'Out Path' field to a merge node with multiple ROPs connected to it.</li>"
            "<li>The 'Frame Range' override will be ignored, instead using the range set up in Houdini.</li>"
            "<li>Each ROP should have:</li>"
            "<ul>"
            "<li>'Non-blocking Current Frame Rendering' unchecked.</li>"
            "<li>'Valid Frame Range' set to 'Render Frame Range Only (Strict)' if the ROPs have different ranges.</li>"
            "</ul>"
            "</ul>"
        )
        batch_tips.setWordWrap(True)
        batch_tips.setTextFormat(Qt.TextFormat.RichText)
        batch_layout.addWidget(batch_tips)
        layout.addWidget(batch_group)

        # General usage tips
        usage_group = QGroupBox("General Usage")
        usage_layout = QVBoxLayout(usage_group)

        usage_tips = QLabel(
            "<p><b>General tips:</b></p>"
            "<ul>"
            "<li>Use the 'Skip Rendered Frames' option to avoid re-rendering existing frames.</li>"
            "<li>Frame progress is shown in the status bar at the bottom.</li>"
            "<li>Notifications can be configured to alert you on render progress.</li>"
            "<li>Computer shutdown can be scheduled after render completes.</li>"
            "</ul>"
        )
        usage_tips.setWordWrap(True)
        usage_tips.setTextFormat(Qt.TextFormat.RichText)
        usage_layout.addWidget(usage_tips)
        layout.addWidget(usage_group)

        # Keyboard shortcuts section
        shortcut_group = QGroupBox("Keyboard Shortcuts")
        shortcut_layout = QVBoxLayout(shortcut_group)

        shortcut_tips = QLabel(
            "<p><b>Keyboard shortcuts:</b></p>"
            "<table border='0' cellspacing='5'>"
            "<tr><td><b>F5</b></td><td>Refresh out nodes</td></tr>"
            "<tr><td><b>Ctrl+R</b></td><td>Start render</td></tr>"
            "<tr><td><b>Esc</b></td><td>Interrupt render</td></tr>"
            "</table>"
        )
        shortcut_tips.setWordWrap(True)
        shortcut_tips.setTextFormat(Qt.TextFormat.RichText)
        shortcut_layout.addWidget(shortcut_tips)
        layout.addWidget(shortcut_group)

        # Buttons
        button_layout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(help_dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        # Apply the same style as the main window
        help_dialog.setStyleSheet(self.styleSheet())

        help_dialog.exec()

    def update_progress(self, current, total):
        """Update progress bars"""
        # Use QTimer.singleShot to ensure UI updates happen in the main thread
        if current is not None:
            # Update frame count display in the main thread
            def _update_ui():
                try:
                    # Get current status from status manager
                    status_total = self.render_status.total_frames

                    # Update frame count display
                    self.fc_value.setText(str(current))
                    self.tfc_value.setText(str(status_total))

                    # Update the progress frame with the total frames
                    if total != self.progress_frame.total_frames:
                        # If the range_check is checked, we need to create a frame range
                        if self.range_check.isChecked():
                            start = int(self.start_frame.text())
                            end = int(self.end_frame.text())
                            step = int(self.frame_step.currentText())
                            frame_range = list(range(start, end + 1, step))
                            self.progress_frame.set_total_frames(total, frame_range)
                        else:
                            self.progress_frame.set_total_frames(total)

                        # Make sure the progress frame is visible but use update() instead of repaint()
                        print(f"DEBUG: Set total frames to {total}, ensuring progress_frame is visible")
                        self.progress_frame.show()
                        # Use update() instead of repaint() to avoid recursive repaints
                        self.progress_frame.update()

                    # Enable output folder button once we have progress
                    output_folder = self.render_status.output_folder
                    if not self.open_folder_btn.isEnabled() and output_folder:
                        self.open_folder_btn.setEnabled(True)
                except Exception as e:
                    print(f"Error in update_progress: {str(e)}")

            # Use singleShot with 0 timeout to execute in main thread
            QTimer.singleShot(0, _update_ui)

    def update_frame_progress(self, frame_index, progress):
        """Update progress for a specific frame"""
        if frame_index is not None and progress is not None:
            print(f"DEBUG: update_frame_progress called for frame {frame_index} with progress {progress}")
            print(f"DEBUG: Is progress_frame visible? {self.progress_frame.isVisible()}")
            print(f"DEBUG: progress_frame geometry: {self.progress_frame.geometry()}")

            # Add more details about frame range and mapping
            if hasattr(self.progress_frame, 'frame_range') and self.progress_frame.frame_range:
                print(f"DEBUG: Frame range: {self.progress_frame.frame_range}")
                print(f"DEBUG: Frame to index mapping: {self.progress_frame.frame_to_index}")
                if frame_index in self.progress_frame.frame_to_index:
                    widget_pos = self.progress_frame.frame_to_index[frame_index]
                    print(f"DEBUG: Frame {frame_index} maps to widget position {widget_pos}")
                else:
                    print(f"DEBUG: Frame {frame_index} not found in mapping")
            else:
                print(f"DEBUG: No frame range mapping, widget position will be {frame_index-1}")

            # Update the frame progress in our custom widget
            self.progress_frame.update_frame_progress(frame_index, progress, None)
            # Force progress frame to be visible
            self.progress_frame.show()
            self.progress_frame.update()  # Use update() instead of repaint()

    def update_frame_completed(self, frame_index, render_time):
        """Handle frame completion"""
        if frame_index is not None and render_time is not None:
            print(f"DEBUG: update_frame_completed called for frame {frame_index} with time {render_time}")
            print(f"DEBUG: Is progress_frame visible? {self.progress_frame.isVisible()}")

            # Add more details about frame range and mapping
            if hasattr(self.progress_frame, 'frame_range') and self.progress_frame.frame_range:
                print(f"DEBUG: Frame range: {self.progress_frame.frame_range}")
                if frame_index in self.progress_frame.frame_to_index:
                    widget_pos = self.progress_frame.frame_to_index[frame_index]
                    print(f"DEBUG: Frame {frame_index} maps to widget position {widget_pos}")
                else:
                    print(f"DEBUG: Frame {frame_index} not found in mapping")
            else:
                print(f"DEBUG: No frame range mapping, widget position will be {frame_index-1}")

            # Update the frame progress widget with the completed frame
            self.progress_frame.add_frame_time(frame_index, render_time)
            # Force progress frame to be visible and update
            self.progress_frame.show()
            self.progress_frame.update()  # Force immediate update

            # Format render time for notifications (not displayed in UI anymore)
            time_str = format_time(render_time)

            # Send notification if interval is set
            if self.notify_check.isChecked():
                interval = int(self.notify_frames.text() or "10")
                if interval > 0 and frame_index % interval == 0:
                    # Get the job name from the hip file
                    job_name = os.path.splitext(os.path.basename(self.hip_input.currentText()))[0]

                    # Find the latest rendered image for this frame if available
                    image_path = self.render_status.rendered_image_path
                    if image_path:
                        print(f"Including latest image in frame notification: {image_path}")

                    # Use the notification UI manager to send the frame notification
                    self.notification_ui_manager.send_frame_completed_notification(
                        job_name=job_name,
                        frame_index=frame_index,
                        total_frames=self.render_status.total_frames,
                        render_time=render_time,
                        image_path=image_path,
                        output_callback=self.append_output_safe
                    )

    def update_frame_skipped(self, frame_index):
        """Handle skipped frame (already exists)"""
        if frame_index is not None:
            print(f"DEBUG: update_frame_skipped called for frame {frame_index}")
            print(f"DEBUG: Is progress_frame visible? {self.progress_frame.isVisible()}")

            # Add more details about frame range and mapping
            if hasattr(self.progress_frame, 'frame_range') and self.progress_frame.frame_range:
                print(f"DEBUG: Frame range: {self.progress_frame.frame_range}")
                if frame_index in self.progress_frame.frame_to_index:
                    widget_pos = self.progress_frame.frame_to_index[frame_index]
                    print(f"DEBUG: Frame {frame_index} maps to widget position {widget_pos}")
                else:
                    print(f"DEBUG: Frame {frame_index} not found in mapping")
            else:
                print(f"DEBUG: No frame range mapping, widget position will be {frame_index-1}")

            # Update the frame progress widget with the skipped frame
            self.progress_frame.set_frame_skipped(frame_index)
            # Force progress frame to be visible and update
            self.progress_frame.show()
            self.progress_frame.update()  # Force immediate update

            # Show information about skipped frames
            self.append_output_safe(
                f"Frame {frame_index} skipped (already rendered)\n",
                color='#ffa500',  # Orange
                bold=False
            )

    def update_image(self, image_path):
        """Update the image preview with the latest rendered image"""
        if not image_path:
            return

        # Update image in render status manager
        self.render_status.update_image(image_path)

        # Get output folder from render status
        output_folder = self.render_status.output_folder

        # Enable the output folder button now that we have output
        if output_folder:
            self.open_folder_btn.setEnabled(True)

        # Use the image preview widget's image handler to load the image
        self.image_preview.load_image(
            image_path,
            output_callback=self.append_output_safe,
            raw_output_callback=self.append_raw_output_safe
        )

    def update_time_labels(self, elapsed, average, total, remaining, eta, show_eta):
        """Update the time labels with current render statistics"""
        # Format all times as human-readable strings
        elapsed_str = format_time(elapsed)
        avg_str = format_time(average)
        total_str = format_time(total)
        remaining_str = format_time(remaining)

        # Update all the time-related labels
        self.elapsed_value.setText(elapsed_str)
        self.average_value.setText(avg_str)
        self.total_value.setText(total_str)
        self.remaining_value.setText(remaining_str)

        # Update ETA display based on the provided datetime
        if show_eta and eta.isValid():
            self.eta_value.setText(eta.toString("hh:mm:ss"))
            self.eta_label.setEnabled(True)
            self.eta_value.setEnabled(True)
        else:
            self.eta_value.setText("--:--:--")
            self.eta_label.setEnabled(False)
            self.eta_value.setEnabled(False)

    def load_settings(self):
        """Load saved settings into UI elements"""
        # Loading flag should already be set when this is called during initialization
        # We don't need to set it again, but we reset it at the end if needed

        # For manual calls to this method, set loading flags to prevent auto-refreshes
        was_loading = self._loading_settings
        was_hip_loading = False

        if not was_loading:
            self._loading_settings = True
            if self.hip_file_manager:
                was_hip_loading = self.hip_file_manager._loading_settings
                self.hip_file_manager.set_loading_settings_state(True)

        # Load settings
        self.settings_manager.load_settings(self)

        # Reset loading flags only if we changed them (not during initialization)
        if not was_loading:
            self._loading_settings = False
            if self.hip_file_manager and not was_hip_loading:
                self.hip_file_manager.set_loading_settings_state(False)

            # Do a single refresh if needed, but only if we weren't already loading
            if self.hip_file_manager and self.hip_input.currentText() and self._initial_load_complete:
                QTimer.singleShot(100, self.hip_file_manager.refresh_out_nodes)

    def save_settings(self):
        """Save current UI state to settings"""
        self.settings_manager.save_settings(self)

    def _debounced_save_settings(self):
        """Save settings after a short delay to avoid excessive saving"""
        self.settings_manager.save_settings_debounced(self)

    def save_settings_debounced(self):
        """Schedule a debounced settings save"""
        self.settings_manager.save_settings_debounced(self)

    def on_out_nodes_loaded(self, out_nodes, node_settings):
        """Handle when out nodes are loaded by the hip file manager"""
        # Connect to the out_input's currentTextChanged signal if not already connected
        if not hasattr(self, 'out_node_signal_connected') or not self.out_node_signal_connected:
            # Safely check if signal is already connected without trying to disconnect
            # This avoids the disconnect warning when the signal isn't connected yet
            self.out_input.currentTextChanged.connect(self.on_out_node_changed)
            self.out_node_signal_connected = True

        # Check if we need to update our frame range and skip settings based on the
        # selected node (only if we're not overriding with custom range)
        if out_nodes:
            node_path = self.out_input.currentText()
            if self.frame_validation_manager:
                self.frame_validation_manager.update_from_node_settings(node_path, node_settings)
