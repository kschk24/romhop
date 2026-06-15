from __future__ import annotations

from PySide6.QtCore import Signal
from dataclasses import replace

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from romhop import config
from romhop.config import Settings
from romhop.gui import theme
from romhop.gui.filter_bar import FilterBar
from romhop.gui.library_view import LibraryView, platforms_from_roms
from romhop.gui.settings_view import SettingsView
from romhop.gui.workers import DownloadWorker, SyncWorker
from romhop.local_index import downloaded_rom_ids
from romhop.platform_names import display_name


def _human_speed(bytes_per_sec: float) -> str:
    """Render a bytes/sec figure as a compact human-readable rate."""
    units = ["B/s", "KB/s", "MB/s", "GB/s"]
    value = float(bytes_per_sec)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.0f} {unit}" if unit == "B/s" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB/s"


def _human_size(num_bytes: int) -> str:
    """Render a byte count as a compact human-readable size."""
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def _sync_state_class(state: str) -> str:
    """Map a fine-grained sync status string to the coarse class that drives
    the indicator dot's colour: ``off`` (grey), ``running`` (green), ``error``
    (red)."""
    if state.startswith("error"):
        return "error"
    if state == "watching":
        return "running"
    return "off"


# Dot colours per coarse class. Grey at rest, green while watching, red on error.
_SYNC_DOT_COLORS = {"off": "#8b949e", "running": "#3fb950", "error": "#f85149"}


