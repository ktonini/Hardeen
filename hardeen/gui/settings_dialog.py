import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QLineEdit, QPushButton, QCheckBox,
    QGroupBox, QFormLayout, QComboBox,
    QMessageBox, QWidget
)
from PySide6.QtCore import Qt, Signal, QPoint, QUrl
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPolygon, QDesktopServices

from ..core.notifications import (
    NotificationManager,
    NotificationConfig,
    NotificationPriority,
    NotificationSettings
)


class SettingsDialog(QDialog):
    """Settings dialog for Hardeen application"""

    # Signals
    settings_changed = Signal(dict)  # Emitted when settings are changed

    def __init__(self, parent=None, settings=None, shutdown_manager=None):
        super().__init__(parent)
        self.settings = settings or {}
        self.parent_window = parent
        self.notification_settings = NotificationSettings.from_dict(self.settings)
        self.shutdown_manager = shutdown_manager  # Store reference to shutdown manager

        self.setWindowTitle("Hardeen Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        # Initialize notification manager
        self.notification_manager = None

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Set up the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)  # Reduce dialog margins
        layout.setSpacing(0)  # Remove spacing between tab widget and dialog edges

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self.create_notifications_tab()
        self.create_shutdown_tab()

    def create_notifications_tab(self):
        """Create the notifications settings tab"""
        notifications_tab = QWidget()
        layout = QVBoxLayout(notifications_tab)
        layout.setContentsMargins(6, 6, 6, 6)  # Reduce tab margins
        layout.setSpacing(6)  # Tighter spacing between elements

        # Pushover settings group
        pushover_group = QGroupBox("Pushover Settings")
        pushover_layout = QVBoxLayout(pushover_group)
        pushover_layout.setContentsMargins(12, 12, 12, 12)  # Comfortable padding inside group
        pushover_layout.setSpacing(8)  # Tighter spacing between elements

        # API Key
        api_key_layout = QHBoxLayout()
        api_key_layout.setSpacing(6)  # Tighter spacing between label and input
        api_key_label = QLabel("API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your Pushover API key")
        api_key_layout.addWidget(api_key_label)
        api_key_layout.addWidget(self.api_key_input)

        # User Key
        user_key_layout = QHBoxLayout()
        user_key_layout.setSpacing(6)  # Tighter spacing between label and input
        user_key_label = QLabel("User Key:")
        self.user_key_input = QLineEdit()
        self.user_key_input.setPlaceholderText("Enter your Pushover user key")
        user_key_layout.addWidget(user_key_label)
        user_key_layout.addWidget(self.user_key_input)

        # Add layouts to pushover group
        pushover_layout.addLayout(api_key_layout)
        pushover_layout.addLayout(user_key_layout)

        # Test button
        self.test_notify_btn = QPushButton("Test Notification")
        self.test_notify_btn.clicked.connect(self.test_notification)
        self.test_notify_btn.setEnabled(False)  # Disabled by default
        pushover_layout.addWidget(self.test_notify_btn)

        # Help text with link to Pushover website
        help_text = QLabel("Pushover is a notification service that sends messages to your devices. <a href='https://pushover.net/'>Visit Pushover Website</a>")
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #888; font-style: italic;")
        help_text.setOpenExternalLinks(True)
        pushover_layout.addWidget(help_text)

        layout.addWidget(pushover_group)

        # Connect signals
        self.api_key_input.textChanged.connect(self.update_notification_controls)
        self.user_key_input.textChanged.connect(self.update_notification_controls)

        self.tab_widget.addTab(notifications_tab, "Notifications")

    def create_shutdown_tab(self):
        """Create the shutdown settings tab"""
        shutdown_tab = QWidget()
        layout = QVBoxLayout(shutdown_tab)
        layout.setContentsMargins(6, 6, 6, 6)  # Reduce tab margins
        layout.setSpacing(6)  # Tighter spacing between elements

        # Shutdown group
        shutdown_group = QGroupBox("Shutdown Options")
        shutdown_layout = QVBoxLayout(shutdown_group)
        shutdown_layout.setContentsMargins(12, 12, 12, 12)  # Comfortable padding inside group
        shutdown_layout.setSpacing(8)  # Tighter spacing between elements

        # Informational text about shutdown options
        info_label = QLabel("You can configure shutdown options in the main window. "
                          "Use this tab to test the shutdown functionality.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #d6d6d6;")
        shutdown_layout.addWidget(info_label)

        # Test shutdown button
        self.test_shutdown_btn = QPushButton(" Test Shutdown")
        self.test_shutdown_btn.setObjectName("testShutdownButton")

        # Use theme icon if available, otherwise create a simple warning icon
        warning_icon = QIcon.fromTheme("dialog-warning")
        if warning_icon.isNull():
            # Create a simple warning icon
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            # Fill triangle
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#ff6b2b")))
            painter.drawPolygon([QPoint(8, 2), QPoint(15, 14), QPoint(1, 14)])

            # Draw exclamation mark
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawLine(8, 5, 8, 10)
            painter.drawPoint(8, 12)
            painter.end()

            warning_icon = QIcon(pixmap)

        self.test_shutdown_btn.setIcon(warning_icon)
        self.test_shutdown_btn.clicked.connect(self.test_shutdown)
        shutdown_layout.addWidget(self.test_shutdown_btn)

        # Warning text
        warning_label = QLabel("Warning: The shutdown feature will turn off your computer. Make sure to save all work before using this feature.")
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #ff6b2b; font-weight: bold;")
        shutdown_layout.addWidget(warning_label)

        layout.addWidget(shutdown_group)

        self.tab_widget.addTab(shutdown_tab, "Shutdown")

    def update_notification_controls(self):
        """Enable/disable notification controls based on key presence"""
        api_key = self.api_key_input.text().strip()
        user_key = self.user_key_input.text().strip()
        can_test = bool(api_key) and bool(user_key)

        # Always use the enabled state from notification_settings
        is_enabled = self.notification_settings.enabled

        # Enable/disable notification controls based on notification settings enabled state
        self.api_key_input.setEnabled(is_enabled)
        self.user_key_input.setEnabled(is_enabled)

        # Test button needs both API key and user key to be enabled
        self.test_notify_btn.setEnabled(can_test and is_enabled)

        # Update tooltip for test button
        if can_test and is_enabled:
            self.test_notify_btn.setToolTip("Send a test notification to verify your Pushover settings")
        elif not is_enabled:
            self.test_notify_btn.setToolTip("Enable notifications in the main window to test")
        else:
            self.test_notify_btn.setToolTip("Enter both API and user keys to test notifications")

        # Update notification manager
        self.update_notification_manager()

    def update_notification_manager(self):
        """Update notification manager with current settings"""
        # Only create notification manager if enabled with valid keys
        api_key = self.api_key_input.text().strip()
        user_key = self.user_key_input.text().strip()

        if api_key and user_key:
            try:
                config = NotificationConfig(
                    api_token=api_key,
                    user_key=user_key,
                    priority=NotificationPriority.NORMAL
                )
                self.notification_manager = NotificationManager(config)
                return
            except Exception as e:
                print(f"Error setting up notification manager: {str(e)}")

        # Fallback to environment-based notification manager
        self.notification_manager = NotificationManager.from_environment()

    def test_notification(self):
        """Send a test notification through Pushover"""
        # Update notification settings - getting API key and user key from the dialog inputs
        self.notification_settings.api_token = self.api_key_input.text().strip()
        self.notification_settings.user_key = self.user_key_input.text().strip()

        # Create notification manager
        if self.notification_settings.api_token and self.notification_settings.user_key:
            config = NotificationConfig(
                api_token=self.notification_settings.api_token,
                user_key=self.notification_settings.user_key,
                priority=NotificationPriority.NORMAL
            )
            self.notification_manager = NotificationManager(config)
        else:
            QMessageBox.warning(
                self,
                "Notification Error",
                "Please enter both API key and user key to send notifications."
            )
            return

        try:
            # Send test notification
            result = self.notification_manager.send_notification(
                title="Hardeen Test Notification",
                message="This is a test notification from Hardeen.\n"
                        "If you can see this, your Pushover integration is working correctly!"
            )

            # Check result
            if result and result.get("status") == 1:
                QMessageBox.information(
                    self,
                    "Notification Sent",
                    "Test notification was sent successfully!\n\n"
                    "You should receive it on your Pushover-enabled devices momentarily."
                )
            else:
                error_msg = result.get("error", "Unknown error") if result else "No response from Pushover API"
                QMessageBox.warning(
                    self,
                    "Notification Error",
                    f"Failed to send test notification: {error_msg}\n\n"
                    "Please check your API key and user key."
                )

        except Exception as e:
            QMessageBox.warning(
                self,
                "Notification Error",
                f"An error occurred while sending the notification: {str(e)}"
            )

    def test_shutdown(self):
        """
        Handler for test shutdown button.
        If we have a shutdown manager reference, use it. Otherwise, display a message.
        """
        if self.shutdown_manager:
            self.shutdown_manager.test_shutdown()
        else:
            # Show a message to the user if no shutdown manager is available
            QMessageBox.information(
                self,
                "Shutdown Test",
                "Shutdown test function is not available."
            )

    def load_settings(self):
        """Load settings into the dialog"""
        # Notification settings (API keys only - other settings managed in main UI)
        self.api_key_input.setText(self.notification_settings.api_token)
        self.user_key_input.setText(self.notification_settings.user_key)

        # Update notification controls
        self.update_notification_controls()

    def closeEvent(self, event):
        """Handle dialog close event"""
        # Save current settings state
        settings_dict = self.notification_settings.to_dict()
        self.settings_changed.emit(settings_dict)
        event.accept()

    def save_settings(self):
        """Save settings from the dialog"""
        # Update notification settings (preserve enabled and interval from notification_settings)
        self.notification_settings.api_token = self.api_key_input.text().strip()
        self.notification_settings.user_key = self.user_key_input.text().strip()

        # Convert settings to dictionary
        settings_dict = self.notification_settings.to_dict()

        # Emit settings changed signal
        self.settings_changed.emit(settings_dict)
