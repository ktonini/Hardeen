import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QComboBox, QSpinBox, QCheckBox, QLineEdit, QGroupBox,
    QProgressBar, QMessageBox, QFileDialog, QFrame, QSplitter, QTextEdit, QDialog,
    QApplication, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QPoint, QSize, QRectF, QPointF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPolygon, QPainterPath, QFont

from .widgets.loading_combo_box import LoadingComboBox
from .widgets.frame_progress import FrameProgressWidget
from .widgets.image_preview import ImagePreviewWidget
from .widgets.custom_tooltip import TooltipHelper
from ..config import DEFAULT_FOLDER, SHUTDOWN_DELAYS, CURRENT_COLOR, COMPLETED_COLOR, DISABLED_TEXT_COLOR

# Get resources directory path
RESOURCES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources")

# Mapping function to convert config delay values to UI display values
def get_ui_shutdown_delay(delay_value):
    """Convert config shutdown delay to UI display format"""
    if delay_value == "No delay":
        return "No delay"
    elif "minute" in delay_value:
        # Replace "X minutes" with "Xm delay"
        minutes = delay_value.split()[0]
        return f"{minutes}m delay"
    elif "hour" in delay_value:
        # Replace "X hour" with "Xh delay"
        hours = delay_value.split()[0]
        return f"{hours}h delay"
    return delay_value

