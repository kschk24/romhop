from __future__ import annotations

import threading
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from romhop.local_index import LocalGame, MatchResult


class ScanResultDialog(QDialog):
    """Reports a scan outcome plus an optional upload picker for unmatched games."""

    def __init__(
        self,
        result: MatchResult,
        parent=None,
        *,
        upload_action: Callable | None = None,
        list_platforms_fn: Callable[[], list[dict]] | None = None,
        create_platform_fn: Callable[[str], dict] | None = None,
        overrides: dict | None = None,
    ):
        """
        upload_action(game, platform_id, platform_slug, on_progress, stop_event, on_event)
            — called per game in the UploadWorker.
        list_platforms_fn() → list[dict]  — fetch RomM platform list (called on main thread).
        create_platform_fn(slug) → dict   — create a missing RomM platform.
        overrides                          — settings.platform_overrides for resolution.
        """
        super().__init__(parent)
        self._result = result
        self._upload_action = upload_action
        self._list_platforms_fn = list_platforms_fn
        self._create_platform_fn = create_platform_fn
        self._overrides = overrides or {}
        self._checkboxes: dict[str, QCheckBox] = {}  # game_key → checkbox
        self._game_by_key: dict[str, LocalGame] = {}
        self._upload_worker = None
        self.setWindowTitle("Scan results")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.summary_text()))

        if upload_action is None:
            # Original behavior: one plain-text widget for everything.
            detail_body = self.detail_text()
            if detail_body:
                detail = QPlainTextEdit(detail_body)
                detail.setReadOnly(True)
                layout.addWidget(detail)
        else:
            # Upload mode: picker for unmatched, plain text for collisions.
            if result.unmatched:
                layout.addWidget(self._build_picker())
            if result.collisions:
                lines = ["Collisions (saves disambiguated by core at sync time):"]
                for c in result.collisions:
                    lines.append(f"  {c.basename}: {c.rom_ids}")
                col_widget = QPlainTextEdit("\n".join(lines))
                col_widget.setReadOnly(True)
                layout.addWidget(col_widget)

        # Progress + log area (shown during upload).
        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(True)
        self._progress_bar.hide()
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(120)
        self._log.hide()
        layout.addWidget(self._progress_bar)
        layout.addWidget(self._log)

        # Button row.
        btn_row = QHBoxLayout()
        if upload_action is not None and result.unmatched:
            self._upload_btn = QPushButton("Upload selected")
            self._upload_btn.clicked.connect(self._on_upload_clicked)
            self._select_all_btn = QPushButton("Select all")
            self._select_all_btn.clicked.connect(self._select_all)
            btn_row.addWidget(self._select_all_btn)
            btn_row.addWidget(self._upload_btn)
        btn_row.addStretch(1)
        self._ok_btn = QPushButton("OK")
        self._ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._ok_btn)
        layout.addLayout(btn_row)

    def _build_picker(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(QLabel("Unmatched games (select to upload):"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setAlignment(Qt.AlignTop)
        for g in self._result.unmatched:
            key = f"{g.system}/{g.game_name}"
            cb = QCheckBox(key)
            self._checkboxes[key] = cb
            self._game_by_key[key] = g
            inner_layout.addWidget(cb)
        scroll.setWidget(inner)
        vbox.addWidget(scroll)
        return container

    def _select_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.setChecked(True)

    def _on_upload_clicked(self) -> None:
        selected_keys = [k for k, cb in self._checkboxes.items() if cb.isChecked()]
        if not selected_keys:
            return
        selected_games = [self._game_by_key[k] for k in selected_keys]

        # Resolve platforms synchronously on main thread.
        jobs = self._resolve_platforms(selected_games)
        if not jobs:
            return

        # Disable controls during upload.
        self._upload_btn.setEnabled(False)
        self._upload_btn.setText("Uploading…")
        self._ok_btn.setEnabled(False)
        self._progress_bar.setMaximum(0)
        self._progress_bar.setFormat("Uploading…")
        self._progress_bar.show()
        self._log.show()

        from romhop.gui.workers import UploadWorker
        from PySide6.QtCore import Qt as _Qt
        worker = UploadWorker(jobs, self._upload_action)
        worker.item_started.connect(self._on_item_started)
        worker.item_progress.connect(self._on_item_progress)
        worker.item_error.connect(self._on_item_error)
        worker.activity.connect(self._on_activity, _Qt.QueuedConnection)
        worker.finished.connect(self._on_upload_finished)
        self._upload_worker = worker
        worker.start()

    def _resolve_platforms(
        self, games: list[LocalGame]
    ) -> list[tuple]:
        """Resolve RomM platform ids for each game. Returns a list of job tuples.

        For missing platforms, prompts user to create them. Games whose platform
        can't be resolved are skipped (with an explanation in the log).
        """
        from romhop.platform_resolve import invert_to_slugs, resolve_platform

        jobs: list[tuple] = []

        romm_platforms: list[dict] = []
        if self._list_platforms_fn is not None:
            try:
                romm_platforms = self._list_platforms_fn()
            except Exception as exc:
                QMessageBox.critical(self, "Platform list failed",
                                     f"Could not fetch RomM platforms: {exc}")
                return []

        # Collect unique systems we need to resolve.
        systems_needed = {g.system for g in games}
        resolved: dict[str, tuple[int, str] | None] = {}  # system → (id, slug) or None

        for system in systems_needed:
            platform = resolve_platform(system, romm_platforms, self._overrides)
            if platform is not None:
                resolved[system] = (platform["id"], platform.get("slug") or platform.get("fs_slug", system))
                continue

            # Platform missing — offer to create it.
            candidate_slugs = invert_to_slugs(system, self._overrides)
            slug = candidate_slugs[0] if candidate_slugs else system

            if self._create_platform_fn is None:
                self._log_line(f"⚠ {system}: platform not found in RomM — skipped")
                resolved[system] = None
                continue

            answer = QMessageBox.question(
                self,
                "Platform not found",
                f"Platform '{slug}' for system '{system}' does not exist in RomM.\n"
                f"Create it now?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                self._log_line(f"⚠ {system}: platform skipped by user")
                resolved[system] = None
                continue

            try:
                new_platform = self._create_platform_fn(slug)
                resolved[system] = (
                    new_platform["id"],
                    new_platform.get("slug") or new_platform.get("fs_slug", slug),
                )
                self._log_line(f"✓ Created platform '{slug}' (id {new_platform['id']})")
            except Exception as exc:
                QMessageBox.warning(self, "Platform create failed",
                                    f"Could not create platform '{slug}': {exc}")
                resolved[system] = None

        for game in games:
            resolution = resolved.get(game.system)
            if resolution is None:
                self._log_line(f"✗ {game.game_name}: no platform — skipped")
            else:
                platform_id, platform_slug = resolution
                jobs.append((game, platform_id, platform_slug))

        return jobs

    def _log_line(self, text: str) -> None:
        self._log.show()
        self._log.appendPlainText(text)

    # QProgressBar's range is a signed 32-bit int, so raw byte counts overflow on
    # large roms. Track progress on a fixed permille scale (mirrors download bar).
    _PROGRESS_SCALE = 1000

    def _on_item_started(self, index: int, count: int, name: str) -> None:
        self._progress_name = name
        self._progress_pos = f"{index}/{count}"
        # New game in the batch: bar goes indeterminate until its total arrives.
        self._progress_bar.setMaximum(0)
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat(f"Uploading {name} ({self._progress_pos})…")

    def _on_item_progress(self, bytes_sent: int, total: int, speed: float) -> None:
        from romhop.gui.main_window import _human_size, _human_speed
        name = getattr(self, "_progress_name", "")
        pos = getattr(self, "_progress_pos", "")
        prefix = f"Uploading {name} ({pos})" if name else "Uploading…"
        rate = _human_speed(speed)
        if total > 0:
            self._progress_bar.setMaximum(self._PROGRESS_SCALE)
            self._progress_bar.setValue(int(bytes_sent * self._PROGRESS_SCALE / total))
            size = f"{_human_size(bytes_sent)} / {_human_size(total)}"
        else:
            self._progress_bar.setMaximum(0)  # unknown size → indeterminate
            size = _human_size(bytes_sent)
        self._progress_bar.setFormat(f"{prefix} · {size} · {rate}")

    def _on_item_error(self, name: str, message: str) -> None:
        self._log_line(f"✗ {name}: {message}")

    def _on_activity(self, event) -> None:
        self._log_line(event.message)
        # Remove uploaded game from picker.
        for key, game in list(self._game_by_key.items()):
            if game.game_name in event.message and not event.is_error:
                if key in self._checkboxes:
                    self._checkboxes[key].hide()

    def _on_upload_finished(self) -> None:
        cancelled = (self._upload_worker is not None
                     and self._upload_worker.was_cancelled())
        if self._upload_worker is not None:
            self._upload_worker.deleteLater()
            self._upload_worker = None
        self._progress_bar.hide()
        if cancelled:
            n_remaining = sum(1 for cb in self._checkboxes.values() if cb.isVisible())
            self._upload_btn.setText("Cancelled")
            self._log_line(f"batch cancelled, {n_remaining} not uploaded")
        else:
            self._upload_btn.setText("Upload complete")
        self._ok_btn.setEnabled(True)

    def summary_text(self) -> str:
        r = self._result
        return (f"{len(r.matched)} matched, {len(r.unmatched)} unmatched, "
                f"{len(r.collisions)} collisions")

    def detail_text(self) -> str:
        r = self._result
        lines = []
        if r.unmatched:
            lines.append("Unmatched (no RomM rom found — rescan in RomM or rename):")
            for g in r.unmatched:
                lines.append(f"  {g.system}/{g.game_name}")
        if r.collisions:
            lines.append("Collisions (saves disambiguated by core at sync time):")
            for c in r.collisions:
                lines.append(f"  {c.basename}: {c.rom_ids}")
        return "\n".join(lines)
