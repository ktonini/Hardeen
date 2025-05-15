import threading
from typing import List, Tuple, Callable, Optional, Any
from PySide6.QtCore import QObject, QTimer, Qt
from PySide6.QtWidgets import QTextEdit, QApplication
from PySide6.QtGui import QTextCursor, QTextCharFormat, QTextBlockFormat, QColor, QFont

class TextOutputManager(QObject):
    """
    Manages text output functionality for the application.
    This includes:
    - Thread-safe queuing of text updates
    - Processing text updates in the main thread
    - Formatting and displaying text in the UI
    - Managing scrolling behavior
    """

    def __init__(self, parent=None, summary_text_widget: Optional[QTextEdit] = None, raw_text_widget: Optional[QTextEdit] = None):
        """Initialize text output manager with necessary widgets and queues"""
        super().__init__(parent)

        self.summary_text = summary_text_widget
        self.raw_text = raw_text_widget

        # Create update queues and locks for thread safety
        self.summary_update_queue: List[Tuple[str, Optional[str], bool, bool]] = []
        self.summary_update_lock = threading.Lock()
        self.raw_update_queue: List[str] = []
        self.raw_update_lock = threading.Lock()

        # Create update timers in the main thread
        self.summary_update_timer = QTimer(self)
        self.raw_update_timer = QTimer(self)

        # Connect timer signals
        self.summary_update_timer.timeout.connect(self.process_summary_updates)
        self.raw_update_timer.timeout.connect(self.process_raw_updates)

        # Start timers
        self.start_timers()

    def set_text_widgets(self, summary_text_widget: QTextEdit, raw_text_widget: QTextEdit):
        """Set or update the text widget references"""
        self.summary_text = summary_text_widget
        self.raw_text = raw_text_widget

    def append_output_safe(self, text: str, color: Optional[str] = None, bold: bool = False, center: bool = False):
        """Queue summary text updates to be processed in the main thread"""
        with self.summary_update_lock:
            self.summary_update_queue.append((text, color, bold, center))

    def process_summary_updates(self):
        """Process queued summary text updates in the main thread"""
        # Safe to manipulate UI here since we're in the main thread via QTimer
        if not self.summary_text:
            return

        updates = []
        with self.summary_update_lock:
            if not self.summary_update_queue:
                return
            updates = self.summary_update_queue.copy()
            self.summary_update_queue.clear()

        # Check if scrollbar is at the bottom before adding text
        scrollbar = self.summary_text.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()

        # Clear any text selection and move cursor to end
        cursor = self.summary_text.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.summary_text.setTextCursor(cursor)

        for text, color, bold, center in updates:
            # Format and insert new text
            format = QTextCharFormat()

            if color:
                format.setForeground(QColor(color))
            if bold:
                format.setFontWeight(QFont.Weight.Bold)
            if center:
                cursor.insertBlock()
                blockFormat = QTextBlockFormat()
                blockFormat.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cursor.setBlockFormat(blockFormat)

            cursor.insertText(text, format)
            cursor.setBlockFormat(QTextBlockFormat())  # Reset block format to default (left-aligned)

        self.summary_text.setTextCursor(cursor)

        # Only scroll to bottom if we were already at the bottom
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def append_raw_output_safe(self, text: str):
        """Queue raw text updates to be processed in the main thread"""
        with self.raw_update_lock:
            self.raw_update_queue.append(text)

    def process_raw_updates(self):
        """Process queued raw text updates in the main thread"""
        # Safe to manipulate UI here since we're in the main thread via QTimer
        if not self.raw_text:
            return

        updates = []
        with self.raw_update_lock:
            if not self.raw_update_queue:
                return
            updates = self.raw_update_queue.copy()
            self.raw_update_queue.clear()

        # Check if scrollbar is at the bottom before adding text
        scrollbar = self.raw_text.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()

        # Clear any text selection and move cursor to end
        cursor = self.raw_text.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.raw_text.setTextCursor(cursor)

        for text in updates:
            cursor.insertText(text + '\n')  # Add newline after each line

        self.raw_text.setTextCursor(cursor)

        # Only scroll to bottom if we were already at the bottom
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def start_timers(self):
        """Start the update timers"""
        self.summary_update_timer.start(100)
        self.raw_update_timer.start(100)

    def stop_timers(self):
        """Safely stop the update timers"""
        self._stop_timer_safe(self.summary_update_timer)
        self._stop_timer_safe(self.raw_update_timer)

    def _stop_timer_safe(self, timer: QTimer):
        """Thread-safe way to stop a timer"""
        if QApplication.instance().thread() == threading.current_thread():
            # We're in the main thread, so we can stop directly
            timer.stop()
        else:
            # We're in a background thread, use invokeMethod
            from PySide6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(timer, "stop", Qt.ConnectionType.QueuedConnection)

    def process_remaining_and_clear(self):
        """Process any remaining updates and clear the queues"""
        # Stop timers to prevent new updates during processing
        self.stop_timers()

        # Process any remaining text updates
        self.process_summary_updates()
        self.process_raw_updates()

        # Clear text update queues
        with self.summary_update_lock:
            self.summary_update_queue.clear()
        with self.raw_update_lock:
            self.raw_update_queue.clear()