class MainWindow(QWidget):
    """Layout A: top search row, library/settings stack, pinned bottom bar."""

    downloads_finished = Signal()
    # Fires whenever the sync indicator text changes; lets tests await state.
    _sync_status_changed = Signal(str)

    def __init__(self, settings: Settings, parent=None, *,
                 rom_provider=None, download_action=None,
                 sync_watch_fn=None, persist_settings=None, cover_provider=None,
                 platform_label=None, platform_names=None):
        super().__init__(parent)
        self._settings = settings
        self._rom_provider = rom_provider
        self._download_action = download_action
        self._cover_provider = cover_provider
        self._sync_watch_fn = sync_watch_fn
        self._platform_names = platform_names
        self._persist_settings = persist_settings or config.save_settings
        self._download_worker = None
        self._sync_worker = None
        self._progress_name = ""
        self._progress_pos = ""
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
        self.library = LibraryView(cover_provider=cover_provider,
                                   platform_label=platform_label)
        # Filter bar: platform, downloaded, sort. Wired to library setters.
        self.filter_bar = FilterBar()
        self.filter_bar.platform_changed.connect(self.library.set_platform_filter)
        self.filter_bar.downloaded_changed.connect(self.library.set_downloaded_filter)
        self.filter_bar.sort_changed.connect(self.library.set_sort)
        # Search is context-dependent: it filters whichever view is active.
        self.search.textChanged.connect(self._on_search_changed)
        self.settings_view = SettingsView(settings)
        self.settings_view.saved.connect(self._on_settings_saved)
        self.settings_view.cancelled.connect(self.show_library)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.library)      # index 0
        self.stack.addWidget(self.settings_view)  # index 1

        # Bottom bar: selection count + download + sync status.
        self.bottom = QFrame()
        self.bottom.setObjectName("BottomBar")
        self._sel_label = QLabel("0 selected")
        self.download_btn = QPushButton("Download")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("CancelDownload")
        self.cancel_btn.hide()
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        # Single shared progress bar: the current game in the batch. Hidden when
        # idle so the bottom bar stays clean until a download is running.
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("DownloadProgress")
        self.progress_bar.setFixedWidth(180)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("StatusDim")
        self.progress_label.hide()
        # Single sync control: one button toggles sync on/off and its leading
        # dot reports the live worker state (grey idle → green watching → red
        # error). No separate indicator, no jump-to-settings shortcut.
        self._sync_state = "idle"
        self.sync_button = QPushButton("●  Save-Sync")
        self.sync_button.setObjectName("SyncButton")
        self.sync_button.setCheckable(True)
        self.sync_button.setChecked(settings.sync_enabled)  # before connect: no fire
        self.sync_button.toggled.connect(self._on_sync_toggled)
        bottom_row = QHBoxLayout(self.bottom)
        bottom_row.addWidget(self._sel_label)
        bottom_row.addWidget(self.download_btn)
        bottom_row.addWidget(self.cancel_btn)
        bottom_row.addWidget(self.progress_bar)
        bottom_row.addWidget(self.progress_label)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.sync_button)
        # Paint the dot grey for the initial idle state.
        self.set_sync_status(self._sync_state)
        # setChecked above fired no signal (it ran pre-connect), so a persisted
        # sync_enabled=True would leave the worker stopped and the dot grey
        # despite the toggle reading on. Kick off the worker now to match it.
        if settings.sync_enabled:
            self._reconcile_sync(True)

        self.library.selection_changed.connect(self._on_selection)
        self.download_btn.clicked.connect(self.download_selected)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.filter_bar)
        layout.addWidget(self.stack, 1)
        layout.addWidget(self.bottom)

    # --- search dispatch ---
    def _on_search_changed(self, query: str) -> None:
        # Route the query to whichever view is currently shown.
        if self.current_view_name() == "settings":
            self.settings_view.filter(query)
        else:
            self.library.filter(query)

    # --- view switching (named for testability) ---
    def show_settings(self) -> None:
        # Drop any stale edits from a previous visit before showing the form.
        self.settings_view.reset()
        self.settings_view.setFocus()
        self.filter_bar.hide()
        self.stack.setCurrentIndex(1)
        # Apply the standing query to the rows now that settings is active.
        self.settings_view.filter(self.search.text())

    def show_library(self) -> None:
        self.filter_bar.show()
        self.stack.setCurrentIndex(0)
        # Re-apply the standing query to the game list.
        self.library.filter(self.search.text())

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
        return f"Sync: {self._sync_state}"

    def sync_state(self) -> str:
        """Coarse class behind the indicator dot: off / running / error."""
        return _sync_state_class(self._sync_state)

    def set_sync_status(self, state: str) -> None:
        # Record the fine-grained text, then recolour the button's dot from its
        # coarse class. Tooltip carries the detail (e.g. an error message).
        self._sync_state = state
        color = _SYNC_DOT_COLORS[_sync_state_class(state)]
        self.sync_button.setStyleSheet(f"#SyncButton {{ color: {color}; }}")
        self.sync_button.setToolTip(f"Sync: {state}")
        self._sync_status_changed.emit(state)

    # --- sync controls ---
    def _on_sync_toggled(self, enabled: bool) -> None:
        # Bottom-bar toggle: persist the intent (survives restart), keep the
        # settings menu in lockstep so the two never disagree, then reconcile.
        self._settings = replace(self._settings, sync_enabled=enabled)
        self._persist_settings(self._settings)
        self.settings_view.set_sync_enabled(enabled)
        self._reconcile_sync(enabled)

    def _reconcile_sync(self, enabled: bool) -> None:
        if enabled:
            self._start_sync()
        else:
            self._stop_sync()

    def _start_sync(self) -> None:
        if self._sync_watch_fn is None or self._sync_worker is not None:
            return
        worker = SyncWorker(self._sync_watch_fn)
        worker.status.connect(self.set_sync_status)
        worker.error.connect(lambda msg: self.set_sync_status(f"error: {msg}"))
        worker.finished.connect(self._on_sync_finished)
        self._sync_worker = worker
        worker.start()

    def _stop_sync(self) -> None:
        if self._sync_worker is not None:
            self._sync_worker.stop()

    def _on_sync_finished(self) -> None:
        if self._sync_worker is not None:
            self._sync_worker.deleteLater()
            self._sync_worker = None

    def _on_settings_saved(self) -> None:
        # Settings already persisted itself; adopt its Settings so our in-memory
        # copy doesn't go stale, then mirror the sync flag onto the bottom
        # button WITHOUT re-persisting (block its signal) and reconcile.
        self._settings = self.settings_view.current_settings()
        enabled = self._settings.sync_enabled
        self.sync_button.blockSignals(True)
        self.sync_button.setChecked(enabled)
        self.sync_button.blockSignals(False)
        self._reconcile_sync(enabled)
        self.show_library()

    def _on_selection(self, roms: list) -> None:
        self._sel_label.setText(f"{len(roms)} selected")

    # --- library loading + downloads ---
    def load_library(self) -> None:
        if self._rom_provider is None:
            return
        roms = self._rom_provider()
        self.library.set_roms(roms)
        pairs = [(slug, self._platform_name_for(roms, slug))
                 for slug in platforms_from_roms(roms)]
        self.filter_bar.set_platforms(pairs)
        self._refresh_downloaded(roms)

    def _platform_name_for(self, roms, slug: str) -> str:
        rom = next((r for r in roms if r.platform_slug == slug), None)
        return display_name(rom, self._platform_names) if rom is not None else slug

    def _refresh_downloaded(self, roms=None) -> None:
        roms = roms if roms is not None else getattr(self.library, "_roms", [])
        ids = downloaded_rom_ids(roms, self._settings.roms_root,
                                 self._settings.platform_overrides)
        self.library.set_downloaded(ids)

    def download_selected(self) -> None:
        if self._download_action is None:
            self.downloads_finished.emit()
            return
        selected = self.library.selected_roms()
        if not selected:
            self.downloads_finished.emit()
            return
        # Disable while a batch runs so a second batch can't start underneath
        # the in-flight queue. One worker drains the queue sequentially.
        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading…")
        self.cancel_btn.show()
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("Cancel")
        self._begin_progress()
        worker = DownloadWorker(selected, self._download_action)
        worker.item_started.connect(self._on_item_started)
        worker.item_progress.connect(self._on_item_progress)
        worker.item_error.connect(self._on_item_error)
        worker.finished.connect(self._on_batch_finished)
        self._download_worker = worker
        worker.start()

    # --- download progress UI ---
    def _begin_progress(self) -> None:
        self.progress_bar.setMaximum(0)  # busy until the first byte count lands
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.progress_label.setText("")
        self.progress_label.show()

    def _on_item_started(self, index: int, count: int, name: str) -> None:
        self._progress_name = name
        self._progress_pos = f"{index}/{count}"
        # New game in the batch: bar goes indeterminate until its total arrives.
        self.progress_bar.setMaximum(0)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"{name} ({self._progress_pos})")

    # QProgressBar's range is a signed 32-bit int, so raw byte counts overflow on
    # large roms (~4 GiB 3DS titles). Track progress on a fixed permille scale.
    _PROGRESS_SCALE = 1000

    def _on_item_progress(self, downloaded: int, total: int, speed: float) -> None:
        if total > 0:
            self.progress_bar.setMaximum(self._PROGRESS_SCALE)
            self.progress_bar.setValue(int(downloaded * self._PROGRESS_SCALE / total))
        else:
            self.progress_bar.setMaximum(0)  # unknown size → indeterminate
        rate = _human_speed(speed)
        if total > 0:
            size = f"{_human_size(downloaded)} / {_human_size(total)}"
            self.progress_label.setText(
                f"{self._progress_name} ({self._progress_pos}) · {size} · {rate}"
            )
        else:
            self.progress_label.setText(
                f"{self._progress_name} ({self._progress_pos}) · {_human_size(downloaded)} · {rate}"
            )

    def _on_item_error(self, name: str, message: str) -> None:
        # A download failure belongs in the download area, not on the sync dot.
        # The batch keeps going; the label is overwritten by the next item (or
        # cleared by _end_progress), so a transient flash is fine here.
        self.progress_label.setText(f"Failed: {name} — {message}")

    def _on_cancel_clicked(self) -> None:
        if self._download_worker is not None:
            self._download_worker.cancel()
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setText("Cancelling…")

    def _on_batch_finished(self) -> None:
        cancelled = (self._download_worker is not None
                     and self._download_worker.was_cancelled())
        if self._download_worker is not None:
            self._download_worker.deleteLater()
            self._download_worker = None
        self._end_progress()
        self.download_btn.setText("Download")
        self.download_btn.setEnabled(True)
        self.cancel_btn.hide()
        if cancelled:
            # _end_progress hid the label; show a brief note in its place.
            self.progress_label.setText("Download cancelled")
            self.progress_label.show()
        self._refresh_downloaded()
        self.downloads_finished.emit()

    def _end_progress(self) -> None:
        self.progress_bar.hide()
        self.progress_label.hide()
