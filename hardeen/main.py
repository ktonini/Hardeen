#!/usr/bin/python3

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from .gui.main_window import Hardeen

def main():
    app = QApplication(sys.argv)

    # Get the icon path relative to this file
    icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.png")
    app.setWindowIcon(QIcon(icon_path))

    # Create main window
    window = Hardeen()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
