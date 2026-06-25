from __future__ import annotations

import re

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from romhop.gui.flow_layout import FlowLayout
from romhop.gui.workers import CoverLoader, DetailWorker

_IMAGE_HEIGHT = 200

REGION_FLAGS: dict[str, str] = {
    "USA": "🇺🇸",
    "Europe": "🇪🇺",
    "World": "🌍",
    "Japan": "🇯🇵",
    "Germany": "🇩🇪",
    "France": "🇫🇷",
    "Spain": "🇪🇸",
    "Italy": "🇮🇹",
    "Netherlands": "🇳🇱",
    "Brazil": "🇧🇷",
    "Korea": "🇰🇷",
    "China": "🇨🇳",
    "Australia": "🇦🇺",
    "Sweden": "🇸🇪",
    "Canada": "🇨🇦",
}

_CHIP_COLORS: dict[str, str] = {
    "region": "#1a5fb4",
    "language": "#26a269",
    "tag": "#5c5c5c",
    "revision": "#a35200",
}


def _strip_tags(name: str) -> str:
    prev = None
    while prev != name:
        prev = name
        name = re.sub(r"\s*\([^)]*\)", "", name)
    return name.strip()


def _placeholder_pixmap(width: int, height: int) -> QPixmap:
    pm = QPixmap(width, height)
    pm.fill(QColor("#3d3d3d"))
    painter = QPainter(pm)
    painter.setPen(QColor("#888888"))
    painter.setFont(painter.font())
    painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "🎮")
    painter.end()
    return pm


class _TagChip(QLabel):
    def __init__(self, text: str, category: str, parent=None):
        super().__init__(text, parent)
        color = _CHIP_COLORS.get(category, _CHIP_COLORS["tag"])
        self.setStyleSheet(
            f"background-color: {color}; color: white; border-radius: 8px;"
            "padding: 2px 6px; font-size: 11px;"
        )
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)


