
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor

from crp_desktop.db import init_db
from crp_desktop.signals import init_signals
from crp_desktop.gui import MainWindow

def apply_light_theme(app: QApplication) -> None:
    """Force a simple light theme (works reliably across platforms)."""
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(255, 255, 255))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.Base, QColor(245, 245, 245))
    palette.setColor(QPalette.AlternateBase, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    app.setPalette(palette)

def run():
    # Ensure DB schema exists before starting the UI
    init_db()

    # Create the QApplication BEFORE any QWidget/QObjects
    app = QApplication(sys.argv)

    # Apply the light theme
    apply_light_theme(app)

    # initialize global signals instance (requires QApplication)
    init_signals()

    # Create and show main window
    mw = MainWindow()
    mw.show()

    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    run()
