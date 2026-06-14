from __future__ import annotations

import sys

from romhop import config


def run() -> None:
    from PySide6.QtWidgets import QApplication

    from romhop.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow(settings=config.load_settings())
    window.resize(900, 600)
    window.show()
    sys.exit(app.exec())
