from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import Signal, QTimer

class LoadingComboBox(QComboBox):
    """Custom ComboBox with loading state animation"""
    loading_state_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False  # Use private variable
        self.loading_dots = 0
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading_text)

    @property
    def loading(self):
        return self._loading

    def start_loading(self):
        """Start loading animation"""
        self._loading = True
        self.loading_dots = 0
        self.loading_timer.start(300)
        self.setEnabled(False)
        self.update_loading_text()
        self.loading_state_changed.emit(True)

    def stop_loading(self):
        """Stop loading animation"""
        self._loading = False
        self.loading_timer.stop()
        self.setEnabled(True)
        self.loading_state_changed.emit(False)

    def update_loading_text(self):
        """Update the loading animation dots"""
        self.loading_dots = (self.loading_dots + 1) % 4
        dots = "." * self.loading_dots
        self.setEditText(f"Loading{dots}")