class DetailPanel(QWidget):
    """Right-docked panel showing one game's metadata and per-game action buttons."""

    download_requested = Signal(object)
    pull_requested = Signal(object)
    open_romm_requested = Signal(object)
    open_folder_requested = Signal(object)
    closed = Signal()
    _detail_loaded = Signal()  # test hook: detail fetch finished

    def __init__(self, parent=None, *, detail_provider=None,
                 cover_provider=None, screenshot_provider=None,
                 platform_label=None):
        super().__init__(parent)
        self._detail_provider = detail_provider
        self._cover_provider = cover_provider
        self._screenshot_provider = screenshot_provider
        self._platform_label_fn = platform_label
        self._rom = None
        self._downloaded_ids: set[int] = set()
        self._cache: dict[int, object] = {}
        self._worker = None
        self._workers: set = set()
        self._cover_loaders: set = set()
        self._shown_source: str = "none"  # "none" | "cover" | "screenshot"
        self._image_cache: dict[int, dict[str, QImage]] = {}

        self.setFixedWidth(300)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("DetailClose")
        close_btn.clicked.connect(self._on_close)
        top = QHBoxLayout()
        top.addStretch(1)
        top.addWidget(close_btn, 0)

        # --- image header ---
        self._image_label = QLabel()
        self._image_label.setFixedHeight(_IMAGE_HEIGHT)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("background-color: #3d3d3d;")
        self._image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._reset_image_placeholder()

        # --- title + platform ---
        self._name_label = QLabel("")
        self._name_label.setObjectName("DetailName")
        self._name_label.setWordWrap(True)
        fm = self._name_label.fontMetrics()
        self._name_label.setMaximumHeight(fm.height() * 3)

        self._platform_display = QLabel("")
        self._platform_display.setWordWrap(False)

        # --- chip area ---
        self._chips_widget = QWidget()
        self._chips_layout = FlowLayout(self._chips_widget, h_spacing=4, v_spacing=4)

        # --- metadata labels ---
        self._meta_label = QLabel("")
        self._meta_label.setWordWrap(True)
        self._summary_label = QLabel("")
        self._summary_label.setWordWrap(True)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(4, 4, 4, 4)
        scroll_layout.addWidget(self._image_label)
        scroll_layout.addWidget(self._name_label)
        scroll_layout.addWidget(self._platform_display)
        scroll_layout.addWidget(self._chips_widget)
        scroll_layout.addWidget(self._meta_label)
        scroll_layout.addWidget(self._summary_label)
        scroll_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(scroll_content)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

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
        box.addWidget(scroll, 1)
        for btn in (self._download_btn, self._pull_btn, self._romm_btn, self._folder_btn):
            box.addWidget(btn)
        self.hide()

    @property
    def has_rom(self) -> bool:
        return self._rom is not None

    def set_downloaded(self, ids: set[int]) -> None:
        self._downloaded_ids = set(ids)

    def _emit(self, signal) -> None:
        if self._rom is not None:
            signal.emit(self._rom)

    def _on_close(self) -> None:
        self.hide()
        self.closed.emit()

    def _reset_image_placeholder(self) -> None:
        pm = _placeholder_pixmap(self.width() or 300, _IMAGE_HEIGHT)
        self._image_label.setPixmap(pm)

    def _apply_pixmap(self, image: QImage) -> None:
        pm = QPixmap.fromImage(image)
        scaled = pm.scaled(
            self._image_label.width() or 300,
            _IMAGE_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled)

    def set_rom(self, rom) -> None:
        same_rom = self._rom is not None and self._rom.id == rom.id
        self._rom = rom
        downloaded = rom.id in self._downloaded_ids

        # title
        self._name_label.setText(_strip_tags(rom.name))

        # platform
        if self._platform_label_fn is not None:
            self._platform_display.setText(self._platform_label_fn(rom))
        else:
            self._platform_display.setText(rom.platform_name or rom.platform_slug)

        # chips
        self._rebuild_chips(rom)

        self._download_btn.setText("Re-download" if downloaded else "Download")
        self._folder_btn.setEnabled(downloaded)
        self._meta_label.setText("")
        self._summary_label.setText("Loading details…")
        self.show()

        # cover image
        self._start_cover_load(rom, same_rom)

        # detail fetch
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

    def _rebuild_chips(self, rom) -> None:
        while self._chips_layout.count():
            item = self._chips_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        for region in getattr(rom, "regions", []):
            flag = REGION_FLAGS.get(region, "")
            text = f"{flag} {region}".strip() if flag else region
            self._chips_layout.addWidget(_TagChip(text, "region"))

        for lang in getattr(rom, "languages", []):
            self._chips_layout.addWidget(_TagChip(lang, "language"))

        revision = getattr(rom, "revision", None)
        if revision:
            self._chips_layout.addWidget(_TagChip(revision, "revision"))

        for tag in getattr(rom, "tags", []):
            self._chips_layout.addWidget(_TagChip(tag, "tag"))

        self._chips_widget.updateGeometry()

    def _start_cover_load(self, rom, same_rom: bool = False) -> None:
        # cancel any in-flight cover/screenshot loaders for the previous rom
        for loader in list(self._cover_loaders):
            loader.requestInterruption()
        self._cover_loaders.clear()

        has_screenshot = bool(getattr(rom, "screenshots", None))
        cache = self._image_cache.get(rom.id, {})

        # apply the best already-cached image instantly — no placeholder flash,
        # no reload. screenshot is authoritative when present.
        if "screenshot" in cache:
            self._shown_source = "screenshot"
            self._apply_pixmap(cache["screenshot"])
            return
        if "cover" in cache and not has_screenshot:
            self._shown_source = "cover"
            self._apply_pixmap(cache["cover"])
            return

        # nothing usable cached. only blank to placeholder when actually switching
        # roms — a repeat click on the same rom keeps whatever's already shown.
        self._shown_source = "none"
        if not same_rom:
            self._reset_image_placeholder()

        # when a screenshot exists, load ONLY the screenshot (single loader, no
        # cover->screenshot upgrade flash). otherwise fall back to the cover.
        if has_screenshot and self._screenshot_provider is not None:
            self._start_loader(rom, self._screenshot_provider, "screenshot")
        elif self._cover_provider is not None:
            self._start_loader(rom, self._cover_provider, "cover")

    def _start_loader(self, rom, provider, kind: str) -> None:
        loader = CoverLoader([rom], provider)
        loader.cover_ready.connect(
            lambda rid, img, r=rom, k=kind: self._on_image_ready(rid, img, r, k)
        )
        loader.finished.connect(lambda lo=loader: self._cover_loaders.discard(lo))
        self._cover_loaders.add(loader)
        loader.start()

    def _on_image_ready(self, rom_id: int, image: QImage, rom, kind: str = "cover") -> None:
        self._image_cache.setdefault(rom_id, {})[kind] = image
        if self._rom is None or self._rom.id != rom_id:
            return
        # screenshot wins; never downgrade back to cover once screenshot shown
        if kind == "cover" and self._shown_source == "screenshot":
            return
        self._shown_source = kind
        self._apply_pixmap(image)

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
        self._meta_label.setText(" · ".join(bits))
        self._summary_label.setText(getattr(detail, "summary", "") or "")
