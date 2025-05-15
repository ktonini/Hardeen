from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QPoint, QEvent
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QPolygon, QPainterPath, QIcon, QFontMetrics
from .custom_tooltip import CustomToolTip
import os
import time
from ...utils.image_utils import load_exr_aovs


class ImageHandler:
    """Class for handling image loading and processing operations"""

    def __init__(self, output_callback=None, raw_output_callback=None):
        """
        Initialize the image handler.

        Args:
            output_callback: Callback function for formatted user messages
            raw_output_callback: Callback function for raw log messages
        """
        self.output_callback = output_callback
        self.raw_output_callback = raw_output_callback

    def is_file_in_use(self, file_path, timeout=1.0):
        """
        Check if a file is still being written to, with timeout in seconds.

        Args:
            file_path: Path to the file to check
            timeout: Maximum time to wait for file to be available

        Returns:
            bool: True if file is in use, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try to open the file in binary mode with write access
                with open(file_path, 'r+b'):
                    # If we can open it with write access, it's not being written to
                    return False
            except IOError:
                # File is locked, wait a bit
                time.sleep(0.1)

        # Additional check: see if the file size is changing
        try:
            size1 = os.path.getsize(file_path)
            time.sleep(0.5)  # Wait half a second
            size2 = os.path.getsize(file_path)

            # If the file size is still changing, it's being written
            if size1 != size2:
                return True
        except:
            pass  # Ignore any errors in this additional check

        # Timeout reached, consider the file still in use
        return True

    def load_image(self, image_path, preview_widget):
        """
        Load an image file and update the image preview widget.

        Args:
            image_path: Path to the image file
            preview_widget: ImagePreviewWidget instance to update

        Returns:
            bool: True if image was loaded successfully, False otherwise
        """
        if not image_path or not os.path.exists(image_path):
            preview_widget.update_preview([])
            return False

        try:
            # Check if file exists
            if not os.path.exists(image_path):
                if self.output_callback:
                    self.output_callback(
                        f"Cannot find image: {os.path.basename(image_path)}",
                        color='#ff6666'
                    )
                return False

            # Check if the file is complete (not still being written)
            if self.is_file_in_use(image_path, timeout=3.0):
                # If the file is still being written, show a message and wait
                if self.output_callback:
                    self.output_callback(
                        f"Waiting for image to finish writing: {os.path.basename(image_path)}",
                        color='#aaaaaa'
                    )
                preview_widget.update_preview([])
                return False

            # Handle based on file extension
            if image_path.lower().endswith('.exr'):
                return self.load_exr(image_path, preview_widget)
            else:
                # For other image types, load directly
                return self.load_generic_image(image_path, preview_widget)

        except Exception as e:
            # Handle error gracefully
            error_msg = f"Error loading image: {str(e)}"
            if self.output_callback:
                self.output_callback(error_msg, color='#ff6666')
            if self.raw_output_callback:
                self.raw_output_callback(f"Error loading image {image_path}: {str(e)}")

            # Show placeholder with error
            pixmap = QPixmap(200, 200)
            pixmap.fill(Qt.GlobalColor.darkGray)
            preview_widget.update_preview([(pixmap, "Image Preview Error")])
            return False

    def load_exr(self, image_path, preview_widget):
        """
        Load an EXR file and update the image preview area with its AOVs.

        Args:
            image_path: Path to the EXR file
            preview_widget: ImagePreviewWidget instance to update

        Returns:
            bool: True if image was loaded successfully, False otherwise
        """
        try:
            # Get file size for debug purposes
            try:
                file_size = os.path.getsize(image_path)
                print(f"Loading EXR file: {image_path}, size: {file_size} bytes")
            except:
                pass  # Ignore errors in getting file size

            # Try to load AOVs from the EXR file
            images = load_exr_aovs(image_path)

            # If no images were loaded but the file exists, it's likely corrupted
            if not images:
                if self.output_callback:
                    self.output_callback(
                        f"Could not read EXR layers from {os.path.basename(image_path)} - file may be corrupted or incomplete",
                        color='#ff6666'
                    )

                # Create a placeholder instead
                pixmap = QPixmap(200, 200)
                pixmap.fill(Qt.GlobalColor.darkGray)
                images = [(pixmap, "EXR Preview Unavailable")]

            preview_widget.update_preview(images)
            return True
        except Exception as e:
            # Handle error gracefully
            error_msg = f"Error loading EXR file: {str(e)}"
            if self.output_callback:
                self.output_callback(error_msg, color='#ff6666')
            if self.raw_output_callback:
                self.raw_output_callback(f"Error loading EXR {image_path}: {str(e)}")

            # Show placeholder with error
            pixmap = QPixmap(200, 200)
            pixmap.fill(Qt.GlobalColor.darkGray)
            preview_widget.update_preview([(pixmap, "EXR Preview Error")])
            return False

    def load_generic_image(self, image_path, preview_widget):
        """
        Load a non-EXR image file and update the preview widget.

        Args:
            image_path: Path to the image file
            preview_widget: ImagePreviewWidget instance to update

        Returns:
            bool: True if image was loaded successfully, False otherwise
        """
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # Create a single image preview
                preview_widget.update_preview([(pixmap, os.path.basename(image_path))])
                return True
            else:
                # If we can't load the image, show error
                if self.output_callback:
                    self.output_callback(
                        f"Cannot load image preview for: {os.path.basename(image_path)}",
                        color='#ff6666'
                    )
                preview_widget.update_preview([])
                return False
        except Exception as e:
            if self.output_callback:
                self.output_callback(
                    f"Error loading image: {str(e)}",
                    color='#ff6666'
                )
            preview_widget.update_preview([])
            return False


class PreviewLabel(QLabel):
    def __init__(self, tooltip_callback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tooltip_callback = tooltip_callback
        self._full_text = ""
        # Set specific style to ensure visibility
        self.setStyleSheet("color: #ffffff; padding: 2px 2px 3px 2px; min-height: 14px; max-height: 14px; font-size: 10px;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def setFullText(self, text):
        self._full_text = text

    def enterEvent(self, event):
        if self._tooltip_callback and self._full_text:
            # Show tooltip centered below the label
            rect = self.rect()
            bottom_center = self.mapToGlobal(QPoint(rect.width() // 2, rect.height()))
            self._tooltip_callback(self._full_text, bottom_center)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._tooltip_callback:
            self._tooltip_callback(None, None)
        super().leaveEvent(event)

class ImagePreviewWidget(QFrame):
    """Widget for displaying image previews with dynamic resizing"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("imagePreviewFrame")
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(1)

        # Create main layout
        self.image_layout = QHBoxLayout(self)
        self.image_layout.setSpacing(4)
        # Increased bottom margin to contain labels properly
        self.image_layout.setContentsMargins(4, 4, 4, 6)

        # Allow the layout to stretch
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Placeholder widget for when no images are loaded
        self.placeholder_widget = QLabel()
        self.placeholder_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_widget.setText("No image preview available")
        self.placeholder_widget.setObjectName("imagePlaceholder")

        # Create a wrapper container to center the placeholder
        placeholder_container = QWidget()
        placeholder_layout = QVBoxLayout(placeholder_container)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.setContentsMargins(20, 20, 20, 20)
        placeholder_layout.addWidget(self.placeholder_widget)

        self.image_layout.addWidget(placeholder_container)

        # Pre-create image+label containers (max 20 AOVs)
        self.image_widgets = []
        self._custom_tooltip = CustomToolTip()
        for _ in range(20):
            container = QWidget()
            container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            container_layout = QVBoxLayout(container)
            container_layout.setSpacing(4)
            container_layout.setContentsMargins(0, 0, 0, 0)

            image_label = QLabel()
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setStyleSheet("background-color: #212121;")
            image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            name_label = PreviewLabel(tooltip_callback=self._handle_tooltip)
            # Style is now set in PreviewLabel constructor
            name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            name_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            name_label.setWordWrap(False)

            container_layout.addWidget(image_label)
            container_layout.addWidget(name_label)
            self.image_layout.addWidget(container)
            container.hide()
            self.image_widgets.append((image_label, name_label))

        # Store original pixmaps for resizing
        self.original_pixmaps = [None] * 20

        # Create placeholder icon
        self._create_placeholder_icon()

        # Create image handler
        self.image_handler = ImageHandler()

    def _create_placeholder_icon(self):
        """Create the placeholder icon for when no images are available"""
        icon_size = 80
        icon = QPixmap(icon_size, icon_size)
        icon.fill(Qt.transparent)
        painter = QPainter(icon)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor("#555555"))
        pen.setWidth(2)
        painter.setPen(pen)
        brush = QBrush(QColor("#555555"))
        painter.setBrush(brush)

        # Draw mountains (filled triangles)
        # Back mountain
        points_back = [
            QPoint(icon_size//2, icon_size//4),          # Peak
            QPoint(icon_size-10, icon_size-12),          # Right base
            QPoint(icon_size//3, icon_size-12)           # Left base
        ]
        painter.drawPolygon(QPolygon(points_back))

        # Front mountain
        points_front = [
            QPoint(icon_size//4, icon_size//3),          # Peak
            QPoint(icon_size//2+10, icon_size-12),       # Right base
            QPoint(10, icon_size-12)                     # Left base
        ]
        painter.drawPolygon(QPolygon(points_front))

        # Draw sun (positioned above mountains)
        painter.setBrush(QBrush(QColor("#555555")))
        sun_size = icon_size//6
        painter.drawEllipse(icon_size-sun_size-10, 8, sun_size, sun_size)
        painter.end()

        # Set the icon to the placeholder
        self.placeholder_widget.setPixmap(icon)
        self.placeholder_widget.setMinimumSize(icon_size, icon_size)
        self.placeholder_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _handle_tooltip(self, text, global_pos):
        if text and global_pos:
            # Use 700ms delay (standard tooltip delay)
            self._custom_tooltip.show_tooltip(text, global_pos, delay=700)
        else:
            self._custom_tooltip.hide_tooltip()

    def update_preview(self, images: list):
        """Update the image preview area with a list of (pixmap, label) tuples."""
        # Make sure the image frame is visible
        self.show()

        # Hide all containers first
        for label, name_label in self.image_widgets:
            label.clear()
            name_label.clear()
            label.parent().hide()

        # Get reference to the placeholder's container
        placeholder_container = self.placeholder_widget.parent()

        # Hide placeholder by default
        placeholder_container.hide()

        if not images:
            # Show placeholder with minimum height
            placeholder_container.show()
            self.setFixedHeight(120)
            return

        # Show and update only as many containers as needed
        for i, (pixmap, label_text) in enumerate(images):
            if i >= len(self.image_widgets):
                break
            image_label, name_label = self.image_widgets[i]
            self.original_pixmaps[i] = pixmap
            image_label.setPixmap(pixmap)
            metrics = QFontMetrics(name_label.font())
            elided = metrics.elidedText(label_text, Qt.TextElideMode.ElideRight, image_label.width() if image_label.width() > 0 else 100)
            name_label.setText(elided)
            name_label.setFullText(label_text)
            image_label.parent().show()
            self.image_layout.setStretchFactor(image_label.parent(), 1)

        # Adjust sizes after adding images
        self.adjust_sizes()

    def load_image(self, image_path, output_callback=None, raw_output_callback=None):
        """Load an image file and update the preview widget.

        Args:
            image_path: Path to the image file
            output_callback: Optional callback for user messages
            raw_output_callback: Optional callback for raw log messages

        Returns:
            bool: True if image was loaded successfully, False otherwise
        """
        # Update the image handler's callbacks if provided
        if output_callback:
            self.image_handler.output_callback = output_callback
        if raw_output_callback:
            self.image_handler.raw_output_callback = raw_output_callback

        # Use the image handler to load the image
        return self.image_handler.load_image(image_path, self)

    def adjust_sizes(self):
        """Dynamically adjust the size of image preview thumbnails and frame height."""
        visible = [w for w in self.image_widgets if w[0].parent().isVisible()]
        count = len(visible)

        if count == 0:
            self.setFixedHeight(120)
            return

        # Calculate available width for the images
        available_width = self.width() - (self.image_layout.spacing() * (count - 1)) - 8  # Minimal padding
        target_width = available_width // count

        # Process each visible image container
        max_height = 0
        for i, (image_label, name_label) in enumerate(visible):
            original_pixmap = self.original_pixmaps[i]
            if original_pixmap and not original_pixmap.isNull():
                # Calculate scaled size maintaining aspect ratio
                original_size = original_pixmap.size()
                aspect_ratio = original_size.height() / original_size.width()
                scaled_height = int(target_width * aspect_ratio)

                # Scale the pixmap
                scaled = original_pixmap.scaled(
                    target_width,
                    scaled_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                image_label.setPixmap(scaled)
                image_label.setFixedSize(scaled.size())
                max_height = max(max_height, scaled_height)
                # Update elided text with new width information
                if hasattr(name_label, '_full_text') and name_label._full_text:
                    metrics = QFontMetrics(name_label.font())
                    elided = metrics.elidedText(name_label._full_text, Qt.TextElideMode.ElideRight, scaled.width())
                    name_label.setText(elided)

        # Set container and frame heights - ensure enough space for labels
        # Label area includes: label height (14px) + padding (6px) + spacing (4px)
        label_area_height = 24

        # Set fixed heights for containers
        for image_label, name_label in visible:
            container = image_label.parent()
            container.setFixedHeight(max_height + label_area_height)

        # Total frame height includes:
        # - image height
        # - label area height (24px)
        # - layout margins (4px top + 6px bottom = 10px)
        # - additional 20px adjustment for Qt's internal spacing and widget margins
        #   (this accounts for various layout and widget spacing that Qt applies internally)
        total_height = max_height + label_area_height + 10 + 20
        self.setFixedHeight(total_height)

    def resizeEvent(self, event):
        """Handle resize events to maintain proper image scaling"""
        super().resizeEvent(event)
        self.adjust_sizes()
