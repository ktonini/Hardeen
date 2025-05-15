from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QComboBox, QLineEdit, QCheckBox


class FrameValidationManager(QObject):
    """
    Manages frame range validation and toggling for the application.
    This includes:
    - Validating start frame, end frame, and frame step
    - Enabling/disabling frame range inputs based on checkbox state
    - Resetting to node values when frame range overrides are disabled
    - Handling skip rendered frames checkbox
    """

    def __init__(self, parent=None, start_frame=None, end_frame=None,
                 frame_step=None, range_check=None, skip_check=None,
                 out_input=None, settings_manager=None, hip_file_manager=None):
        """Initialize frame validation manager with the necessary widgets and managers"""
        super().__init__(parent)

        # Store widget references
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.frame_step = frame_step
        self.range_check = range_check
        self.skip_check = skip_check
        self.out_input = out_input

        # Store manager references
        self.settings_manager = settings_manager
        self.hip_file_manager = hip_file_manager

        # Connect signals if widgets are provided
        self.connect_signals()

    def set_widgets(self, start_frame, end_frame, frame_step, range_check, skip_check, out_input):
        """Set or update widget references and reconnect signals"""
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.frame_step = frame_step
        self.range_check = range_check
        self.skip_check = skip_check
        self.out_input = out_input

        # Reconnect signals with the new widgets
        self.connect_signals()

    def connect_signals(self):
        """Connect event handlers to widget signals"""
        if self.start_frame:
            self.start_frame.editingFinished.connect(self.validate_start_frame)
            self.start_frame.textEdited.connect(self.on_frame_range_edited)

        if self.end_frame:
            self.end_frame.editingFinished.connect(self.validate_end_frame)
            self.end_frame.textEdited.connect(self.on_frame_range_edited)

        if self.frame_step:
            self.frame_step.editTextChanged.connect(self.validate_frame_step)
            if hasattr(self.frame_step, 'lineEdit'):
                self.frame_step.lineEdit().textEdited.connect(self.on_frame_range_edited)

        if self.range_check:
            self.range_check.stateChanged.connect(self.toggle_frame_range)

        if self.skip_check:
            self.skip_check.stateChanged.connect(self.on_skip_check_changed)

    def toggle_frame_range(self, skip_validation=False):
        """Enable/disable frame range inputs based on checkbox state"""
        if not all([self.start_frame, self.end_frame, self.frame_step, self.range_check]):
            return

        enabled = self.range_check.isChecked()
        self.start_frame.setEnabled(enabled)
        self.end_frame.setEnabled(enabled)
        self.frame_step.setEnabled(enabled)

        # If we're disabling custom frame range, update with node settings
        if not enabled and not skip_validation and self.hip_file_manager:
            node_path = self.out_input.currentText()
            node_settings = self.hip_file_manager.get_node_settings()
            if node_path in node_settings:
                settings = node_settings[node_path]
                # Block signals to prevent triggering validation
                old_start_state = self.start_frame.blockSignals(True)
                old_end_state = self.end_frame.blockSignals(True)
                old_step_state = self.frame_step.blockSignals(True)

                self.start_frame.setText(str(settings['f1']))
                self.end_frame.setText(str(settings['f2']))
                self.frame_step.setCurrentText("1")

                self.start_frame.blockSignals(old_start_state)
                self.end_frame.blockSignals(old_end_state)
                self.frame_step.blockSignals(old_step_state)
        # If enabling custom frame range, keep current values - user will set them

        # Save frame range settings
        if not skip_validation and self.settings_manager:
            self.settings_manager.save_settings_debounced(self.parent())

    def validate_start_frame(self):
        """Validate the start frame"""
        if not self.start_frame or not self.settings_manager:
            return

        # Skip validation during loading
        parent = self.parent()
        if parent and hasattr(parent, '_loading_settings') and parent._loading_settings:
            return

        text = self.start_frame.text().strip()

        # If empty, try to use out node settings (only if override is disabled)
        if not text:
            if self.range_check and not self.range_check.isChecked() and self.hip_file_manager:
                node_path = self.out_input.currentText()
                node_settings = self.hip_file_manager.get_node_settings()
                if node_path in node_settings:
                    self.start_frame.setText(str(node_settings[node_path]['f1']))
                    self.settings_manager.save_settings_debounced(self.parent())
                    return
            # Default fallback
            self.start_frame.setText("1")
            self.settings_manager.save_settings_debounced(self.parent())
            return

        # If not a valid number, reset to default or node value
        if not text.isdigit():
            if self.range_check and not self.range_check.isChecked() and self.hip_file_manager:
                node_path = self.out_input.currentText()
                node_settings = self.hip_file_manager.get_node_settings()
                if node_path in node_settings:
                    self.start_frame.setText(str(node_settings[node_path]['f1']))
                    self.settings_manager.save_settings_debounced(self.parent())
                    return
            # Default fallback
            self.start_frame.setText("1")
            self.settings_manager.save_settings_debounced(self.parent())
            return

        # Ensure value is at least 1
        value = int(text)
        if value < 1:
            self.start_frame.setText("1")
            self.settings_manager.save_settings_debounced(self.parent())
            return

        # Save settings if valid and changed
        self.settings_manager.save_settings_debounced(self.parent())

    def validate_end_frame(self):
        """Validate the end frame"""
        if not self.end_frame or not self.settings_manager:
            return

        # Skip validation during loading
        parent = self.parent()
        if parent and hasattr(parent, '_loading_settings') and parent._loading_settings:
            return

        text = self.end_frame.text().strip()

        # If empty, try to use out node settings (only if override is disabled)
        if not text:
            if self.range_check and not self.range_check.isChecked() and self.hip_file_manager:
                node_path = self.out_input.currentText()
                node_settings = self.hip_file_manager.get_node_settings()
                if node_path in node_settings:
                    self.end_frame.setText(str(node_settings[node_path]['f2']))
                    self.settings_manager.save_settings_debounced(self.parent())
                    return
            # Default fallback
            self.end_frame.setText("100")
            self.settings_manager.save_settings_debounced(self.parent())
            return

        # If not a valid number, reset to default or node value
        if not text.isdigit():
            if self.range_check and not self.range_check.isChecked() and self.hip_file_manager:
                node_path = self.out_input.currentText()
                node_settings = self.hip_file_manager.get_node_settings()
                if node_path in node_settings:
                    self.end_frame.setText(str(node_settings[node_path]['f2']))
                    self.settings_manager.save_settings_debounced(self.parent())
                    return
            # Default fallback
            self.end_frame.setText("100")
            self.settings_manager.save_settings_debounced(self.parent())
            return

        # Ensure value is at least 1
        value = int(text)
        if value < 1:
            self.end_frame.setText("1")
            self.settings_manager.save_settings_debounced(self.parent())
            return

        # Save settings if valid and changed
        self.settings_manager.save_settings_debounced(self.parent())

    def validate_frame_step(self):
        """Validate the frame step"""
        if not self.frame_step or not self.settings_manager:
            return

        # Skip validation during loading
        parent = self.parent()
        if parent and hasattr(parent, '_loading_settings') and parent._loading_settings:
            return

        text = self.frame_step.currentText().strip()

        # If empty, use default
        if not text:
            self.frame_step.setCurrentText("1")
            self.settings_manager.save_settings_debounced(self.parent())
            return

        # If not a valid number, reset to default
        if not text.isdigit():
            self.frame_step.setCurrentText("1")
            self.settings_manager.save_settings_debounced(self.parent())
            return

        # Only enforce that value is at least 1
        # Allow arbitrary positive integers, not just 1-10
        value = int(text)
        if value < 1:
            self.frame_step.setCurrentText("1")
            self.settings_manager.save_settings_debounced(self.parent())
            return

        # Save settings if valid and changed
        self.settings_manager.save_settings_debounced(self.parent())

    def on_skip_check_changed(self, state):
        """Handle skip rendered frames checkbox state changes"""
        if self.settings_manager:
            self.settings_manager.save_settings_debounced(self.parent())

    def on_frame_range_edited(self, text):
        """Handle changes to frame range fields"""
        if self.settings_manager:
            self.settings_manager.save_settings_debounced(self.parent())

    def update_from_node_settings(self, node_path, node_settings):
        """Update frame range from node settings (called from main window)"""
        if not all([self.start_frame, self.end_frame, self.frame_step, self.range_check, self.skip_check]):
            return

        if node_path in node_settings:
            settings = node_settings[node_path]

            # Only update frame range if checkbox is unchecked (not overriding)
            if not self.range_check.isChecked():
                # Use out node values
                self.start_frame.setText(str(settings['f1']))
                self.end_frame.setText(str(settings['f2']))
                self.frame_step.setCurrentText("1")

            # Only update skip rendered setting if there's no saved setting
            if self.settings_manager and not self.settings_manager.get('skip_rendered', None):
                self.skip_check.setChecked(bool(settings['skip_rendered']))
