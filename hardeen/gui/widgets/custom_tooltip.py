from PySide6.QtWidgets import QLabel, QApplication
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QFont

class CustomToolTip(QLabel):
    # Singleton instance for app-wide use
    _instance = None

    @staticmethod
    def instance():
        """Get the singleton instance of CustomToolTip"""
        if CustomToolTip._instance is None:
            CustomToolTip._instance = CustomToolTip()
        return CustomToolTip._instance

    def __init__(self, parent=None):
        super().__init__(parent, Qt.ToolTip)
        self.setWindowFlags(Qt.ToolTip)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("""
            background-color: #232323;
            color: #fff;
            border: 1px solid #444;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 12px;
        """)
        self.setFont(QFont('Inter', 10))
        self.hide()

        # Timer for display delay
        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._show_after_delay)

        # Timer for hiding
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        # Store pending tooltip data
        self._pending_text = ""
        self._pending_pos = QPoint()
        self._pending_timeout = 3000

    def show_tooltip(self, text, global_pos, delay=700, timeout=3000):
        """
        Queue showing a tooltip with specified delay

        Args:
            text: Text to display in tooltip
            global_pos: Global screen position (QPoint)
            delay: Milliseconds to wait before showing (default: 700ms)
            timeout: Milliseconds to display tooltip (default: 3000ms)
        """
        # Cancel any pending operations
        self._delay_timer.stop()
        self._hide_timer.stop()

        if not text or not global_pos:
            self.hide()
            return

        # Store pending tooltip data
        self._pending_text = text
        self._pending_pos = global_pos
        self._pending_timeout = timeout

        # Start delay timer
        self._delay_timer.start(delay)

    def _show_after_delay(self):
        """Show the tooltip after the delay has elapsed"""
        self.setText(self._pending_text)
        self.adjustSize()

        # Center the tooltip on the position point
        pos = self._pending_pos
        pos.setX(pos.x() - self.width() // 2)  # Adjust x to center tooltip

        self.move(pos)
        self.show()
        self.raise_()

        # Start the hide timer
        self._hide_timer.start(self._pending_timeout)

    def hide_tooltip(self):
        """Cancel and hide the tooltip"""
        self._delay_timer.stop()
        self._hide_timer.stop()
        self.hide()

class TooltipHelper:
    """Utility class to easily add custom tooltips to any widget"""

    @staticmethod
    def install(widget, text, position='bottom-center', delay=700, timeout=3000):
        """
        Install a custom tooltip on a widget

        Args:
            widget: The widget to add tooltip to
            text: Tooltip text
            position: Where to position tooltip ('bottom-center', 'bottom-left', 'top-center', 'right', 'left')
            delay: Milliseconds to wait before showing
            timeout: Milliseconds to display tooltip
        """
        # Store original event handlers
        orig_enter = widget.enterEvent
        orig_leave = widget.leaveEvent

        # Set tooltip text as an attribute
        widget._tooltip_text = text
        widget._tooltip_position = position
        widget._tooltip_delay = delay
        widget._tooltip_timeout = timeout

        # Custom enter event handler
        def custom_enter_event(event):
            # Call original handler
            if orig_enter:
                orig_enter(event)

            # Show tooltip
            tooltip = CustomToolTip.instance()

            # Calculate position
            if position == 'bottom-center':
                # Calculate center point of bottom edge
                pos = widget.mapToGlobal(widget.rect().bottomLeft())
                # Add half widget width to get to the center
                center_x = pos.x() + widget.width() // 2
                # Set the position (will be adjusted by tooltip itself)
                pos.setX(center_x)
                pos.setY(pos.y() + 5)  # Add some padding
            elif position == 'bottom-left':
                pos = widget.mapToGlobal(widget.rect().bottomLeft())
                pos.setY(pos.y() + 5)  # Add some padding
            elif position == 'top-center':
                pos = widget.mapToGlobal(widget.rect().topLeft())
                center_x = pos.x() + widget.width() // 2
                pos.setX(center_x)
                pos.setY(pos.y() - 5)  # Add some padding
            elif position == 'right':
                pos = widget.mapToGlobal(widget.rect().topRight())
                pos.setX(pos.x() + 5)  # Add some padding
            elif position == 'left':
                pos = widget.mapToGlobal(widget.rect().topLeft())
                pos.setX(pos.x() - 5)  # Add some padding
            else:
                pos = widget.mapToGlobal(widget.rect().bottomLeft())
                center_x = pos.x() + widget.width() // 2
                pos.setX(center_x)
                pos.setY(pos.y() + 5)  # Default to bottom-center

            tooltip.show_tooltip(widget._tooltip_text, pos, delay, timeout)

        # Custom leave event handler
        def custom_leave_event(event):
            # Call original handler
            if orig_leave:
                orig_leave(event)

            # Hide tooltip
            CustomToolTip.instance().hide_tooltip()

        # Replace event handlers
        widget.enterEvent = custom_enter_event
        widget.leaveEvent = custom_leave_event
