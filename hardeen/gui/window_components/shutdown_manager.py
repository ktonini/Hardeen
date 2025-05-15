import os
import sys
import subprocess
from typing import Callable, Optional
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QMessageBox, QApplication
from ...config import SHUTDOWN_DELAYS


class ShutdownManager(QObject):
    """
    Manages shutdown functionality for the application.
    This includes:
    - Testing shutdown behavior
    - Formatting delay time
    - Converting delay text to seconds
    - Running countdown dialogs
    - Executing actual shutdown commands
    """

    # Signal for when shutdown is canceled
    shutdown_canceled = Signal()

    def __init__(self, parent=None, settings_manager=None, output_callback: Callable = None):
        """Initialize shutdown manager with necessary references"""
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.output_callback = output_callback
        self.parent = parent

    def test_shutdown(self):
        """Test the shutdown functionality with the selected delay"""
        delay_seconds = self.get_shutdown_delay_seconds()

        # Show confirmation message with options to simulate or actually shutdown
        msgBox = QMessageBox(self.parent)
        msgBox.setWindowTitle("Test Shutdown")
        msgBox.setText(f"How would you like to test the shutdown functionality?")
        msgBox.setInformativeText(f"Both options will use a {self.format_delay_time(delay_seconds)} delay.")
        simulateButton = msgBox.addButton("Simulate Only", QMessageBox.ActionRole)
        realShutdownButton = msgBox.addButton("Real Shutdown", QMessageBox.ActionRole)
        cancelButton = msgBox.addButton(QMessageBox.Cancel)
        msgBox.setDefaultButton(cancelButton)

        msgBox.exec()

        if msgBox.clickedButton() == simulateButton:
            # Run with test mode (simulation only)
            self.run_shutdown_countdown(delay_seconds, test_mode=True)
        elif msgBox.clickedButton() == realShutdownButton:
            # Show extra confirmation for real shutdown
            confirm = QMessageBox.warning(
                self.parent,
                "Confirm Real Shutdown",
                f"WARNING: This will actually shut down your computer after a {self.format_delay_time(delay_seconds)} delay.\n\n"
                f"Are you absolutely sure you want to proceed?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if confirm == QMessageBox.Yes:
                self.run_shutdown_countdown(delay_seconds, test_mode=False)

    def format_delay_time(self, seconds):
        """Format delay time in seconds to a human-readable string"""
        if seconds <= 5:
            return "minimal"
        elif seconds == 60:
            return "1 minute"
        elif seconds < 60 * 60:
            return f"{seconds // 60} minutes"
        else:
            return f"{seconds // 3600} hour"

    def get_shutdown_delay_seconds(self):
        """Convert the selected delay option to seconds"""
        if not self.settings_manager:
            return 5  # Default minimal delay for safety

        # Get stored delay value using standardized format
        delay_text = self.settings_manager.get('shutdown_delay', SHUTDOWN_DELAYS[0])

        # Map the delay text to seconds
        if delay_text == SHUTDOWN_DELAYS[0]:  # "No delay"
            return 5  # Minimal delay for safety
        elif delay_text == SHUTDOWN_DELAYS[1]:  # "1 minute"
            return 60
        elif delay_text == SHUTDOWN_DELAYS[2]:  # "5 minutes"
            return 5 * 60
        elif delay_text == SHUTDOWN_DELAYS[3]:  # "10 minutes"
            return 10 * 60
        elif delay_text == SHUTDOWN_DELAYS[4]:  # "30 minutes"
            return 30 * 60
        elif delay_text == SHUTDOWN_DELAYS[5]:  # "1 hour"
            return 60 * 60
        else:
            # For backward compatibility, fallback to parsing
            # Try to extract number of minutes/hours from the string
            try:
                if "minute" in delay_text:
                    minutes = int(delay_text.split()[0])
                    return minutes * 60
                elif "hour" in delay_text:
                    hours = int(delay_text.split()[0])
                    return hours * 3600
                elif "m delay" in delay_text:
                    minutes = int(delay_text.split("m")[0])
                    return minutes * 60
                elif "h delay" in delay_text:
                    hours = int(delay_text.split("h")[0])
                    return hours * 3600
            except (ValueError, IndexError):
                pass

            # If all else fails, default to minimal delay
            return 5

    def run_shutdown_countdown(self, delay_seconds, test_mode=False):
        """Run the shutdown countdown with a message box"""
        countdown_dialog = QMessageBox(self.parent)
        countdown_dialog.setWindowTitle("Shutdown Countdown")
        countdown_dialog.setStandardButtons(QMessageBox.Cancel)
        countdown_dialog.button(QMessageBox.Cancel).setText("Cancel Shutdown")

        # Create a timer for the countdown
        timer = QTimer(self.parent)
        remaining_time = delay_seconds

        def update_countdown():
            nonlocal remaining_time
            if remaining_time > 0:
                minutes = remaining_time // 60
                seconds = remaining_time % 60
                countdown_dialog.setText(f"Computer will {'simulate' if test_mode else ''} shutdown in "
                                         f"{minutes:02d}:{seconds:02d}")
                remaining_time -= 1
            else:
                timer.stop()
                countdown_dialog.accept()
                if test_mode:
                    QMessageBox.information(
                        self.parent,
                        "Test Complete",
                        "Shutdown test completed successfully. In a real scenario, "
                        "the computer would have shut down now."
                    )
                else:
                    self.execute_shutdown()

        # Start the countdown
        timer.timeout.connect(update_countdown)
        timer.start(1000)  # Update every second

        # Initialize dialog text
        minutes = delay_seconds // 60
        seconds = delay_seconds % 60
        countdown_dialog.setText(f"Computer will {'simulate' if test_mode else ''} shutdown in "
                                 f"{minutes:02d}:{seconds:02d}")

        # Show the dialog
        if countdown_dialog.exec() == QMessageBox.Cancel:
            # User canceled
            timer.stop()
            self.shutdown_canceled.emit()
            if self.output_callback:
                self.output_callback(
                    "\nShutdown canceled by user\n",
                    color='#ff6b2b',
                    bold=True
                )

    def execute_shutdown(self):
        """Execute the actual shutdown command based on the OS"""
        try:
            if self.output_callback:
                self.output_callback(
                    "\nInitiating system shutdown...\n",
                    color='#ff4c00',
                    bold=True
                )

            if sys.platform == "win32":
                # Windows
                os.system("shutdown /s /t 1")
            elif sys.platform == "darwin":
                # macOS
                os.system("osascript -e 'tell app \"System Events\" to shut down'")
            else:
                # Linux - try different methods
                try:
                    # Try systemd first
                    result = os.system("systemctl poweroff")
                    if result != 0:
                        # Try dbus
                        from pydbus import SystemBus
                        bus = SystemBus()
                        proxy = bus.get('org.freedesktop.login1', '/org/freedesktop/login1')
                        proxy.PowerOff(False)
                except:
                    # Fall back to traditional method
                    os.system("shutdown -h now")
        except Exception as e:
            QMessageBox.critical(
                self.parent,
                "Shutdown Error",
                f"Failed to shut down the computer: {str(e)}"
            )
