from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from dataclasses import replace

logger = logging.getLogger(__name__)

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from romhop import config
from romhop.config import Settings
from romhop.gui import theme
from romhop.gui.tray import SYNC_DOT_COLORS, TrayIcon
from romhop.gui.filter_bar import FilterBar
from romhop.gui.library_view import LibraryView, platforms_from_roms
from romhop.gui.settings_view import SettingsView
from romhop.gui.setup_wizard import SetupWizard
from romhop.gui.detail_panel import DetailPanel
from romhop.gui.scan_result_dialog import ScanResultDialog
from romhop.gui.pull_conflict_dialog import PullConflictDialog
from romhop.gui.activity_hub import ActivityHub
from romhop.gui.activity_log import ActivityLogView
from romhop.gui.toast import ToastManager
from romhop.gui.workers import CallableWorker, DownloadWorker, PullWorker, SyncWorker, UpdateWorker
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


class MainWindow(QWidget):
    """Layout A: top search row, library/settings stack, pinned bottom bar."""

    downloads_finished = Signal()
    # Fires whenever the sync indicator text changes; lets tests await state.
    _sync_status_changed = Signal(str)

    def __init__(self, settings: Settings, parent=None, *,
                 rom_provider=None, download_action=None, scan_action=None,
                 sync_watch_fn=None, persist_settings=None, cover_provider=None,
                 screenshot_provider=None, platform_label=None, platform_names=None,
                 apply_token=None,
                 apply_settings=None, quit_fn=None, confirm_no_tray=None,
                 validate_fn=None, detect_retroarch_fn=None, recreate_client=None,
                 update_check_fn=None, update_apply_fn=None, relaunch_fn=None,
                 open_log_dir_fn=None, export_logs_fn=None, detail_provider=None,
                 open_in_romm=None, open_folder=None, pull_action=None,
                 upload_action=None, list_platforms_fn=None, create_platform_fn=None):
        super().__init__(parent)
        self._settings = settings
        self._apply_token = apply_token
        self._apply_settings = apply_settings
        self._validate_fn = validate_fn
        self._detect_retroarch_fn = detect_retroarch_fn
        self._recreate_client = recreate_client
        self._rom_provider = rom_provider
        self._download_action = download_action
        self._cover_provider = cover_provider
        self._sync_watch_fn = sync_watch_fn
        self._platform_names = platform_names
        self._persist_settings = persist_settings or config.save_settings
        self._scan_action = scan_action
        self._update_check_fn = update_check_fn
        self._update_apply_fn = update_apply_fn
        self._relaunch_fn = relaunch_fn
        self._detail_provider = detail_provider
        self._open_in_romm_fn = open_in_romm
        self._open_folder_fn = open_folder
        self._pull_action = pull_action
        self._upload_action = upload_action
        self._list_platforms_fn = list_platforms_fn
        self._create_platform_fn = create_platform_fn
        self._pull_workers: set = set()
        self._bulk_pull_worker = None
        self._pending_update = None
        self._check_worker = None
        self._apply_worker = None
        self._download_worker = None
        self._scan_worker = None
        self._sync_worker = None
        self._activity_hub = ActivityHub(self)
        self._activity_log_connected = False
        self._toast_manager = ToastManager(self)
        self._activity_hub.event.connect(self._toast_manager.post)
        self._activity_hub.event.connect(self._on_activity_desktop_notify)
        self._progress_name = ""
        self._progress_pos = ""
        self.tray = None
        self._quitting = False
        self._tray_hint_shown = False
        self._quit_fn = quit_fn or (lambda: QApplication.instance().quit())
        self._confirm_no_tray = confirm_no_tray or self._default_no_tray_notice
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
        self.settings_view = SettingsView(
            settings,
            open_log_dir_fn=open_log_dir_fn,
            export_logs_fn=export_logs_fn,
        )
        self.settings_view.saved.connect(self._on_settings_saved)
        self.settings_view.cancelled.connect(self.show_library)
        self.settings_view.scan_requested.connect(self.run_scan)
        self.settings_view.token_changed.connect(self._on_token_changed)
        self.settings_view.setup_requested.connect(self.run_setup_wizard)
        self.settings_view.update_check_requested.connect(self.check_for_updates)
        if update_check_fn is None:
            self.settings_view.update_check_btn.hide()
        self.activity_log = ActivityLogView()
        self.stack = QStackedWidget()
        self.stack.addWidget(self.library)        # index 0
        self.stack.addWidget(self.settings_view)  # index 1
        self.stack.addWidget(self.activity_log)   # index 2

        # Bottom bar: selection count + download + sync status.
        self.bottom = QFrame()
        self.bottom.setObjectName("BottomBar")
        self._sel_label = QLabel("0 selected")
        self.download_btn = QPushButton("Download")
        self.pull_btn = QPushButton("Pull saves")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("CancelDownload")
        self.cancel_btn.hide()
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        # Single shared progress bar: the current game in the batch. Hidden when
        # idle so the bottom bar stays clean until a download is running.
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("DownloadProgress")
        self.progress_bar.setFixedWidth(360)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("StatusDim")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # Don't let the fallback style's font metrics under-allocate width and
        # clip the leading characters of the game name (frozen-build TASK-005).
        self.progress_label.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred
        )
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
        self.uncheck_btn = QPushButton("Uncheck")
        self.uncheck_btn.clicked.connect(self.library.clear_selection)
        self.activity_btn = QPushButton("Activity")
        self.activity_btn.setObjectName("ActivityButton")
        self.activity_btn.clicked.connect(self.toggle_activity_log)
        bottom_row = QHBoxLayout(self.bottom)
        bottom_row.addWidget(self._sel_label)
        bottom_row.addWidget(self.uncheck_btn)
        bottom_row.addWidget(self.download_btn)
        bottom_row.addWidget(self.pull_btn)
        bottom_row.addWidget(self.cancel_btn)
        bottom_row.addWidget(self.progress_bar)
        bottom_row.addWidget(self.progress_label)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.activity_btn)
        bottom_row.addWidget(self.sync_button)
        # Paint the dot grey for the initial idle state.
        self.set_sync_status(self._sync_state)
        # setChecked above fired no signal (it ran pre-connect), so a persisted
        # sync_enabled=True would leave the worker stopped and the dot grey
        # despite the toggle reading on. Kick off the worker now to match it.
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = TrayIcon(self)
            self.tray.show_requested.connect(self.toggle_window_visibility)
            self.tray.sync_toggled.connect(self.sync_button.setChecked)
            self.tray.quit_requested.connect(self.quit_app)
            self.tray.set_sync_checked(settings.sync_enabled)
            self.tray.set_status(self._sync_state, self.sync_state())
            self.tray.show()
        if settings.sync_enabled:
            self._reconcile_sync(True)
        if self.tray is None:
            self.settings_view.set_desktop_notifications_available(
                False, "No system tray available — OS notifications cannot be shown")

        self.library.selection_changed.connect(self._on_selection)
        self.download_btn.clicked.connect(self.download_selected)
        self.pull_btn.clicked.connect(self._pull_selected)

        # Update banner: in-layout, hidden until a newer version is found.
        self.update_banner = QLabel("")
        self.update_banner.setObjectName("UpdateBanner")
        self.update_banner.hide()
        self._update_btn = QPushButton("Update")
        self._update_btn.setObjectName("UpdateNow")
        self._update_btn.clicked.connect(self._on_update_clicked)
        self._update_btn.hide()
        self._update_later_btn = QPushButton("Later")
        self._update_later_btn.clicked.connect(self._hide_update_bar)
        self._update_later_btn.hide()
        update_bar_row = QHBoxLayout()
        update_bar_row.addWidget(self.update_banner)
        update_bar_row.addWidget(self._update_btn)
        update_bar_row.addWidget(self._update_later_btn)
        update_bar_row.addStretch(1)

        self.detail_panel = DetailPanel(
            detail_provider=detail_provider,
            cover_provider=cover_provider,
            screenshot_provider=screenshot_provider,
            platform_label=platform_label,
        )
        self.library.tile_activated.connect(self._on_tile_activated)
        self.library.action_requested.connect(self._dispatch_action)
        self.detail_panel.download_requested.connect(
            lambda r: self._dispatch_action("download", r))
        self.detail_panel.pull_requested.connect(
            lambda r: self._dispatch_action("pull", r))
        self.detail_panel.open_romm_requested.connect(
            lambda r: self._dispatch_action("open_romm", r))
        self.detail_panel.open_folder_requested.connect(
            lambda r: self._dispatch_action("open_folder", r))
        content = QHBoxLayout()
        content.addWidget(self.stack, 1)
        content.addWidget(self.detail_panel, 0)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.filter_bar)
        layout.addLayout(content, 1)
        layout.addLayout(update_bar_row)
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
        self._disconnect_activity_log()
        self.settings_view.reset()
        self.settings_view.setFocus()
        self.filter_bar.hide()
        self.uncheck_btn.hide()
        self.download_btn.hide()
        self.pull_btn.hide()
        self.search.clear()
        self.stack.setCurrentIndex(1)

    def show_library(self) -> None:
        self._disconnect_activity_log()
        self.filter_bar.show()
        self.uncheck_btn.show()
        self.download_btn.show()
        self.pull_btn.show()
        self.search.clear()
        self.stack.setCurrentIndex(0)

    def show_activity_log(self) -> None:
        self.activity_log.load(self._activity_hub.history())
        if not self._activity_log_connected:
            self._activity_hub.event.connect(self.activity_log.append_event)
            self._activity_log_connected = True
        self.filter_bar.hide()
        self.uncheck_btn.hide()
        self.download_btn.hide()
        self.pull_btn.hide()
        self.search.clear()
        self.stack.setCurrentIndex(2)

    def _disconnect_activity_log(self) -> None:
        if self._activity_log_connected:
            self._activity_hub.event.disconnect(self.activity_log.append_event)
            self._activity_log_connected = False

    def toggle_settings(self) -> None:
        # Gear acts as a toggle: into settings, or back out (discarding edits).
        if self.current_view_name() == "settings":
            self.settings_view.reset()
            self.show_library()
        else:
            self.show_settings()

    def toggle_activity_log(self) -> None:
        if self.current_view_name() == "activity":
            self.show_library()
        else:
            self.show_activity_log()

    def current_view_name(self) -> str:
        idx = self.stack.currentIndex()
        if idx == 0:
            return "library"
        if idx == 1:
            return "settings"
        return "activity"

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
        color = SYNC_DOT_COLORS[_sync_state_class(state)]
        self.sync_button.setStyleSheet(f"#SyncButton {{ color: {color}; }}")
        self.sync_button.setToolTip(f"Sync: {state}")
        if self.tray is not None:
            self.tray.set_status(state, _sync_state_class(state))
        self._sync_status_changed.emit(state)

    # --- window visibility / tray lifecycle ---
    def show_and_raise(self) -> None:
        # Restore + focus, used by the tray and by a second `romhop gui` launch.
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def toggle_window_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show_and_raise()

    def _default_no_tray_notice(self) -> None:
        QMessageBox.information(
            self, "romhop",
            "No system tray is available on this desktop. The window will hide "
            "and keep syncing in the background. Relaunch `romhop gui` to bring "
            "it back.")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._toast_manager.reposition()

    def _on_activity_desktop_notify(self, activity_event) -> None:
        if not self._settings.desktop_notifications:
            return
        if self.tray is None:
            return
        if QApplication.activeWindow() is self and self.isVisible():
            return
        title = "romhop — Error" if activity_event.is_error else "romhop"
        icon = (QSystemTrayIcon.MessageIcon.Critical if activity_event.is_error
                else QSystemTrayIcon.MessageIcon.Information)
        self.tray.showMessage(title, activity_event.message, icon, 4000)

    def closeEvent(self, event: QCloseEvent) -> None:
        # A real quit (via the tray) flows through here with _quitting set.
        if self._quitting:
            self._shutdown_sync()
            super().closeEvent(event)
            return
        if self.tray is not None:
            event.ignore()
            self.hide()
            if not self._tray_hint_shown:
                msg = ("Still running — save-sync active." if self._settings.sync_enabled
                       else "Still running in the tray.")
                self.tray.showMessage("romhop", msg)
                self._tray_hint_shown = True
            return
        # No tray: warn once, then hide and keep running headless.
        self._confirm_no_tray()
        event.ignore()
        self.hide()

    def quit_app(self) -> None:
        self._quitting = True
        self._shutdown_sync()
        self._shutdown_update_workers()
        self._quit_fn()

    def _shutdown_sync(self) -> None:
        if self._sync_worker is not None:
            self._sync_worker.stop()
            self._sync_worker.wait(5000)

    def _shutdown_update_workers(self) -> None:
        for attr in ("_check_worker", "_apply_worker"):
            worker = getattr(self, attr)
            if worker is not None:
                worker.quit()
                worker.wait()
                worker.deleteLater()
                setattr(self, attr, None)

    # --- sync controls ---
    def _on_sync_toggled(self, enabled: bool) -> None:
        # Bottom-bar toggle: persist the intent (survives restart), keep the
        # settings menu in lockstep so the two never disagree, then reconcile.
        self._settings = replace(self._settings, sync_enabled=enabled)
        self._persist_settings(self._settings)
        if self._apply_settings is not None:
            self._apply_settings(self._settings)
        self.settings_view.set_sync_enabled(enabled)
        if self.tray is not None:
            self.tray.set_sync_checked(enabled)
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
        from PySide6.QtCore import Qt
        worker.activity.connect(self._activity_hub.post, Qt.QueuedConnection)
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

    def _on_token_changed(self, token: str) -> None:
        # Push the new token onto the live client and refresh the library so it
        # takes effect without a restart. Library load failures are tolerated
        # the same way startup is.
        if self._apply_token is not None:
            self._apply_token(token)
        try:
            self.load_library()
        except Exception as exc:  # noqa: BLE001 - keep the window alive
            self.set_sync_status(f"library load failed: {exc}")

    def _on_settings_saved(self) -> None:
        # Settings already persisted itself; adopt its Settings so our in-memory
        # copy doesn't go stale, then mirror the sync flag onto the bottom
        # button WITHOUT re-persisting (block its signal) and reconcile.
        self._settings = self.settings_view.current_settings()
        # Push the fresh settings into the live backend closures (download_action,
        # sync_watch_fn) so changes like the download limit or roms_root take
        # effect immediately instead of only after a restart.
        if self._apply_settings is not None:
            self._apply_settings(self._settings)
        enabled = self._settings.sync_enabled
        self.sync_button.blockSignals(True)
        self.sync_button.setChecked(enabled)
        self.sync_button.blockSignals(False)
        if self.tray is not None:
            self.tray.set_sync_checked(enabled)
        self._reconcile_sync(enabled)

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
        self.detail_panel.set_downloaded(ids)

    def _on_tile_activated(self, rom) -> None:
        self.detail_panel.set_rom(rom)

    def run_scan(self) -> None:
        # One scan at a time; ignore re-clicks while a worker is live.
        if self._scan_action is None or self._scan_worker is not None:
            return
        self.settings_view.set_scanning(True)
        settings = self._settings
        worker = CallableWorker(lambda: self._scan_action(settings))
        worker.done.connect(self._on_scan_done)
        worker.error.connect(self._on_scan_error)
        worker.finished.connect(self._on_scan_finished)
        self._scan_worker = worker
        worker.start()

    def _build_setup_wizard(self) -> SetupWizard:
        wiz = SetupWizard(
            validate_fn=self._validate_fn,
            detect_retroarch_fn=self._detect_retroarch_fn,
            initial_settings=self._settings,
            parent=self,
        )
        wiz.completed.connect(self._on_setup_complete)
        return wiz

    def run_setup_wizard(self) -> None:
        self._build_setup_wizard().exec()

    def _on_setup_complete(self, settings, do_scan: bool) -> None:
        self._settings = settings
        if self._recreate_client is not None:
            self._recreate_client(settings)
        self.settings_view.load(settings)
        self.show_library()
        try:
            self.load_library()
        except Exception as exc:  # noqa: BLE001 - keep window alive
            self.set_sync_status(f"library load failed: {exc}")
        if do_scan:
            self.run_scan()

    def _on_scan_done(self, result) -> None:
        self.settings_view.set_scanning(False)
        ScanResultDialog(
            result, self,
            upload_action=self._upload_action,
            list_platforms_fn=self._list_platforms_fn,
            create_platform_fn=self._create_platform_fn,
            overrides=self._settings.platform_overrides,
        ).exec()

    def _on_scan_error(self, message: str) -> None:
        self.settings_view.set_scanning(False)
        QMessageBox.critical(self, "Scan failed", message)

    def _on_scan_finished(self) -> None:
        if self._scan_worker is not None:
            self._scan_worker.deleteLater()
            self._scan_worker = None

    def _start_download(self, roms: list) -> None:
        if self._download_action is None or not roms or self._download_worker is not None:
            return
        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading…")
        self.cancel_btn.show()
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("Cancel")
        self._begin_progress()
        from PySide6.QtCore import Qt
        worker = DownloadWorker(roms, self._download_action)
        worker.item_started.connect(self._on_item_started)
        worker.item_progress.connect(self._on_item_progress)
        worker.item_error.connect(self._on_item_error)
        worker.activity.connect(self._activity_hub.post, Qt.QueuedConnection)
        worker.finished.connect(self._on_batch_finished)
        self._download_worker = worker
        worker.start()

    def download_selected(self) -> None:
        if self._download_action is None:
            self.downloads_finished.emit()
            return
        selected = self.library.selected_roms()
        if not selected:
            self.downloads_finished.emit()
            return
        self._start_download(selected)

    def _dispatch_action(self, name: str, rom) -> None:
        if name == "download":
            self._start_download([rom])
        elif name == "pull":
            self._pull_one(rom)
        elif name == "open_romm":
            if self._open_in_romm_fn is not None:
                self._open_in_romm_fn(rom)
        elif name == "open_folder":
            if self._open_folder_fn is not None:
                self._open_folder_fn(rom)

    def _pull_one(self, rom) -> None:
        if self._pull_action is None:
            return
        worker = PullWorker(lambda on_conflict: self._pull_action([rom], on_conflict))
        worker.conflict.connect(self._on_pull_conflict)
        worker.done.connect(self._on_pull_done)
        worker.failed.connect(self._on_pull_failed)
        worker.finished.connect(lambda w=worker: self._pull_workers.discard(w))
        self._pull_workers.add(worker)
        worker.start()

    def _pull_selected(self) -> None:
        if self._pull_action is None:
            return
        # Ignore the click while a bulk pull is already running: the button is
        # the only entry point, so one live bulk worker is enough of a guard.
        if self._bulk_pull_worker is not None:
            return
        selected = self.library.selected_roms()
        if not selected:
            return
        self.pull_btn.setText("Pulling…")
        self.pull_btn.setEnabled(False)
        worker = PullWorker(
            lambda on_conflict: self._pull_action(selected, on_conflict))
        worker.conflict.connect(self._on_pull_conflict)
        worker.done.connect(self._on_pull_done)
        worker.failed.connect(self._on_pull_failed)
        worker.finished.connect(lambda w=worker: self._on_bulk_pull_finished(w))
        self._pull_workers.add(worker)
        self._bulk_pull_worker = worker
        worker.start()

    def _on_bulk_pull_finished(self, worker) -> None:
        self._pull_workers.discard(worker)
        self._bulk_pull_worker = None
        self.pull_btn.setText("Pull saves")
        self.pull_btn.setEnabled(True)

    def _on_pull_conflict(self, item, local_path, local_mtime) -> None:
        worker = self.sender()
        take = PullConflictDialog.ask(item.file_name, item.remote_updated,
                                      local_mtime, self)
        worker.resolve_conflict(take)

    def _on_pull_done(self, summary: dict) -> None:
        w = summary.get("written", 0)
        s = summary.get("skipped", 0)
        k = summary.get("kept", 0)
        f = summary.get("failed", 0)
        m = summary.get("missing", 0)
        text = f"Written: {w}  Skipped: {s}  Kept: {k}"
        if m:
            text += f"  Missing on RomM: {m}"
        if f:
            text += f"  Failed: {f}"
        QMessageBox.information(self, "Pull complete", text)

    def _on_pull_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Pull failed", message)

    # --- download progress UI ---
    def _begin_progress(self) -> None:
        self.progress_bar.setMaximum(0)  # busy until the first byte count lands
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("")
        self.progress_bar.show()
        self.progress_label.hide()

    def _on_item_started(self, index: int, count: int, name: str) -> None:
        self._progress_name = name
        self._progress_pos = f"{index}/{count}"
        # New game in the batch: bar goes indeterminate until its total arrives.
        self.progress_bar.setMaximum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"{name} ({self._progress_pos})")

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
            self.progress_bar.setFormat(
                f"{self._progress_name} ({self._progress_pos}) · {size} · {rate}"
            )
        else:
            self.progress_bar.setFormat(
                f"{self._progress_name} ({self._progress_pos}) · {_human_size(downloaded)} · {rate}"
            )

    def _on_item_error(self, name: str, message: str) -> None:
        # A download failure belongs in the download area, not on the sync dot.
        # The batch keeps going; the label is overwritten by the next item (or
        # cleared by _end_progress), so a transient flash is fine here.
        self.progress_bar.setFormat(f"Failed: {name} — {message}")

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

    # --- update flow ---

    def check_for_updates(self) -> None:
        if self._update_check_fn is None:
            return
        if self._check_worker is not None:
            self._check_worker.quit()
            self._check_worker.wait()
            self._check_worker.deleteLater()
            self._check_worker = None
        self._check_worker = UpdateWorker(check_fn=self._update_check_fn)
        self._check_worker.available.connect(self._on_update_available)
        self._check_worker.failed.connect(self._on_update_failed)
        self._check_worker.start()

    def _hide_update_bar(self) -> None:
        self.update_banner.hide()
        self._update_btn.hide()
        self._update_later_btn.hide()

    def _on_update_available(self, info) -> None:
        if info is None:
            self._hide_update_bar()
            return
        self._pending_update = info
        self.update_banner.setText(f"v{info.version} available")
        self.update_banner.show()
        self._update_btn.show()
        self._update_later_btn.show()

    def _on_update_clicked(self) -> None:
        self._hide_update_bar()
        if self._apply_worker is not None:
            self._apply_worker.quit()
            self._apply_worker.wait()
            self._apply_worker.deleteLater()
            self._apply_worker = None
        self._apply_worker = UpdateWorker(
            apply_fn=self._update_apply_fn, info=self._pending_update
        )
        self._apply_worker.progress.connect(self._on_update_progress)
        self._apply_worker.applied.connect(self._on_update_applied)
        self._apply_worker.failed.connect(self._on_update_failed)
        self._apply_worker.start()

    def _on_update_progress(self, done: int, total: int) -> None:
        if total > 0:
            self.progress_bar.setMaximum(self._PROGRESS_SCALE)
            self.progress_bar.setValue(int(done * self._PROGRESS_SCALE / total))
        else:
            self.progress_bar.setMaximum(0)
        self.progress_bar.setFormat("Updating…")
        self.progress_bar.show()

    def _on_update_applied(self) -> None:
        self.progress_bar.hide()
        QMessageBox.information(self, "Update ready", "Restart romhop to finish updating.")
        if self._relaunch_fn is not None:
            self._relaunch_fn()

    def _on_update_failed(self, msg: str) -> None:
        logger.warning("Update failed: %s", msg)
        self.set_sync_status(f"update error: {msg}")
