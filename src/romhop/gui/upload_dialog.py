from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from romhop.local_index import LocalGame
from romhop.upload import UploadCandidates

_SORT_PLATFORM = "Platform"
_SORT_NAME = "Name"


@dataclass
class _Row:
    game: LocalGame
    kind: str  # "ok" | "missing" | "unresolvable"
    platform: dict | None  # resolvable: the platform dict
    slug: str | None  # missing: candidate slug
    reason: str  # unresolvable: human reason
    cb: QCheckBox
    create_btn: QPushButton | None
    container: QWidget  # pre-built row widget, kept alive on _scroll_inner
    resolved_platform: dict | None = None  # set after user creates a missing platform


class UploadDialog(QDialog):
    """Standalone upload picker: opened from Settings after off-thread discovery."""

    def __init__(
        self,
        candidates: UploadCandidates,
        parent=None,
        *,
        upload_action: Callable | None = None,
        create_platform_fn: Callable[[str], dict] | None = None,
        overrides: dict | None = None,
    ):
        super().__init__(parent)
        self._upload_action = upload_action
        self._create_platform_fn = create_platform_fn
        self._overrides = overrides or {}
        self._upload_worker = None
        self._rows: list[_Row] = []

        self.setWindowTitle("Upload local games to RomM")

        layout = QVBoxLayout(self)

        # Summary
        total = (len(candidates.resolvable)
                 + len(candidates.missing_platform)
                 + len(candidates.unresolvable))
        summary = (f"{len(candidates.resolvable)} ready to upload"
                   + (f", {len(candidates.missing_platform)} missing platform"
                      if candidates.missing_platform else "")
                   + (f", {len(candidates.unresolvable)} unresolvable"
                      if candidates.unresolvable else ""))
        layout.addWidget(QLabel(f"{total} unmatched games found. {summary}."))

        # Filter + sort bar
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Platform:"))
        self._platform_combo = QComboBox()
        self._platform_combo.addItem("All")
        all_systems: list[str] = sorted({
            g.system for g, _ in candidates.resolvable
        } | {
            g.system for g, _ in candidates.missing_platform
        } | {
            g.system for g in candidates.unresolvable
        })
        for sys in all_systems:
            self._platform_combo.addItem(sys)
        self._platform_combo.currentTextChanged.connect(self._refresh_rows)
        bar.addWidget(self._platform_combo)

        bar.addSpacing(12)
        bar.addWidget(QLabel("Sort:"))
        self._sort_combo = QComboBox()
        self._sort_combo.addItem(_SORT_PLATFORM)
        self._sort_combo.addItem(_SORT_NAME)
        self._sort_combo.currentTextChanged.connect(self._refresh_rows)
        bar.addWidget(self._sort_combo)
        bar.addStretch(1)
        layout.addLayout(bar)

        # Game list
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll_inner = QWidget()
        self._inner_layout = QVBoxLayout(self._scroll_inner)
        self._inner_layout.setAlignment(Qt.AlignTop)
        self._scroll.setWidget(self._scroll_inner)
        layout.addWidget(self._scroll)

        # Build row data structures (widgets created once, re-parented on refresh)
        self._build_rows(candidates)
        self._refresh_rows()

        # Progress + log (hidden until upload starts)
        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(True)
        self._progress_bar.hide()
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(100)
        self._log.hide()
        layout.addWidget(self._progress_bar)
        layout.addWidget(self._log)

        # Button row
        btn_row = QHBoxLayout()
        self._select_all_btn = QPushButton("Select all")
        self._select_all_btn.clicked.connect(self._select_all)
        self._select_none_btn = QPushButton("Select none")
        self._select_none_btn.clicked.connect(self._select_none)
        btn_row.addWidget(self._select_all_btn)
        btn_row.addWidget(self._select_none_btn)
        btn_row.addStretch(1)
        self._upload_btn = QPushButton("Upload selected")
        self._upload_btn.clicked.connect(self._on_upload_clicked)
        self._ok_btn = QPushButton("Close")
        self._ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._upload_btn)
        btn_row.addWidget(self._ok_btn)
        layout.addLayout(btn_row)

        self.resize(560, 480)

    # --- row construction ---

    def _make_container(self, cb: QCheckBox, create_btn: QPushButton | None) -> QWidget:
        container = QWidget(self._scroll_inner)
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(cb)
        if create_btn is not None:
            create_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            h.addWidget(create_btn)
        h.addStretch(1)
        return container

    def _build_rows(self, candidates: UploadCandidates) -> None:
        for game, platform in candidates.resolvable:
            label = f"{game.system}/{game.game_name}"
            cb = QCheckBox(label, self._scroll_inner)
            cb.setChecked(False)
            container = self._make_container(cb, None)
            row = _Row(
                game=game, kind="ok", platform=platform, slug=None,
                reason="", cb=cb, create_btn=None, container=container,
            )
            self._rows.append(row)

        for game, slug in candidates.missing_platform:
            label = f"{game.system}/{game.game_name}"
            cb = QCheckBox(label, self._scroll_inner)
            cb.setEnabled(False)
            cb.setToolTip(f"Platform '{slug}' not in RomM — click Create to add it")
            btn = QPushButton(f"Create platform '{slug}'", self._scroll_inner)
            container = self._make_container(cb, btn)
            row = _Row(
                game=game, kind="missing", platform=None, slug=slug,
                reason=f"Platform '{slug}' not in RomM", cb=cb, create_btn=btn,
                container=container,
            )
            btn.clicked.connect(lambda _=False, r=row: self._on_create_platform(r))
            self._rows.append(row)

        for game in candidates.unresolvable:
            label = f"{game.system}/{game.game_name}"
            cb = QCheckBox(label, self._scroll_inner)
            cb.setEnabled(False)
            cb.setToolTip("No RomM slug derivable for this system")
            container = self._make_container(cb, None)
            row = _Row(
                game=game, kind="unresolvable", platform=None, slug=None,
                reason="No RomM slug derivable for this system", cb=cb, create_btn=None,
                container=container,
            )
            self._rows.append(row)

    # --- display ---

    def _sorted_rows(self) -> list[_Row]:
        sort = self._sort_combo.currentText()
        if sort == _SORT_NAME:
            return sorted(self._rows, key=lambda r: r.game.game_name.lower())
        # Platform default: group by system, then name within
        return sorted(self._rows, key=lambda r: (r.game.system.lower(), r.game.game_name.lower()))

    def _refresh_rows(self) -> None:
        plat_filter = self._platform_combo.currentText()

        # Remove all items from the layout (widgets stay children of _scroll_inner)
        while self._inner_layout.count():
            self._inner_layout.takeAt(0)

        for row in self._sorted_rows():
            if plat_filter != "All" and row.game.system != plat_filter:
                continue
            self._inner_layout.addWidget(row.container)

    # --- select helpers ---

    def _visible_ok_rows(self) -> list[_Row]:
        """Rows currently shown that can be checked."""
        plat_filter = self._platform_combo.currentText()
        return [
            r for r in self._rows
            if r.kind in ("ok", "missing")
            and r.cb.isEnabled()
            and (plat_filter == "All" or r.game.system == plat_filter)
        ]

    def _select_all(self) -> None:
        for row in self._visible_ok_rows():
            row.cb.setChecked(True)

    def _select_none(self) -> None:
        for row in self._visible_ok_rows():
            row.cb.setChecked(False)

    # --- create platform ---

    def _on_create_platform(self, row: _Row) -> None:
        if self._create_platform_fn is None:
            QMessageBox.warning(self, "Not available", "Create platform is not configured.")
            return
        slug = row.slug or row.game.system
        try:
            new_platform = self._create_platform_fn(slug)
        except Exception as exc:
            QMessageBox.warning(self, "Platform create failed",
                                f"Could not create platform '{slug}': {exc}")
            return
        row.resolved_platform = new_platform
        row.platform = new_platform
        row.kind = "ok"
        row.cb.setEnabled(True)
        row.cb.setChecked(True)
        if row.create_btn is not None:
            row.create_btn.setText(f"✓ Created '{slug}'")
            row.create_btn.setEnabled(False)
        self._log_line(f"✓ Created platform '{slug}' (id {new_platform['id']})")

    # --- upload ---

    def _on_upload_clicked(self) -> None:
        jobs = []
        for row in self._rows:
            if not row.cb.isChecked() or not row.cb.isEnabled():
                continue
            if row.platform is None:
                continue
            pid = row.platform["id"]
            pslug = row.platform.get("slug") or row.platform.get("fs_slug", row.game.system)
            jobs.append((row.game, pid, pslug))

        if not jobs:
            QMessageBox.information(self, "Nothing selected", "Select at least one game to upload.")
            return

        self._upload_btn.setEnabled(False)
        self._upload_btn.setText("Uploading…")
        self._ok_btn.setEnabled(False)
        self._select_all_btn.setEnabled(False)
        self._select_none_btn.setEnabled(False)
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

    # --- worker signals ---

    _PROGRESS_SCALE = 1000

    def _on_item_started(self, index: int, count: int, name: str) -> None:
        self._progress_name = name
        self._progress_pos = f"{index}/{count}"
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
            self._progress_bar.setMaximum(0)
            size = _human_size(bytes_sent)
        self._progress_bar.setFormat(f"{prefix} · {size} · {rate}")

    def _on_item_error(self, name: str, message: str) -> None:
        self._log_line(f"✗ {name}: {message}")

    def _on_activity(self, event) -> None:
        self._log_line(event.message)

    def _on_upload_finished(self) -> None:
        cancelled = (self._upload_worker is not None
                     and self._upload_worker.was_cancelled())
        if self._upload_worker is not None:
            self._upload_worker.deleteLater()
            self._upload_worker = None
        self._progress_bar.hide()
        if cancelled:
            self._upload_btn.setText("Cancelled")
        else:
            self._upload_btn.setText("Upload complete")
        self._ok_btn.setEnabled(True)
        self._select_all_btn.setEnabled(True)
        self._select_none_btn.setEnabled(True)

    def _log_line(self, text: str) -> None:
        self._log.show()
        self._log.appendPlainText(text)