class UIComponents:
    """Class to organize UI components for the main window"""

    @staticmethod
    def create_hip_path_section(parent):
        """Create the Hip Path section UI elements"""
        hip_layout = QHBoxLayout()
        hip_layout.setSpacing(4)

        hip_label = QLabel("Hip Path:")
        hip_input = LoadingComboBox()
        hip_input.setEditable(True)
        hip_input.setMinimumWidth(300)

        hip_browse_btn = QPushButton("Browse...")
        hip_refresh_btn = QPushButton()
        hip_refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        hip_refresh_btn.setFixedSize(24, 24)

        hip_layout.addWidget(hip_label)
        hip_layout.addWidget(hip_input, 1)  # Add stretch factor
        hip_layout.addWidget(hip_browse_btn)
        hip_layout.addWidget(hip_refresh_btn)

        # Add tooltips
        TooltipHelper.install(hip_refresh_btn, "Refresh recent HIP files")

        return hip_layout, hip_input, hip_browse_btn, hip_refresh_btn

    @staticmethod
    def create_out_path_section(parent):
        """Create the Out Path section UI elements"""
        out_layout = QHBoxLayout()
        out_layout.setSpacing(4)

        out_label = QLabel("Out Path:")
        out_input = LoadingComboBox()
        out_input.setEditable(True)
        out_input.setMinimumWidth(300)

        out_refresh_btn = QPushButton()
        out_refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        out_refresh_btn.setFixedSize(24, 24)

        out_layout.addWidget(out_label)
        out_layout.addWidget(out_input, 1)  # Add stretch factor
        out_layout.addWidget(out_refresh_btn)

        # Add tooltips
        TooltipHelper.install(out_refresh_btn, "Refresh out nodes from HIP file (F5)")

        return out_layout, out_input, out_refresh_btn

    @staticmethod
    def create_overrides_group(parent):
        """Create the Overrides group UI elements"""
        overrides_group = QGroupBox("Overrides")
        overrides_layout = QHBoxLayout(overrides_group)
        overrides_layout.setSpacing(4)

        range_check = QCheckBox("Frame Range:")

        start_frame = QLineEdit()
        start_frame.setFixedWidth(70)
        start_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        start_frame.setText("1")

        end_frame = QLineEdit()
        end_frame.setFixedWidth(70)
        end_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        end_frame.setText("100")

        frame_step = QComboBox()
        frame_step.setEditable(True)
        frame_step.setFixedWidth(70)
        frame_step.addItems(["1", "2", "3", "4", "5", "10"])
        frame_step.setCurrentText("1")
        frame_step.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)

        to_label = QLabel("to")
        to_label.setFixedWidth(16)

        by_label = QLabel("by")
        by_label.setFixedWidth(16)

        skip_check = QCheckBox("Skip Rendered Frames")

        overrides_layout.addWidget(range_check)
        overrides_layout.addWidget(start_frame)
        overrides_layout.addWidget(to_label)
        overrides_layout.addWidget(end_frame)
        overrides_layout.addWidget(by_label)
        overrides_layout.addWidget(frame_step)
        overrides_layout.addSpacing(12)
        overrides_layout.addWidget(skip_check)
        overrides_layout.addStretch()  # Push everything to the left

        return overrides_group, range_check, start_frame, end_frame, frame_step, skip_check

    @staticmethod
    def create_advanced_settings_group(parent):
        """Create the Advanced Settings group UI elements"""
        settings_group = QGroupBox("Advanced Settings")
        settings_layout = QHBoxLayout(settings_group)

        # Left form layout (notification controls)
        left_form = QVBoxLayout()

        # Notification controls
        notification_controls = QHBoxLayout()
        notify_check = QCheckBox("Enable notifications every")
        notify_frames = QLineEdit()
        notify_frames.setPlaceholderText("10")
        notify_frames.setFixedWidth(70)
        notify_frames.setAlignment(Qt.AlignmentFlag.AlignCenter)

        notification_controls.addWidget(notify_check)
        notification_controls.addWidget(notify_frames)
        notification_controls.addWidget(QLabel("frames"))
        notification_controls.addStretch()
        left_form.addLayout(notification_controls)

        # Shutdown controls
        shutdown_controls = QHBoxLayout()
        shutdown_check = QCheckBox("Shut down after render with")

        shutdown_delay = QComboBox()
        shutdown_delay.setObjectName("shutdownDelayCombo")
        shutdown_delay.setFixedWidth(130)
        shutdown_delay.setEditable(False)

        # Add items using the config values mapped to UI display format
        ui_delay_values = [get_ui_shutdown_delay(delay) for delay in SHUTDOWN_DELAYS]
        shutdown_delay.addItems(ui_delay_values)
        shutdown_delay.setCurrentIndex(0)

        shutdown_controls.addWidget(shutdown_check)
        shutdown_controls.addWidget(shutdown_delay)
        shutdown_controls.addStretch()
        left_form.addLayout(shutdown_controls)

        settings_layout.addLayout(left_form, 1)

        # Settings buttons layout
        settings_btn_layout = QHBoxLayout()
        settings_btn_layout.addStretch()

        # Help button with icon
        help_btn = QPushButton()
        help_btn.setObjectName("helpButton")
        help_btn.setIcon(UIComponents.create_help_icon())
        help_btn.setFixedSize(24, 24)
        help_btn.setIconSize(QSize(20, 20))
        help_btn.setProperty("fixedsize", "true")

        # Settings button with icon
        settings_btn = QPushButton()
        settings_btn.setObjectName("settingsButton")
        settings_btn.setIcon(UIComponents.create_gear_icon())
        settings_btn.setFixedSize(24, 24)
        settings_btn.setIconSize(QSize(20, 20))
        settings_btn.setProperty("fixedsize", "true")

        settings_btn_layout.addWidget(help_btn)
        settings_btn_layout.addWidget(settings_btn)
        settings_layout.addLayout(settings_btn_layout)

        # Add tooltips
        TooltipHelper.install(help_btn, "Show Help & Tips")
        TooltipHelper.install(settings_btn, "Configure Advanced Settings")

        return (
            settings_group, notify_check, notify_frames,
            shutdown_check, shutdown_delay, help_btn, settings_btn
        )

    @staticmethod
    def create_help_icon():
        """Create a help icon (question mark)"""
        help_icon = QIcon.fromTheme("help-contents")
        if not help_icon.isNull():
            return help_icon

        # Create a simple help icon (question mark)
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw question mark
        painter.setPen(QPen(QColor("#d6d6d6"), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(QBrush(QColor("#d6d6d6")))

        # Draw circle
        painter.drawEllipse(QPointF(12, 12), 9, 9)

        # Draw question mark
        painter.setPen(QPen(QColor("#232323"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        path = QPainterPath()
        path.moveTo(8, 8)
        path.cubicTo(8, 6, 10, 5, 12, 5)
        path.cubicTo(14, 5, 16, 6, 16, 8)
        path.cubicTo(16, 10, 14, 11, 12, 13)
        path.lineTo(12, 16)
        painter.drawPath(path)

        # Draw dot at bottom
        painter.drawEllipse(QPointF(12, 19), 1, 1)

        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def create_gear_icon():
        """Create a gear icon for settings"""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Use colors that match the UI
        icon_color = QColor("#d6d6d6")
        painter.setPen(QPen(icon_color, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(QBrush(icon_color))

        # Draw gear with rectangular teeth
        center_x, center_y = 12, 12
        main_radius = 6
        inner_radius = 5
        num_teeth = 7

        # Create the gear shape with rectangular teeth
        gear_path = QPainterPath()

        from math import sin, cos, pi

        # Start by creating the main circle
        gear_path.addEllipse(QPointF(center_x, center_y), main_radius, main_radius)

        # Add rectangular teeth
        for i in range(num_teeth):
            angle = 2 * pi * i / num_teeth

            # Calculate the four corners of the rectangular tooth
            # Inner corners on the main circle
            inner_angle1 = angle - (pi/num_teeth) * 0.4
            inner_angle2 = angle + (pi/num_teeth) * 0.4

            inner_x1 = center_x + main_radius * cos(inner_angle1)
            inner_y1 = center_y + main_radius * sin(inner_angle1)

            inner_x2 = center_x + main_radius * cos(inner_angle2)
            inner_y2 = center_y + main_radius * sin(inner_angle2)

            # Outer corners extended from the main circle
            outer_angle1 = inner_angle1
            outer_angle2 = inner_angle2

            tooth_height = 3
            outer_x1 = center_x + (main_radius + tooth_height) * cos(outer_angle1)
            outer_y1 = center_y + (main_radius + tooth_height) * sin(outer_angle1)

            outer_x2 = center_x + (main_radius + tooth_height) * cos(outer_angle2)
            outer_y2 = center_y + (main_radius + tooth_height) * sin(outer_angle2)

            # Create a path for this tooth
            tooth_path = QPainterPath()
            tooth_path.moveTo(inner_x1, inner_y1)
            tooth_path.lineTo(outer_x1, outer_y1)
            tooth_path.lineTo(outer_x2, outer_y2)
            tooth_path.lineTo(inner_x2, inner_y2)
            tooth_path.closeSubpath()

            # Add this tooth to the gear
            gear_path = gear_path.united(tooth_path)

        # Create inner circle (hole)
        inner_hole = QPainterPath()
        inner_hole.addEllipse(QPointF(center_x, center_y), inner_radius, inner_radius)

        # Subtract the hole from the gear
        gear_path = gear_path.subtracted(inner_hole)

        # Draw the gear
        painter.drawPath(gear_path)

        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def create_control_buttons(parent):
        """Create the render control buttons"""
        controls_layout = QHBoxLayout()

        open_folder_btn = QPushButton("Open Output Location")
        open_folder_btn.setObjectName("openFolderButton")
        open_folder_btn.setEnabled(False)
        open_folder_btn.setMinimumHeight(48)

        cancel_btn = QPushButton("Interrupt")
        cancel_btn.setObjectName("cancelButton")
        cancel_btn.setMinimumHeight(48)
        cancel_btn.hide()  # Initially hidden

        render_btn = QPushButton("Render")
        render_btn.setObjectName("renderButton")
        render_btn.setMinimumHeight(48)

        controls_layout.addWidget(open_folder_btn)
        controls_layout.addWidget(cancel_btn)
        controls_layout.addWidget(render_btn)

        # Add tooltips
        TooltipHelper.install(render_btn, "Start Render (Ctrl+R)")
        TooltipHelper.install(cancel_btn, "Interrupt render (Esc)")
        TooltipHelper.install(open_folder_btn, "Open the output folder in file explorer")

        return controls_layout, open_folder_btn, cancel_btn, render_btn

    @staticmethod
    def create_text_output_area(parent):
        """Create the text output and raw output areas"""
        text_splitter = QSplitter(Qt.Orientation.Horizontal)

        summary_text = QTextEdit()
        summary_text.setReadOnly(True)
        summary_text.setObjectName("outputArea")

        raw_text = QTextEdit()
        raw_text.setReadOnly(True)
        raw_text.setObjectName("outputArea")

        text_splitter.addWidget(summary_text)
        text_splitter.addWidget(raw_text)
        text_splitter.setSizes([500, 500])

        return text_splitter, summary_text, raw_text

    @staticmethod
    def create_stats_layout(parent):
        """Create the statistics/info line UI elements"""
        stats_layout = QHBoxLayout()
        stats_layout.setObjectName("statsInfoLine")
        stats_layout.setSpacing(0)  # Remove default spacing
        stats_layout.setContentsMargins(0, 0, 0, 0)

        # Helper function to create a stat container
        def create_stat_container(label_widget, value_widget):
            container = QFrame()
            container.setObjectName("statContainer")
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(8, 4, 8, 4)
            container_layout.setSpacing(4)
            container_layout.addWidget(label_widget)
            container_layout.addWidget(value_widget)
            return container

        # Frames
        fc_label = QLabel("Frames:")
        fc_value = QLabel("-")
        tfc_label = QLabel("/")
        tfc_value = QLabel("-")

        # Create frames container with custom layout
        frames_container = QFrame()
        frames_container.setObjectName("statContainer")
        frames_layout = QHBoxLayout(frames_container)
        frames_layout.setContentsMargins(8, 4, 8, 4)
        frames_layout.setSpacing(2)  # Very tight spacing for frame elements
        frames_layout.addWidget(fc_label)
        frames_layout.addWidget(fc_value)
        frames_layout.addWidget(tfc_label)
        frames_layout.addWidget(tfc_value)

        # Average time
        average_label = QLabel("Average:")
        average_value = QLabel("-")
        average_container = create_stat_container(average_label, average_value)

        # Elapsed time
        elapsed_label = QLabel("Elapsed:")
        elapsed_value = QLabel("-")
        elapsed_container = create_stat_container(elapsed_label, elapsed_value)

        # Estimated total time
        total_label = QLabel("Est. Total:")
        total_value = QLabel("-")
        total_container = create_stat_container(total_label, total_value)

        # ETA
        eta_label = QLabel("ETA:")
        eta_value = QLabel("--:--:--")
        eta_container = create_stat_container(eta_label, eta_value)

        # Remaining time
        remaining_label = QLabel("Remaining:")
        remaining_value = QLabel("--")
        remaining_container = create_stat_container(remaining_label, remaining_value)

                # Add the first container (frames)
        stats_layout.addWidget(frames_container)

        # Add stretches and middle containers
        stats_layout.addStretch(1)
        stats_layout.addWidget(average_container)
        stats_layout.addStretch(1)
        stats_layout.addWidget(elapsed_container)
        stats_layout.addStretch(1)
        stats_layout.addWidget(total_container)
        stats_layout.addStretch(1)
        stats_layout.addWidget(eta_container)
        stats_layout.addStretch(1)

        # Add the last container (remaining) - no stretch after it
        stats_layout.addWidget(remaining_container)

        # Style stats labels and values
        for label in [fc_value, tfc_value, average_value, elapsed_value, total_value, eta_value, remaining_value]:
            label.setStyleSheet(f"color: {CURRENT_COLOR}; font-weight: bold;")
        for label in [fc_label, tfc_label, average_label, elapsed_label, total_label, eta_label, remaining_label]:
            label.setStyleSheet("color: #d6d6d6; font-weight: normal;")

        return (
            stats_layout,
            fc_label, fc_value, tfc_label, tfc_value,
            average_label, average_value, elapsed_label, elapsed_value,
            total_label, total_value, eta_label, eta_value,
            remaining_label, remaining_value
        )

    @staticmethod
    def create_frame_progress_widget(parent):
        """Create the frame progress widget"""
        progress_frame = FrameProgressWidget()
        progress_frame.setMinimumHeight(50)
        progress_frame.setMaximumHeight(70)


        return progress_frame

    @staticmethod
    def create_image_preview(parent):
        """Create the image preview widget"""
        image_preview = ImagePreviewWidget()
        image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        return image_preview

    @staticmethod
    def apply_stylesheet(widget):
        """Apply the application stylesheet"""
        widget.setStyleSheet(widget.styleSheet() + """
            QWidget {
                font-family: 'Inter', 'Segoe UI', 'Arial', sans-serif;
                font-size: 14px;
                color: #e0e0e0;
            }
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #353535, stop:1 #232323);
            }
            QSplitter::handle {
                background: transparent;
                margin: 0 2px;
            }
            QSplitter::handle:horizontal {
                width: 4px;
                image: none;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #444444;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #555555;
            }
            QScrollBar::add-line:vertical {
                height: 0px;
                border: none;
                background: none;
            }
            QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
                border: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: transparent;
                height: 8px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #444444;
                min-width: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #555555;
            }
            QScrollBar::add-line:horizontal {
                width: 0px;
                border: none;
                background: none;
            }
            QScrollBar::sub-line:horizontal {
                width: 0px;
                border: none;
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
                border: none;
            }
            QGroupBox {
                border: none;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
                padding-bottom: 12px;
                padding-left: 12px;
                padding-right: 12px;
                background: rgba(40,40,40,0.96);
                font-weight: 600;
                font-size: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 10px 0 10px;
                color: #ff6b2b;
                font-size: 16px;
                font-weight: 700;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #181818;
                color: #f0f0f0;
                border: none;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 14px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #ff6b2b;
            }
            QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
                background-color: #292929;
                color: #888;
                border: none;
            }
            QPushButton {
                background: #232323;
                color: #e0e0e0;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
                font-weight: 600;
                font-size: 15px;
            }
            QPushButton:hover {
                background: #ff6b2b;
                color: #181818;
                border: none;
            }
            QPushButton:pressed {
                background: #cc3d00;
                color: #fff;
            }
            QPushButton:disabled {
                background-color: #292929;
                color: #666666;
                border: none;
            }
            QPushButton#renderButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 """ + CURRENT_COLOR + """, stop:1 #ff6b2b);
                color: #181818;
                border: none;
                border-radius: 4px;
                font-size: 18px;
                font-weight: 800;
            }
            QPushButton#renderButton:hover {
                background: #ff6b2b;
                color: #fff;
            }
            QPushButton[fixedsize="true"] {
                background: #232323;
                padding: 2px;
                border-radius: 4px;
            }
            QPushButton[fixedsize="true"]:hover {
                background: #555555;
                border: none;
            }
            QPushButton[fixedsize="true"]:pressed {
                background: #ff6b2b;
            }
            QComboBox {
                padding-right: 20px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: url(""" + os.path.join(RESOURCES_DIR, "down_arrow.png") + """);
                width: 12px;
                height: 12px;
                margin-right: 4px;
            }
            QComboBox:hover {
                border: 1px solid #ff6b2b;
            }
            QComboBox:on {
                border: 1px solid #ff6b2b;
            }
            QComboBox:disabled {
                background-color: #292929;
                color: #666666;
                border: none;
            }
            QComboBox::drop-down:disabled {
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background-color: #181818;
                color: #ffffff;
                selection-background-color: #ff6b2b;
                selection-color: #ffffff;
                border: none;
                border-radius: 4px;
            }
            QComboBox#shutdownDelayCombo {
                padding-right: 20px;
                padding-left: 10px;
                font-weight: 500;
            }
            QComboBox#shutdownDelayCombo:hover {
                border: 1px solid #ff6b2b;
            }
            QComboBox#shutdownDelayCombo QAbstractItemView::item:hover {
                background-color: #ff6b2b;
                color: #ffffff;
            }
            QComboBox#shutdownDelayCombo QAbstractItemView::item:selected {
                background-color: #ff6b2b;
                color: #ffffff;
            }
            QComboBox#shutdownDelayCombo::item:selected {
                background-color: #ff6b2b;
                color: #ffffff;
                border: none;
            }
            QComboBox#shutdownDelayCombo::selection {
                background-color: #ff6b2b;
                color: #ffffff;
            }
            #outputArea {
                background-color: #232323;
                border: none;
                border-radius: 4px;
                margin-top: 8px;
                margin-bottom: 8px;
            }
            #imagePlaceholder {
                background-color: transparent;
                min-height: 64px;
                min-width: 64px;
                color: #888;
                font-size: 18px;
                margin: 0;
                padding: 0;
            }
            #imagePreviewFrame {
                background-color: #232323;
                border: none;
                border-radius: 4px;
                margin: 8px 0;
                padding: 4px;
            }
            QFrame[frameShape="4"] {
                background: #232323;
                border-radius: 4px;
                border: none;
                margin: 8px 0;
                padding: 1px;
            }
            #statsInfoLine {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #232323, stop:1 #292929);
                border-radius: 4px;
                border: none;
                margin: 8px 0;
                padding: 6px 12px;
                font-size: 15px;
                font-weight: 600;
                color: #ff6b2b;
            }
            #statContainer {
                background: rgba(35, 35, 35, 0.7);
                border-radius: 6px;
                padding: 2px;
                border: 1px solid rgba(60, 60, 60, 0.5);
            }
            #testShutdownButton {
                background: #333333;
                color: #dddddd;
                font-weight: 600;
                border: none;
                padding-left: 12px;
                padding-right: 16px;
            }
            #testShutdownButton:hover {
                background: #cc3500;
                color: #ffffff;
            }
            #testShutdownButton:disabled {
                background-color: #252525;
                color: #555555;
                border: none;
                opacity: 0.7;
            }
            #testNotifyButton {
                background: #333333;
                color: #dddddd;
                font-weight: 600;
                border: none;
                padding-left: 12px;
                padding-right: 16px;
            }
            #testNotifyButton:hover {
                background: #0066cc;
                color: #ffffff;
            }
            #testNotifyButton:disabled {
                background-color: #252525;
                color: #555555;
                border: none;
                opacity: 0.7;
            }
            #settingsStatusArea QLabel {
                padding: 2px 0;
            }
            QPushButton#settingsButton {
                background: #333333;
                border: none;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton#settingsButton:hover {
                background: #505050;
                color: #ffffff;
            }
        """)
