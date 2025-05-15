import os
import datetime
from typing import Optional, Dict, Any, Callable
from PySide6.QtCore import QObject, Signal, QTimer, QDateTime
from PySide6.QtWidgets import QMessageBox, QPushButton, QLabel
from PySide6.QtCore import Qt

from ...core.render_manager import RenderManager
from ...utils.time_utils import format_time


class RenderControlManager(QObject):
    """
    Manager class that handles all render control functionality.
    Manages the start, stop, interrupt, and completion of renders.
    """

    # Define signals
    render_started = Signal()
    render_interrupted = Signal()
    render_killed = Signal()

    def __init__(
        self,
        parent,
        render_manager: RenderManager,
        render_status_manager,
        notification_ui_manager,
        settings_manager,
        text_output_manager,
        shutdown_manager,
        ui_components: Dict[str, Any]
    ):
        """Initialize the render control manager"""
        super().__init__(parent)

        # Store managers
        self.render_manager = render_manager
        self.render_status = render_status_manager
        self.notification_ui_manager = notification_ui_manager
        self.settings_manager = settings_manager
        self.text_output_manager = text_output_manager
        self.shutdown_manager = shutdown_manager

        # Store UI components needed for render control
        self.ui = ui_components

        # Connect signals from the render status manager to UI update methods in parent
        self.connect_signals()

    def connect_signals(self):
        """Connect render status signals to parent methods"""
        self.shutdown_manager.shutdown_canceled.connect(self.on_shutdown_canceled)

    def handle_render_button(self):
        """Unified handler for Render/Interrupt/Kill button."""
        if not self.render_manager.is_rendering():
            # Start rendering
            self.start_render()
        elif not self.render_manager.canceling:
            # First interrupt (graceful)
            self.interrupt_render()
        else:
            # Force kill
            self.kill_render()

    def start_render(self):
        """Start the render process using the render manager"""
        # Update UI
        self.ui['render_btn'].hide()
        self.ui['cancel_btn'].show()
        self.ui['cancel_btn'].setText('Interrupt')

        # Initialize the render status manager
        self.render_status.start_render()

        # Disable open folder button until we have an output
        self.ui['open_folder_btn'].setEnabled(False)

        # Clear previous image previews
        self.ui['image_preview'].update_preview([])

        # Clear the frame progress widget
        self.ui['progress_frame'].clear()

        # Calculate total frames
        if self.ui['range_check'].isChecked():
            start = int(self.ui['start_frame'].text())
            end = int(self.ui['end_frame'].text())
            step = int(self.ui['frame_step'].currentText())
            total_frames = len(range(start, end + 1, step))
            frame_range = list(range(start, end + 1, step))
            print(f"DEBUG: Setting frame range: {frame_range}")
            # Properly initialize the frame progress widget with the exact frames to render
            self.ui['progress_frame'].set_total_frames(total_frames, frame_range)
            # Set total frames in render status manager
            self.render_status.set_total_frames(total_frames, frame_range)
        else:
            # If no range specified, get frames from ROP if available or default to single frame
            try:
                node_path = self.ui['out_input'].currentText()
                node_settings = self.ui['hip_file_manager'].get_node_settings() if self.ui['hip_file_manager'] else {}

                if node_path in node_settings:
                    settings = node_settings[node_path]
                    f1 = settings['f1']
                    f2 = settings['f2']
                    total_frames = f2 - f1 + 1
                    frame_range = list(range(f1, f2 + 1))
                    print(f"DEBUG: Setting frames from ROP: {frame_range}")
                    self.ui['progress_frame'].set_total_frames(total_frames, frame_range)
                    # Set total frames in render status manager
                    self.render_status.set_total_frames(total_frames, frame_range)
                else:
                    # Default to single frame
                    total_frames = 1
                    self.ui['progress_frame'].set_total_frames(total_frames)
                    # Set total frames in render status manager
                    self.render_status.set_total_frames(total_frames)
            except Exception as e:
                print(f"Error determining frame range: {e}")
                total_frames = 1
                self.ui['progress_frame'].set_total_frames(total_frames)
                # Set total frames in render status manager
                self.render_status.set_total_frames(total_frames)

        # Ensure the widget is visible and updated
        self.ui['progress_frame'].show()
        self.ui['progress_frame'].update()

        # Send start notification if notifications are enabled
        if self.ui['notify_check'].isChecked():
            job_name = os.path.splitext(os.path.basename(self.ui['hip_input'].currentText()))[0]
            start_frame = int(self.ui['start_frame'].text())
            end_frame = int(self.ui['end_frame'].text())
            step = int(self.ui['frame_step'].currentText())

            # Use the notification UI manager to send the notification
            self.notification_ui_manager.send_render_started_notification(
                job_name=job_name,
                start_frame=start_frame,
                end_frame=end_frame,
                step=step,
                total_frames=total_frames,
                output_callback=self.ui['append_output_safe']
            )

        # Start render using the render manager
        self.render_manager.start_render(
            hip_path=self.ui['hip_input'].currentText(),
            out_path=self.ui['out_input'].currentText(),
            start_frame=int(self.ui['start_frame'].text()),
            end_frame=int(self.ui['end_frame'].text()),
            use_range=self.ui['range_check'].isChecked(),
            use_skip=self.ui['skip_check'].isChecked(),
            frame_step=int(self.ui['frame_step'].currentText())
        )

        # Emit signal
        self.render_started.emit()

    def interrupt_render(self):
        """Cancel the render process using the render manager"""
        if not self.render_manager.canceling:
            # First interrupt - graceful stop

            # Update UI in the main thread
            self.ui['cancel_btn'].setText('Kill')

            # Then tell the render manager to interrupt
            self.render_manager.interrupt_render()

            # Send cancellation notification
            if self.ui['notify_check'].isChecked():
                job_name = os.path.splitext(os.path.basename(self.ui['hip_input'].currentText()))[0]

                # Get current status from render status manager
                status = self.render_status.get_status_summary()
                current_frame = status['current_frame']
                total_frames = status['total_frames']
                elapsed = status['elapsed_time']

                # Use the last rendered image for the notification if it exists
                image_path = status['rendered_image_path']
                if image_path:
                    print(f"Including latest image in interrupt notification: {image_path}")

                # Use the notification UI manager to send the notification
                self.notification_ui_manager.send_render_interrupted_notification(
                    job_name=job_name,
                    current_frame=current_frame,
                    total_frames=total_frames,
                    elapsed_time=elapsed,
                    image_path=image_path,
                    output_callback=self.ui['append_output_safe']
                )

            # Emit signal
            self.render_interrupted.emit()
        else:
            # Force kill
            self.kill_render()

    def kill_render(self):
        """Force kill the render process"""
        self.render_manager.kill_render()

        # Send kill notification
        if self.ui['notify_check'].isChecked():
            job_name = os.path.splitext(os.path.basename(self.ui['hip_input'].currentText()))[0]

            # Get current status from render status manager
            status = self.render_status.get_status_summary()
            current_frame = status['current_frame']
            total_frames = status['total_frames']
            elapsed = status['elapsed_time']

            # Use the last rendered image for the notification if it exists
            image_path = status['rendered_image_path']
            if image_path:
                print(f"Including latest image in kill notification: {image_path}")

            # Use the notification UI manager to send the notification
            self.notification_ui_manager.send_render_killed_notification(
                job_name=job_name,
                current_frame=current_frame,
                total_frames=total_frames,
                elapsed_time=elapsed,
                image_path=image_path,
                output_callback=self.ui['append_output_safe']
            )

        # Emit signal
        self.render_killed.emit()

    def render_finished(self):
        """Handle render completion (called in main thread through signal)"""
        # Process any remaining text updates via text output manager
        if self.text_output_manager:
            self.text_output_manager.stop_timers()
            self.text_output_manager.process_remaining_and_clear()

        # Get status from render status manager
        status = self.render_status.get_status_summary()
        elapsed = status['elapsed_time']
        elapsed_str = format_time(elapsed)
        current_frame = status['current_frame']
        total_frames = status['total_frames']

        if self.render_manager.canceling:
            # If we were canceling, show interrupted message
            if self.render_manager.killed:
                self.ui['append_output_safe'](
                    '\n Render killed and stopped. \n\n',
                    color='#ff7a7a',
                    bold=True,
                    center=True
                )
            else:
                self.ui['append_output_safe'](
                    '\n Render gracefully canceled. \n\n',
                    color='#ff7a7a',
                    bold=True,
                    center=True
                )
        else:
            # Show completion message
            self.ui['append_output_safe'](
                '\n RENDER COMPLETED \n\n',
                color='#22adf2',
                bold=True,
                center=True
            )

            # Completion notification
            if self.ui['notify_check'].isChecked():
                job_name = os.path.splitext(os.path.basename(self.ui['hip_input'].currentText()))[0]

                # Use the notification UI manager to send the notification
                self.notification_ui_manager.send_render_completed_notification(
                    job_name=job_name,
                    total_frames=total_frames,
                    elapsed_time=elapsed,
                    output_callback=self.ui['append_output_safe']
                )

        # Process any final updates that were just added
        if self.text_output_manager:
            self.text_output_manager.process_summary_updates()
            self.text_output_manager.process_raw_updates()

        # Reset UI state
        self.ui['render_btn'].show()
        self.ui['cancel_btn'].hide()
        self.ui['cancel_btn'].setText('Interrupt')

        # Get average from progress frame if available
        frame_times = getattr(self.ui['progress_frame'], 'frame_times', {})
        times = [t for t in frame_times.values() if t > 0]
        average = sum(times) / len(times) if times else 0.0

        # Keep the time labels with correct values (don't reset)
        # The remaining time should be 0 since the render is complete
        self.render_status.time_labels_signal.emit(
            elapsed,           # Keep actual elapsed time
            average,           # Keep actual average time
            elapsed,           # Est. Total is now the actual elapsed time
            0.0,               # Remaining time is 0 since we're done
            QDateTime(),       # Empty ETA since we're done
            False              # Don't show ETA
        )

        # IMPORTANT: Reset the render manager's process to None so new renders can start
        self.render_manager.process = None

        # Shutdown logic - only trigger if render completed normally (not interrupted)
        if self.ui['shutdown_check'].isChecked() and not self.render_manager.canceling:
            # Send pushover notification about pending shutdown
            if self.ui['notify_check'].isChecked():
                try:
                    job_name = os.path.splitext(os.path.basename(self.ui['hip_input'].currentText()))[0]
                    delay_text = self.ui['shutdown_delay'].currentText()

                    # Use the notification UI manager to send the notification
                    self.notification_ui_manager.send_shutdown_notification(
                        job_name=job_name,
                        delay_text=delay_text,
                        output_callback=self.ui['append_output_safe']
                    )
                except Exception as e:
                    print(f"Error sending notification: {e}")

            msg_box = QMessageBox(self.parent())
            msg_box.setWindowTitle("Shutdown Confirmation")
            msg_box.setText(f"Render is complete. The computer will shut down in {self.ui['shutdown_delay'].currentText()}.")
            msg_box.setInformativeText("Click 'Cancel Shutdown' to prevent the computer from shutting down.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Cancel)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Cancel)
            msg_box.button(QMessageBox.StandardButton.Cancel).setText("Cancel Shutdown")
            reply = msg_box.exec()
            if reply == QMessageBox.StandardButton.Cancel:
                # Restart timers and return without shutdown
                if self.text_output_manager:
                    self.text_output_manager.start_timers()
                return

            # Schedule shutdown after selected delay - use the shutdown manager
            delay_seconds = self.settings_manager.get_shutdown_delay_seconds()
            # Start shutdown countdown
            self.shutdown_manager.run_shutdown_countdown(delay_seconds, test_mode=False)

        # Restart text update timers in the main thread
        if self.text_output_manager:
            self.text_output_manager.start_timers()

    def on_shutdown_canceled(self):
        """Handle when a shutdown is canceled by the user"""
        # Make sure timers are restarted
        if self.text_output_manager:
            self.text_output_manager.start_timers()

    def update_status(self):
        """Update UI with current render status"""
        # Check if render is in progress
        if self.render_manager.is_rendering():
            # Update button states if needed
            if self.ui['render_btn'].isVisible():
                self.ui['render_btn'].hide()
                self.ui['cancel_btn'].show()

            # Update button text based on canceling state
            if self.render_manager.canceling and self.ui['cancel_btn'].text() != 'Kill':
                self.ui['cancel_btn'].setText('Kill')
        else:
            # Update button states if needed
            if self.ui['cancel_btn'].isVisible():
                self.ui['cancel_btn'].hide()
                self.ui['render_btn'].show()

    def handle_render_close(self, event):
        """Handle closing window when render is in progress"""
        # Process any remaining text updates via text output manager
        if self.text_output_manager:
            self.text_output_manager.process_remaining_and_clear()

        # If rendering is in progress, check if user wants to cancel
        if self.render_manager.is_rendering():
            reply = QMessageBox.question(
                self.parent(),
                "Confirm Exit",
                "A render is in progress. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.render_manager.kill_render()
                return True  # Accept the event
            else:
                return False  # Ignore the event

        return True  # Accept the event if no render in progress
