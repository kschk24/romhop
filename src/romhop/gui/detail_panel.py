from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from romhop.gui.workers import DetailWorker


def _human_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


class DetailPanel(QWidget):
    """Right-docked panel showing one game's metadata and per-game action buttons."""

    download_requested = Signal(object)
    pull_requested = Signal(object)
    open_romm_requested = Signal(object)
    open_folder_requested = Signal(object)
    closed = Signal()
    _detail_loaded = Signal()  # test hook: detail fetch finished

    def __init__(self, parent=None, *, detail_provider=None):
        super().__init__(parent)
        self._detail_provider = detail_provider
        self._rom = None
        self._downloaded_ids: set[int] = set()
        self._cache: dict[int, object] = {}
        self._worker = None
        self._workers: set = set()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("DetailClose")
        close_btn.clicked.connect(self._on_close)
        top = QHBoxLayout()
        top.addStretch(1)
        top.addWidget(close_btn, 0)

        self._name_label = QLabel("")
        self._name_label.setObjectName("DetailName")
        self._name_label.setWordWrap(True)
        self._platform_label = QLabel("")
        self._meta_label = QLabel("")
        self._meta_label.setWordWrap(True)
        self._summary_label = QLabel("")
        self._summary_label.setWordWrap(True)
        self._files_label = QLabel("")
        self._files_label.setWordWrap(True)

        self._download_btn = QPushButton("Download")
        self._pull_btn = QPushButton("Pull savegames")
        self._romm_btn = QPushButton("Open in RomM")
        self._folder_btn = QPushButton("Open containing folder")
        self._download_btn.clicked.connect(lambda: self._emit(self.download_requested))
        self._pull_btn.clicked.connect(lambda: self._emit(self.pull_requested))
        self._romm_btn.clicked.connect(lambda: self._emit(self.open_romm_requested))
        self._folder_btn.clicked.connect(lambda: self._emit(self.open_folder_requested))

        box = QVBoxLayout(self)
        box.addLayout(top)
        box.addWidget(self._name_label)
        box.addWidget(self._platform_label)
        box.addWidget(self._meta_label)
        box.addWidget(self._summary_label)
        box.addWidget(self._files_label)
        for btn in (self._download_btn, self._pull_btn, self._romm_btn, self._folder_btn):
            box.addWidget(btn)
        box.addStretch(1)
        self.hide()

    def set_downloaded(self, ids: set[int]) -> None:
        self._downloaded_ids = set(ids)

    def _emit(self, signal) -> None:
        if self._rom is not None:
            signal.emit(self._rom)

    def _on_close(self) -> None:
        self.hide()
        self.closed.emit()

    def set_rom(self, rom) -> None:
        self._rom = rom
        downloaded = rom.id in self._downloaded_ids
        self._name_label.setText(rom.name)
        self._platform_label.setText(rom.platform_name or rom.platform_slug)
        self._files_label.setText("\n".join(rom.file_names))
        self._download_btn.setText("Re-download" if downloaded else "Download")
        self._folder_btn.setEnabled(downloaded)
        self._meta_label.setText("")
        self._summary_label.setText("Loading details…")
        self.show()
        cached = self._cache.get(rom.id)
        if cached is not None:
            self._apply_detail(cached)
            self._detail_loaded.emit()
            return
        if self._detail_provider is None:
            self._summary_label.setText("")
            return
        captured_rom = rom
        worker = DetailWorker(lambda: self._detail_provider(captured_rom))
        worker.loaded.connect(lambda d, rid=rom.id: self._on_loaded(rid, d))
        worker.failed.connect(self._on_failed)
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        self._workers.add(worker)
        self._worker = worker
        worker.start()

    def _on_loaded(self, rom_id: int, detail) -> None:
        self._cache[rom_id] = detail
        if self._rom is not None and self._rom.id == rom_id:
            self._apply_detail(detail)
        self._detail_loaded.emit()

    def _on_failed(self, message: str) -> None:
        self._summary_label.setText("Couldn't load details.")
        self._detail_loaded.emit()

    def _apply_detail(self, detail) -> None:
        bits = []
        if getattr(detail, "release_date", None):
            bits.append(detail.release_date)
        if getattr(detail, "genres", None):
            bits.append(", ".join(detail.genres))
        if getattr(detail, "file_size", None):
            bits.append(_human_size(detail.file_size))
        self._meta_label.setText(" · ".join(bits))
        self._summary_label.setText(getattr(detail, "summary", "") or "")
