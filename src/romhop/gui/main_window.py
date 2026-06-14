from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from romhop.config import Settings
from romhop.gui import theme
from romhop.gui.library_view import LibraryView
from romhop.gui.settings_view import SettingsView


class MainWindow(QWidget):
    """Layout A: top search row, library/settings stack, pinned bottom bar."""

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("romhop")

        loaded = theme.load_active_theme(settings.theme)
        self.setStyleSheet(loaded.qss)

        # Top row: search + settings gear.
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search…")
        gear = QPushButton("⚙")
        gear.clicked.connect(self.show_settings)
        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(gear, 0)

        # Stacked content: library + settings.
        self.library = LibraryView()
        self.search.textChanged.connect(self.library.filter)
        self.settings_view = SettingsView(settings)
        self.settings_view.saved.connect(self.show_library)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.library)      # index 0
        self.stack.addWidget(self.settings_view)  # index 1

        # Bottom bar: selection count + download + sync status.
        self.bottom = QFrame()
        self.bottom.setObjectName("BottomBar")
        self._sel_label = QLabel("0 selected")
        self.download_btn = QPushButton("Download")
        self._sync_label = QLabel("Sync: idle")
        self._sync_label.setObjectName("StatusDim")
        bottom_row = QHBoxLayout(self.bottom)
        bottom_row.addWidget(self._sel_label)
        bottom_row.addWidget(self.download_btn)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self._sync_label)

        self.library.selection_changed.connect(self._on_selection)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.stack, 1)
        layout.addWidget(self.bottom)

    # --- view switching (named for testability) ---
    def show_settings(self) -> None:
        self.stack.setCurrentIndex(1)

    def show_library(self) -> None:
        self.stack.setCurrentIndex(0)

    def current_view_name(self) -> str:
        return "library" if self.stack.currentIndex() == 0 else "settings"

    # --- bottom bar state ---
    def sync_status_text(self) -> str:
        return self._sync_label.text()

    def set_sync_status(self, state: str) -> None:
        self._sync_label.setText(f"Sync: {state}")

    def _on_selection(self, roms: list) -> None:
        self._sel_label.setText(f"{len(roms)} selected")
