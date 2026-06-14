from __future__ import annotations

from PySide6.QtCore import Signal
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
from romhop.gui.workers import CallableWorker


class MainWindow(QWidget):
    """Layout A: top search row, library/settings stack, pinned bottom bar."""

    downloads_finished = Signal()

    def __init__(self, settings: Settings, parent=None, *,
                 rom_provider=None, download_action=None):
        super().__init__(parent)
        self._settings = settings
        self._rom_provider = rom_provider
        self._download_action = download_action
        self._workers: list = []
        self._pending = 0
        self.setWindowTitle("romhop")

        loaded = theme.load_active_theme(settings.theme)
        self.setStyleSheet(loaded.qss)

        # Top row: search + settings gear.
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search…")
        gear = QPushButton("⚙")
        gear.clicked.connect(self.toggle_settings)
        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(gear, 0)

        # Stacked content: library + settings.
        self.library = LibraryView()
        self.search.textChanged.connect(self.library.filter)
        self.settings_view = SettingsView(settings)
        self.settings_view.saved.connect(self.show_library)
        self.settings_view.cancelled.connect(self.show_library)
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
        self.download_btn.clicked.connect(self.download_selected)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.stack, 1)
        layout.addWidget(self.bottom)

    # --- view switching (named for testability) ---
    def show_settings(self) -> None:
        # Drop any stale edits from a previous visit before showing the form.
        self.settings_view.reset()
        self.settings_view.setFocus()
        self.stack.setCurrentIndex(1)

    def show_library(self) -> None:
        self.stack.setCurrentIndex(0)

    def toggle_settings(self) -> None:
        # Gear acts as a toggle: into settings, or back out (discarding edits).
        if self.current_view_name() == "settings":
            self.settings_view.reset()
            self.show_library()
        else:
            self.show_settings()

    def current_view_name(self) -> str:
        return "library" if self.stack.currentIndex() == 0 else "settings"

    # --- bottom bar state ---
    def sync_status_text(self) -> str:
        return self._sync_label.text()

    def set_sync_status(self, state: str) -> None:
        self._sync_label.setText(f"Sync: {state}")

    def _on_selection(self, roms: list) -> None:
        self._sel_label.setText(f"{len(roms)} selected")

    # --- library loading + downloads ---
    def load_library(self) -> None:
        if self._rom_provider is None:
            return
        self.library.set_roms(self._rom_provider())

    def download_selected(self) -> None:
        if self._download_action is None:
            self.downloads_finished.emit()
            return
        selected = self.library.selected_roms()
        self._pending = len(selected)
        if self._pending == 0:
            self.downloads_finished.emit()
            return
        # Disable while a batch runs so a second batch can't reset _pending
        # underneath the in-flight workers.
        self.download_btn.setEnabled(False)
        for rom in selected:
            worker = CallableWorker(lambda r=rom: self._download_action(r))
            worker.done.connect(self._on_download_done)
            worker.error.connect(self._on_download_error)
            # finished fires after run() returns: safe point to drop the
            # reference so the worker list doesn't grow unbounded.
            worker.finished.connect(lambda w=worker: self._cleanup_worker(w))
            self._workers.append(worker)
            worker.start()

    def _cleanup_worker(self, worker: CallableWorker) -> None:
        if worker in self._workers:
            self._workers.remove(worker)
        worker.deleteLater()

    def _on_download_done(self, _result) -> None:
        self._finish_one()

    def _on_download_error(self, message: str) -> None:
        self.set_sync_status(f"error: {message}")
        self._finish_one()

    def _finish_one(self) -> None:
        self._pending -= 1
        if self._pending <= 0:
            self._pending = 0
            self.download_btn.setEnabled(True)
            self.downloads_finished.emit()
