import os
import threading
from typing import List, Tuple, Callable, Optional, Any, Dict
from PySide6.QtWidgets import QComboBox, QMessageBox, QFileDialog, QApplication
from PySide6.QtCore import QObject, QTimer, Signal

from ...core.houdini import HoudiniManager
from ...config import DEFAULT_FOLDER

class HipFileManager(QObject):
    """
    Manages Houdini HIP file operations for the application.
    This includes:
    - Loading available hip files from history
    - Parsing out nodes from hip files
    - Handling hip file selection changes
    - Managing file browsing
    """

    # Signals for notifying the main window of changes
    hip_file_changed = Signal(str)
    out_nodes_loaded = Signal(list, dict)  # list of out nodes, dictionary of node settings
    output_update = Signal(str, str, bool, bool)  # text, color, bold, center

    def __init__(self, parent=None, hip_input: Optional[QComboBox] = None,
                 out_input: Optional[QComboBox] = None,
                 settings_manager=None):
        """Initialize hip file manager with necessary widgets and managers"""
        super().__init__(parent)

        # Save widget references
        self.hip_input = hip_input
        self.out_input = out_input
        self.settings_manager = settings_manager

        # Create the Houdini manager for interfacing with Houdini
        self.houdini_manager = HoudiniManager()

        # Store node settings for later use
        self.node_settings = {}

        # Flag to track when settings are being loaded
        self._loading_settings = False

    def set_widgets(self, hip_input: QComboBox, out_input: QComboBox):
        """Set or update widget references"""
        self.hip_input = hip_input
        self.out_input = out_input

    def load_hip_files(self):
        """Load available hip files from Houdini history"""
        if not self.hip_input:
            return

        # Remember current selection
        current_selection = self.hip_input.currentText()

        # Block signals temporarily to prevent auto-refresh
        old_state = self.hip_input.blockSignals(True)

        # Clear and load new files
        self.hip_input.clear()
        history_file = self.houdini_manager.get_houdini_history_file()
        if history_file:
            hip_files = self.houdini_manager.parse_hip_files(history_file)
            self.hip_input.addItems(hip_files)

        # Restore previous selection if it exists in the new list
        if current_selection:
            index = self.hip_input.findText(current_selection)
            if index >= 0:
                self.hip_input.setCurrentIndex(index)

        # Restore signal handling
        self.hip_input.blockSignals(old_state)

        # If we're not in loading mode and have a valid selection, refresh out nodes
        if not self._loading_settings and self.hip_input.currentText():
            self.refresh_out_nodes()

    def browse_hip_file(self):
        """Open file dialog to select a hip file"""
        if not self.hip_input:
            return

        # Get parent for dialog
        parent = self.parent() if self.parent() else None

        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "Select Houdini File",
            str(DEFAULT_FOLDER),
            "Houdini Files (*.hip *.hipnc)"
        )

        if file_path:
            # Add to combo box if not already present
            index = self.hip_input.findText(file_path)
            if index == -1:
                self.hip_input.insertItem(0, file_path)
            self.hip_input.setCurrentText(file_path)

    def on_hip_file_changed(self, hip_file: str):
        """Handle hip file selection change"""
        if not hip_file:
            return

        # Skip processing completely during settings loading
        if self._loading_settings:
            return

        # Emit signal for logging
        self.output_update.emit(
            f"\nSelected HIP file:\n",
            '#7abfff',
            True,
            False
        )

        self.output_update.emit(f"  {hip_file}\n", '#d6d6d6', False, False)

        # Save the selected hip file if we have a settings manager
        if self.settings_manager:
            self.settings_manager.save_settings_debounced(self.parent())

        # Refresh out nodes from the selected hip file
        self.refresh_out_nodes()

        # Emit signal that hip file changed
        self.hip_file_changed.emit(hip_file)

    def refresh_out_nodes(self):
        """Refresh the list of out nodes from current hip file"""
        if not self.hip_input or not self.out_input:
            return

        # Store current text before clearing
        current_text = self.out_input.currentText()
        self.out_input.clear()

        # Get selected hip file
        hip_file = self.hip_input.currentText()
        if not hip_file:
            # No hip file selected
            self.output_update.emit(
                "\nNo HIP file selected. Please select a HIP file first.",
                '#ff6666',
                True,
                False
            )
            return

        if os.path.exists(hip_file):
            # Start loading animation if available
            if hasattr(self.out_input, 'start_loading'):
                self.out_input.start_loading()

            # Use QTimer to allow the UI to update before processing
            QTimer.singleShot(100, lambda: self._process_out_nodes(hip_file, current_text))
        else:
            # Show warning if hip file doesn't exist
            parent = self.parent() if self.parent() else None
            QMessageBox.warning(parent, "Error", "Selected HIP file does not exist")

            # Emit empty out nodes signal so the UI can update appropriately
            self.out_nodes_loaded.emit([], {})

    def _process_out_nodes(self, hip_file: str, current_text: str):
        """Process out nodes after showing loading state"""
        if not self.out_input:
            return

        try:
            # Get out nodes from hip file through houdini manager
            out_nodes, node_settings = self.houdini_manager.parse_out_nodes(hip_file)

            # Stop loading animation if available
            if hasattr(self.out_input, 'stop_loading'):
                self.out_input.stop_loading()

            if out_nodes:
                # Reverse the list so latest nodes appear first
                out_nodes.reverse()

                # Add nodes to combo box
                self.out_input.addItems(out_nodes)

                # Emit signal for logging - only if not during loading settings
                if not self._loading_settings:
                    self.output_update.emit(
                        f"\nFound {len(out_nodes)} out nodes:\n",
                        '#7abfff',
                        True,
                        False
                    )

                    for node in out_nodes:
                        self.output_update.emit(f"  {node}\n", '#d6d6d6', False, False)

            # Add saved paths from settings if available and we have a settings manager
            if self.settings_manager:
                saved_paths = self.settings_manager.get_list('outnames', [])
                if saved_paths:
                    for path in saved_paths:
                        if path not in out_nodes:
                            self.out_input.addItem(path)

            # Select the most recent out node (first in the list) or restore previous selection
            if out_nodes:
                first_node = out_nodes[0]
                self.out_input.setCurrentText(first_node)
            elif current_text:
                # If no new nodes found but we had a previous selection, restore it
                self.out_input.setEditText(current_text)

            # If no nodes were found, log that information - only if not during loading settings
            if not out_nodes and not self._loading_settings:
                self.output_update.emit(
                    "\nNo out nodes found in the selected HIP file",
                    '#ff6666',
                    True,
                    False
                )

            # Store node settings for later use
            self.node_settings = node_settings

            # Emit signal that out nodes have been loaded
            self.out_nodes_loaded.emit(out_nodes, node_settings)

        except Exception as e:
            # Handle any exceptions during parsing
            if hasattr(self.out_input, 'stop_loading'):
                self.out_input.stop_loading()

            # Only emit error if not during loading settings
            if not self._loading_settings:
                self.output_update.emit(
                    f"\nError parsing out nodes: {str(e)}\n",
                    '#ff0000',
                    True,
                    False
                )

            # Emit empty results on error
            self.out_nodes_loaded.emit([], {})

    def get_node_settings(self) -> Dict:
        """Get the current node settings dictionary"""
        return self.node_settings

    def set_loading_settings_state(self, state: bool):
        """Set the state of the loading settings flag"""
        self._loading_settings = state
