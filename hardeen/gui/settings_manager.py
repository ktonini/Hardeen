import os
import datetime
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QMessageBox, QComboBox

from ..core.notifications import (
    NotificationManager,
    NotificationConfig,
    NotificationPriority,
    NotificationSettings
)
from ..utils.settings import Settings
from ..config import DEFAULT_FOLDER, DEFAULT_OUTNODE, SHUTDOWN_DELAYS
from ..gui.ui_components import get_ui_shutdown_delay

# Map UI display formats back to config values
def get_config_shutdown_delay(ui_delay_value):
    """Convert UI display format back to config shutdown delay value"""
    if ui_delay_value == "No delay":
        return "No delay"
    elif "m delay" in ui_delay_value:
        # Replace "Xm delay" with "X minutes"
        minutes = ui_delay_value.split("m")[0]
        return f"{minutes} minute{'s' if minutes != '1' else ''}"
    elif "h delay" in ui_delay_value:
        # Replace "Xh delay" with "X hour"
        hours = ui_delay_value.split("h")[0]
        return f"{hours} hour"
    return ui_delay_value

class SettingsManager(QObject):
    """
    Manages application settings, including loading, saving, and updating UI components.
    This centralizes all settings logic that was previously scattered in the main window.
    """

    # Define signals
    settings_changed = Signal()
    notification_settings_changed = Signal(object)  # Pass the NotificationSettings instance

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize settings
        self.settings = Settings()
        self.notification_settings = NotificationSettings()
        self.notification_manager = NotificationManager.from_environment()

        # Create debounce timer for saving settings
        self._save_settings_timer = QTimer(self)
        self._save_settings_timer.setSingleShot(True)
        self._save_settings_timer.setInterval(300)  # 300ms debounce
        self._save_settings_timer.timeout.connect(self._debounced_save_settings)

        # Flag to track when settings are being loaded
        self._loading_settings = False

    def load_settings(self, ui):
        """Load settings into UI components"""
        self._loading_settings = True

        # Load hip file path
        last_hip = self.settings.get('last_hipname', DEFAULT_FOLDER)
        if last_hip and os.path.exists(last_hip):
            # Block hip input signals to prevent triggering on_hip_file_changed
            old_state = ui.hip_input.blockSignals(True)
            ui.hip_input.setEditText(last_hip)
            ui.hip_input.blockSignals(old_state)

        # Load saved out nodes if available
        out_nodes = self.settings.get_list('outnames', [])
        if out_nodes:
            # Block out input signals
            old_state = ui.out_input.blockSignals(True)
            ui.out_input.addItems(out_nodes)
            last_out = self.settings.get('last_outname', DEFAULT_OUTNODE)
            ui.out_input.setEditText(last_out)
            ui.out_input.blockSignals(old_state)

        # Load frame range settings
        use_range = self.settings.get('use_frame_range', False)
        saved_start = self.settings.get('start_frame')
        saved_end = self.settings.get('end_frame')
        saved_step = self.settings.get('frame_step')

        # Set checkbox state first (this doesn't trigger toggle_frame_range due to blockSignals)
        old_range_state = ui.range_check.blockSignals(True)
        ui.range_check.setChecked(use_range)
        ui.range_check.blockSignals(old_range_state)

        # Set initial values for frame range
        old_start_state = ui.start_frame.blockSignals(True)
        old_end_state = ui.end_frame.blockSignals(True)
        old_step_state = ui.frame_step.blockSignals(True)

        if saved_start is not None and saved_end is not None:
            ui.start_frame.setText(str(saved_start))
            ui.end_frame.setText(str(saved_end))
        else:
            ui.start_frame.setText("1")
            ui.end_frame.setText("100")

        if saved_step is not None:
            ui.frame_step.setCurrentText(str(saved_step))
        else:
            ui.frame_step.setCurrentText("1")

        ui.start_frame.blockSignals(old_start_state)
        ui.end_frame.blockSignals(old_end_state)
        ui.frame_step.blockSignals(old_step_state)

        # Now enable/disable fields based on the frame range checkbox (skip validation to avoid overriding)
        ui.toggle_frame_range(skip_validation=True)

        # Load skip rendered frames setting
        old_skip_state = ui.skip_check.blockSignals(True)
        ui.skip_check.setChecked(self.settings.get('skip_rendered', False))
        ui.skip_check.blockSignals(old_skip_state)

        # Load notification settings
        old_notify_state = ui.notify_check.blockSignals(True)
        old_frames_state = ui.notify_frames.blockSignals(True)
        ui.notify_check.setChecked(self.settings.get('notifications_enabled', False))
        ui.notify_frames.setText(self.settings.get('notification_interval', "10"))
        ui.notify_check.blockSignals(old_notify_state)
        ui.notify_frames.blockSignals(old_frames_state)

        # Load shutdown settings
        old_shutdown_state = ui.shutdown_check.blockSignals(True)
        old_delay_state = ui.shutdown_delay.blockSignals(True)
        ui.shutdown_check.setChecked(self.settings.get('shutdown_after_render', False))

        # Get the stored delay value (in config format)
        delay_val = self.settings.get('shutdown_delay', SHUTDOWN_DELAYS[0])

        # Map the saved config value to its UI display equivalent
        ui_delay_value = get_ui_shutdown_delay(delay_val)

        # Find the index of this value in the dropdown
        idx = ui.shutdown_delay.findText(ui_delay_value)

        # Set the index if found, otherwise default to "No delay" (index 0)
        ui.shutdown_delay.setCurrentIndex(idx if idx != -1 else 0)

        # Enable/disable the dropdown based on checkbox state
        ui.shutdown_delay.setEnabled(ui.shutdown_check.isChecked())

        # Restore signal blocking state
        ui.shutdown_check.blockSignals(old_shutdown_state)
        ui.shutdown_delay.blockSignals(old_delay_state)

        # Update notification settings from the UI
        self.notification_settings.enabled = ui.notify_check.isChecked()
        self.notification_settings.interval = int(ui.notify_frames.text() or "10")
        self.notification_settings.api_token = self.settings.get('pushover_api_key', '')
        self.notification_settings.user_key = self.settings.get('pushover_user_key', '')

        # Update notification manager with saved settings
        self.update_notification_manager()

        self._loading_settings = False

    def save_settings(self, ui):
        """Save current UI state to settings"""
        # Save hip and out node selections
        self.settings.set('last_hipname', ui.hip_input.currentText())
        self.settings.set('outnames', self._get_unique_items(ui.out_input))
        self.settings.set('last_outname', ui.out_input.currentText())

        # Save frame range settings
        self.settings.set('use_frame_range', ui.range_check.isChecked())
        self.settings.set('start_frame', ui.start_frame.text())
        self.settings.set('end_frame', ui.end_frame.text())
        self.settings.set('frame_step', ui.frame_step.currentText())

        # Save skip rendered frames setting
        self.settings.set('skip_rendered', ui.skip_check.isChecked())

        # Save notification settings
        self.settings.set('notifications_enabled', ui.notify_check.isChecked())

        # Save notification interval with fallback to default
        interval_text = ui.notify_frames.text().strip()
        self.settings.set('notification_interval', interval_text if interval_text else "10")

        self.settings.set('pushover_api_key', self.settings.get('pushover_api_key', ''))
        self.settings.set('pushover_user_key', self.settings.get('pushover_user_key', ''))

        # Save shutdown settings
        self.settings.set('shutdown_after_render', ui.shutdown_check.isChecked())

        # Get the UI display value from the dropdown
        ui_delay_value = ui.shutdown_delay.currentText()

        # Convert to standardized config format
        config_delay_value = get_config_shutdown_delay(ui_delay_value)

        # Save using the standardized format
        self.settings.set('shutdown_delay', config_delay_value)

        # Emit settings changed signal
        self.settings_changed.emit()

    def _get_unique_items(self, combo):
        """Helper to get unique items from QComboBox"""
        return list(set(combo.itemText(i) for i in range(combo.count())))

    def update_notification_manager(self):
        """Update notification manager with current settings"""
        if self.notification_settings.enabled:
            try:
                config = NotificationConfig(
                    api_token=self.notification_settings.api_token,
                    user_key=self.notification_settings.user_key,
                    device=self.notification_settings.device,
                    priority=self.notification_settings.priority,
                    sound=self.notification_settings.sound
                )
                self.notification_manager = NotificationManager(config)
                return
            except Exception as e:
                print(f"Error setting up notification manager: {str(e)}")

        # Fallback to environment-based notification manager
        self.notification_manager = NotificationManager.from_environment()

    def on_notification_settings_changed(self, ui):
        """Handle changes to notification settings in the UI"""
        # Skip if we're loading settings
        if self._loading_settings:
            return

        # Update settings
        self.notification_settings.enabled = ui.notify_check.isChecked()

        # Safely handle notification interval
        try:
            interval_text = ui.notify_frames.text().strip()
            self.notification_settings.interval = int(interval_text) if interval_text else 10
        except (ValueError, TypeError):
            self.notification_settings.interval = 10
            # Reset the input with the default value if invalid
            ui.notify_frames.setText("10")

        self.notification_settings.api_token = self.settings.get('pushover_api_key', '')
        self.notification_settings.user_key = self.settings.get('pushover_user_key', '')

        # Update notification manager
        self.update_notification_manager()

        # Update display
        self.update_settings_display(ui)

        # Save settings
        self.save_settings_debounced(ui)

        # Emit notification settings changed signal with the settings instance
        self.notification_settings_changed.emit(self.notification_settings)

    def on_shutdown_settings_changed(self, ui):
        """Handle changes to shutdown settings in the UI"""
        # Skip if we're loading settings
        if self._loading_settings:
            return

        # Update settings
        self.settings.set('shutdown_after_render', ui.shutdown_check.isChecked())

        # Get the UI display value from the dropdown
        ui_delay_value = ui.shutdown_delay.currentText()

        # Convert to standardized config format
        config_delay_value = get_config_shutdown_delay(ui_delay_value)

        # Save using the standardized format
        self.settings.set('shutdown_delay', config_delay_value)

        # Enable/disable controls
        ui.shutdown_delay.setEnabled(ui.shutdown_check.isChecked())

        # Update display
        self.update_settings_display(ui)

        # Save settings
        self.save_settings_debounced(ui)

    def update_settings_display(self, ui):
        """Update the settings display in the UI"""
        # Enable/disable notification frames field based on checkbox
        ui.notify_frames.setEnabled(ui.notify_check.isChecked())

    def _debounced_save_settings(self):
        """Called when the debounce timer expires to actually save settings"""
        if hasattr(self, '_ui_to_save'):
            self.save_settings(self._ui_to_save)

    def save_settings_debounced(self, ui):
        """Schedule a debounced settings save"""
        # Skip if we're loading settings
        if self._loading_settings:
            return

        # Store UI reference for the callback
        self._ui_to_save = ui
        self._save_settings_timer.start()

    def show_settings_dialog(self, ui):
        """Show the settings dialog"""
        # Prepare current settings
        current_settings = {
            # Notification settings - include the enabled and interval settings from the main UI
            'notifications_enabled': self.settings.get('notifications_enabled', False),
            'notification_interval': self.settings.get('notification_interval', "10"),
            'pushover_api_key': self.settings.get('pushover_api_key', ''),
            'pushover_user_key': self.settings.get('pushover_user_key', ''),

            # Shutdown settings
            'shutdown_after_render': self.settings.get('shutdown_after_render', False),
            'shutdown_delay': self.settings.get('shutdown_delay', 'No delay')
        }

        # Create and show dialog
        from .settings_dialog import SettingsDialog

        # Get shutdown_manager from ui if available
        shutdown_manager = getattr(ui, 'shutdown_manager', None)

        # Create notification settings with current state from UI
        notification_settings = NotificationSettings(
            enabled=ui.notify_check.isChecked(),
            interval=int(ui.notify_frames.text() or "10"),
            api_token=self.settings.get('pushover_api_key', ''),
            user_key=self.settings.get('pushover_user_key', '')
        )

        # Create dialog with current notification settings
        dialog = SettingsDialog(ui, current_settings, shutdown_manager)
        dialog.notification_settings = notification_settings  # Set current notification settings

        # Connect the settings_changed signal to our apply_settings method
        dialog.settings_changed.connect(lambda settings_dict: self.apply_settings(ui, settings_dict))

        # Apply dialog styling
        dialog.setStyleSheet(ui.styleSheet())

        # Show dialog
        if dialog.exec():
            self.update_settings_display(ui)

        # Return the dialog instance
        return dialog

    def apply_settings(self, ui, settings_dict):
        """Apply settings from the dialog"""
        # Update our settings object
        for key, value in settings_dict.items():
            self.settings.set(key, value)

        # Preserve the main UI notification settings
        self.settings.set('notifications_enabled', ui.notify_check.isChecked())
        self.settings.set('notification_interval', ui.notify_frames.text().strip() or "10")

        # Update notification manager
        self.update_notification_manager()

        # Update the display
        self.update_settings_display(ui)

    def get_notification_settings(self):
        """Get the current notification settings"""
        return self.notification_settings

    def is_loading_settings(self):
        """Check if settings are currently being loaded"""
        return self._loading_settings

    def get(self, key, default=None):
        """Pass-through to settings.get method"""
        return self.settings.get(key, default)

    def get_list(self, key, default=None):
        """Pass-through to settings.get_list method"""
        return self.settings.get_list(key, default)

    def get_pushover_api_key(self):
        """Get the Pushover API key from settings"""
        return self.settings.get('pushover_api_key', '')

    def get_pushover_user_key(self):
        """Get the Pushover user key from settings"""
        return self.settings.get('pushover_user_key', '')

    def get_shutdown_delay_seconds(self):
        """Convert the selected delay option to seconds"""
        delay_text = self.get('shutdown_delay', 'No delay')

        if delay_text == "No delay":
            return 5  # Minimal delay for safety
        elif delay_text == "1 minute":
            return 60
        elif delay_text == "5 minutes":
            return 5 * 60
        elif delay_text == "10 minutes":
            return 10 * 60
        elif delay_text == "30 minutes":
            return 30 * 60
        elif delay_text == "1 hour":
            return 60 * 60
        else:
            return 5  # Default minimal delay
