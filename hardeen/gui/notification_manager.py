import os
from typing import Optional, Dict, Any, Callable
import datetime
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox

from ..core.notifications import (
    NotificationManager,
    NotificationConfig,
    NotificationPriority,
    NotificationSettings
)
from ..utils.time_utils import format_time

class NotificationUIManager(QObject):
    """
    Manages the UI integration with the notification system.
    This class is responsible for:
    - Sending notifications in response to application events
    - Handling UI interactions related to notifications
    - Managing notification settings and configuration

    It works with the core NotificationManager to actually send notifications.
    """

    # Define signals
    notification_sent = Signal(bool, str)  # Success flag and message

    def __init__(self, settings_manager, parent=None):
        """Initialize the notification UI manager with a reference to the settings manager"""
        super().__init__(parent)
        self.settings_manager = settings_manager

    @property
    def notification_manager(self):
        """Get the notification manager from the settings manager"""
        return self.settings_manager.notification_manager

    @property
    def notification_settings(self):
        """Get the notification settings from the settings manager"""
        return self.settings_manager.notification_settings

    def send_notification(self, title: str, message: str, image_path: Optional[str] = None,
                         output_callback: Optional[Callable] = None):
        """
        Send a notification with the given title and message.

        Args:
            title: The notification title
            message: The notification message
            image_path: Optional path to an image to attach
            output_callback: Optional callback to send output to the UI
        """
        if not self.notification_manager:
            print("Notification manager not available")
            if output_callback:
                output_callback(
                    "\nNotification failed: Notification manager not available\n",
                    color='#ff6666',
                    bold=True
                )
            print(f"Notification settings: enabled={self.notification_settings.enabled}, "
                  f"api_token={bool(self.notification_settings.api_token)}, "
                  f"user_key={bool(self.notification_settings.user_key)}")
            self.notification_sent.emit(False, "Notification manager not available")
            return

        try:
            result = self.notification_manager.send_notification(
                title=title,
                message=message,
                image_path=image_path
            )

            if result.get("status") != 1:
                error_msg = result.get("error", "Unknown error")
                print(f"Failed to send notification: {error_msg}")
                if output_callback:
                    output_callback(
                        f"\nNotification failed: {error_msg}\n",
                        color='#ff6666',
                        bold=True
                    )
                self.notification_sent.emit(False, error_msg)
            else:
                # Success - only log to console but don't output to UI
                print("Notification sent successfully")
                # Signal that notification was sent successfully
                self.notification_sent.emit(True, "Notification sent successfully")
        except Exception as e:
            print(f"Error sending notification: {str(e)}")
            if output_callback:
                output_callback(
                    f"\nError sending notification: {str(e)}\n",
                    color='#ff6666',
                    bold=True
                )
            self.notification_sent.emit(False, str(e))

    def send_push_notification(self, message: str, image_path: Optional[str] = None,
                              output_callback: Optional[Callable] = None):
        """
        Send a push notification with just a message (no title).
        This is a convenience method that calls send_notification with standard title.

        Args:
            message: The notification message
            image_path: Optional path to an image to attach
            output_callback: Optional callback to send output to the UI
        """
        # Use app name or a generic title
        title = "Hardeen Render Manager"
        self.send_notification(title, message, image_path, output_callback)

    def send_render_started_notification(self, job_name: str, start_frame: int, end_frame: int,
                                        step: int, total_frames: int, output_callback: Optional[Callable] = None):
        """Send a notification when a render starts"""
        start_message = (
            f"🚀 Render Started: {job_name}\n"
            f"Frames: {start_frame}-{end_frame}{', every ' + str(step) + ' frames' if step > 1 else ''}\n"
            f"Total frames: {total_frames}"
        )
        self.send_push_notification(start_message, None, output_callback)

    def send_render_completed_notification(self, job_name: str, total_frames: int, elapsed_time: float,
                                          output_callback: Optional[Callable] = None):
        """Send a notification when a render completes"""
        elapsed_str = format_time(elapsed_time)
        completion_message = (
            f"✅ Render Complete: {job_name}\n"
            f"Total frames: {total_frames}\n"
            f"Total time: {elapsed_str}"
        )
        self.send_push_notification(completion_message, None, output_callback)

    def send_render_interrupted_notification(self, job_name: str, current_frame: int, total_frames: int,
                                           elapsed_time: float, image_path: Optional[str] = None,
                                           output_callback: Optional[Callable] = None):
        """Send a notification when a render is interrupted"""
        elapsed_str = format_time(elapsed_time)
        cancel_message = (
            f"⚠️ Render Interrupted: {job_name}\n"
            f"Will stop after frame: {current_frame}/{total_frames}\n"
            f"Total Time: {elapsed_str}"
        )
        self.send_push_notification(cancel_message, image_path, output_callback)

    def send_render_killed_notification(self, job_name: str, current_frame: int, total_frames: int,
                                       elapsed_time: float, image_path: Optional[str] = None,
                                       output_callback: Optional[Callable] = None):
        """Send a notification when a render is forcibly killed"""
        elapsed_str = format_time(elapsed_time)
        kill_message = (
            f"🛑 Render Force Killed: {job_name}\n"
            f"Stopped at: {current_frame}/{total_frames}\n"
            f"Total Time: {elapsed_str}"
        )
        self.send_push_notification(kill_message, image_path, output_callback)

    def send_frame_completed_notification(self, job_name: str, frame_index: int, total_frames: int,
                                         render_time: float, image_path: Optional[str] = None,
                                         output_callback: Optional[Callable] = None):
        """Send a notification when a frame completes"""
        time_str = format_time(render_time)
        frame_message = (
            f"🎬 Frame {frame_index}/{total_frames} completed\n"
            f"Render time: {time_str}\n"
            f"Job: {job_name}"
        )
        self.send_push_notification(frame_message, image_path, output_callback)

    def send_shutdown_notification(self, job_name: str, delay_text: str,
                                  output_callback: Optional[Callable] = None):
        """Send a notification about an impending shutdown"""
        shutdown_message = (
            f"⚠️ Render complete: {job_name}\n"
            f"The computer will shut down in {delay_text} unless canceled."
        )
        self.send_push_notification(shutdown_message, None, output_callback)

    def test_notification(self, ui_parent, output_callback=None):
        """Send a test notification through Pushover"""
        # Update notification manager to ensure it has the latest settings
        self.settings_manager.update_notification_manager()

        # Check if notification manager is available and properly configured
        if not self.notification_manager:
            QMessageBox.warning(ui_parent, "Notification Error", "Notification system is not available")
            return

        # Check if we have a valid configuration
        if not self.notification_settings.api_token or not self.notification_settings.user_key:
            QMessageBox.warning(
                ui_parent,
                "Notification Error",
                "Please enter both API key and user key to send notifications."
            )
            return

        try:
            # Show a "sending" message if callback provided
            if output_callback:
                output_callback(
                    "\nSending test notification...",
                    color='#4c9bff',
                    bold=True
                )

            # Send test notification
            result = self.notification_manager.send_push_notification(
                title="Hardeen Test Notification",
                message="This is a test notification from Hardeen.\n"
                        "If you can see this, your Pushover integration is working correctly!"
            )

            # Check result
            if result and result.get("status") == 1:
                # Don't output success message to the UI, just log it
                print("Test notification sent successfully!")

                QMessageBox.information(
                    ui_parent,
                    "Notification Sent",
                    "Test notification was sent successfully!\n\n"
                    "You should receive it on your Pushover-enabled devices momentarily."
                )
            else:
                error_msg = result.get("error", "Unknown error") if result else "No response from Pushover API"
                if output_callback:
                    output_callback(
                        f"\nFailed to send test notification: {error_msg}",
                        color='#ff6666',
                        bold=True
                    )

                QMessageBox.warning(
                    ui_parent,
                    "Notification Error",
                    f"Failed to send test notification: {error_msg}\n\n"
                    "Please check your API key and user key."
                )

        except Exception as e:
            if output_callback:
                output_callback(
                    f"\nError sending test notification: {str(e)}",
                    color='#ff6666',
                    bold=True
                )

            QMessageBox.warning(
                ui_parent,
                "Notification Error",
                f"An error occurred while sending the notification: {str(e)}"
            )
