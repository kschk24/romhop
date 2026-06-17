from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from romhop.gui.workers import CoverLoader
from romhop.romm_client import Rom

# Column-wrap budget: width one cell claims (tile + grid spacing) before the
# grid wraps to another column.
CELL_TARGET_WIDTH = 160
# Fixed on-screen tile size — identical on every platform regardless of game
# count. Slightly narrower than the wrap budget so grid spacing fits without
# spilling into an extra column. Height is fixed so few-game platforms don't
# stretch their tiles tall (see overflow handling in _relayout).
CELL_WIDTH = 150
CELL_HEIGHT = 170
# Cover image area inside a tile; the rest holds the name checkbox.
COVER_HEIGHT = 120


def columns_for_width(width: int, cell_width: int = CELL_TARGET_WIDTH) -> int:
    """How many columns fit in `width`, never fewer than one."""
    return max(1, width // cell_width)


def platforms_from_roms(roms: list[Rom]) -> list[str]:
    return sorted({r.platform_slug for r in roms})


def filter_games(roms: list[Rom], platform: str | None, query: str,
                 downloaded_ids: set[int] | None = None,
                 downloaded_mode: str = "all", sort: str = "asc") -> list[Rom]:
    """Filter the whole rom set by platform (None = all), text query, and
    downloaded status, then sort by name. `downloaded_mode` is all/downloaded/missing."""
    ids = downloaded_ids or set()
    q = query.strip().lower()
    out = list(roms)
    if platform is not None:
        out = [r for r in out if r.platform_slug == platform]
    if q:
        out = [r for r in out if q in r.name.lower()]
    if downloaded_mode == "downloaded":
        out = [r for r in out if r.id in ids]
    elif downloaded_mode == "missing":
        out = [r for r in out if r.id not in ids]
    out.sort(key=lambda r: r.name.lower(), reverse=(sort == "desc"))
    return out


class LibraryView(QWidget):
    """Flat game grid with checkbox multi-select and filter controls."""

    selection_changed = Signal(list)   # list[Rom] currently checked
    tile_activated = Signal(object)    # Rom whose body was clicked
    action_requested = Signal(str, object)  # (action_name, Rom)

    def __init__(self, parent=None, *, cover_provider=None, platform_label=None):
        super().__init__(parent)
        # cover_provider(rom) -> Path | None (cached cover image); fetched off
        # the UI thread by a CoverLoader and rendered into each tile.
        self._cover_provider = cover_provider
        # platform_label(rom) -> str displayed in the platform pill on each tile.
        self._platform_label = platform_label or (
            lambda rom: rom.platform_name or rom.platform_slug
        )
        self._cover_labels: dict[int, QLabel] = {}
        self._pixmap_cache: dict[int, QPixmap] = {}
        self._pills: dict[int, QLabel] = {}
        self._ribbons: dict[int, QLabel] = {}
        self._cover_loader = None
        # Every loader started but not yet finished. Holding a strong reference
        # here keeps the QThread alive until run() returns, even after a newer
        # load supersedes it — otherwise GC frees a running thread and Qt aborts.
        self._cover_loaders: set = set()
        self._roms: list[Rom] = []
        self._checks: dict[int, tuple[QCheckBox, Rom]] = {}
        # Global selection: rom ids checked across ALL filter states. The per-filter
        # _checks dict is rebuilt on every filter change, so selection state
        # must live here to survive filter changes and to drive a download set
        # that spans platforms.
        self._selected_ids: set[int] = set()
        self._cells: list[QWidget] = []
        self._cols = 0
        self._query = ""
        # Filter state
        self._platform_filter: str | None = None
        self._downloaded_mode = "all"
        self._sort = "asc"
        self._downloaded_ids: set[int] = set()

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._grid_host)

        row = QHBoxLayout(self)
        row.addWidget(self._scroll, 1)

    def set_roms(self, roms: list[Rom]) -> None:
        self._roms = roms
        # Fresh library: drop any selection and caches that referred to the old rom set.
        self._selected_ids.clear()
        self._pixmap_cache.clear()
        self._downloaded_ids = set()
        self._platform_filter = None
        self._downloaded_mode = "all"
        self._sort = "asc"
        self._populate()

    def filter(self, query: str) -> None:
        self._query = query
        self._populate()

    def set_platform_filter(self, slug: str | None) -> None:
        self._platform_filter = slug
        self._populate()

    def set_downloaded_filter(self, mode: str) -> None:
        self._downloaded_mode = mode
        self._populate()

    def set_sort(self, order: str) -> None:
        self._sort = order
        self._populate()

    def set_downloaded(self, ids: set[int]) -> None:
        self._downloaded_ids = set(ids)
        self._populate()

    def _populate(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
            del item
        self._checks.clear()
        self._cover_labels = {}
        self._pills = {}
        self._ribbons = {}
        self._cells = []
        games = filter_games(self._roms, self._platform_filter, self._query,
                             self._downloaded_ids, self._downloaded_mode, self._sort)
        for rom in games:
            cell = QWidget()
            # Fixed size: tiles look identical across platforms; overflow scrolls
            # rather than the grid stretching tiles to fill the viewport.
            cell.setFixedSize(CELL_WIDTH, CELL_HEIGHT)
            box = QVBoxLayout(cell)
            box.setContentsMargins(4, 4, 4, 4)
            box.setSpacing(2)
            # Cover area: blank placeholder until the loader supplies a pixmap.
            cover = QLabel()
            cover.setObjectName("Cover")
            cover.setFixedSize(CELL_WIDTH - 8, COVER_HEIGHT)
            cover.setAlignment(Qt.AlignCenter)
            # Platform pill overlaid on the cover image (bottom-left corner).
            pill = QLabel(self._platform_label(rom), cover)
            pill.setObjectName("PlatformPill")
            pill.move(4, COVER_HEIGHT - 20)
            self._pills[rom.id] = pill
            # Downloaded indicator: dim cover + green ribbon across the top.
            if rom.id in self._downloaded_ids:
                cover.setProperty("downloaded", True)
                ribbon = QLabel("DOWNLOADED", cover)
                ribbon.setObjectName("DownloadedRibbon")
                ribbon.setFixedWidth(CELL_WIDTH - 8)
                ribbon.setAlignment(Qt.AlignCenter)
                ribbon.move(0, 0)
                self._ribbons[rom.id] = ribbon
            check = QCheckBox()  # bare glyph: batch-select only, no title text
            check.setChecked(rom.id in self._selected_ids)
            check.toggled.connect(
                lambda checked, rid=rom.id: self._on_toggle(rid, checked)
            )
            name = QLabel(rom.name)
            name.setObjectName("TileName")
            name.setWordWrap(True)
            cover.mousePressEvent = lambda e, rid=rom.id: self._activate_rom(rid)
            name.mousePressEvent = lambda e, rid=rom.id: self._activate_rom(rid)
            name_row = QHBoxLayout()
            name_row.setContentsMargins(0, 0, 0, 0)
            name_row.addWidget(check, 0)
            name_row.addWidget(name, 1)
            cell.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            cell.customContextMenuRequested.connect(
                lambda pos, rid=rom.id, c=cell: self._show_menu(c, rid)
            )
            box.addWidget(cover)
            box.addLayout(name_row)
            self._cells.append(cell)
            self._checks[rom.id] = (check, rom)
            self._cover_labels[rom.id] = cover
        self._relayout(force=True)
        self._start_cover_load(games)
        self._emit_selection()

    def _start_cover_load(self, roms: list[Rom]) -> None:
        # Split into cache hits (pixmap already decoded) and misses.
        cached = [r for r in roms if r.id in self._pixmap_cache]
        misses = [r for r in roms if r.id not in self._pixmap_cache]

        # Apply cached pixmaps synchronously — zero decode cost.
        for rom in cached:
            label = self._cover_labels.get(rom.id)
            if label is not None:
                label.setPixmap(self._pixmap_cache[rom.id])

        # Always cancel any stale loader (may be running from a previous filter).
        self._stop_cover_load()

        if not misses or self._cover_provider is None:
            return

        # A previous load may still be running (covers fetch from disk/network).
        # Ask it to stop, but keep it referenced in _cover_loaders until it
        # actually finishes — dropping a running QThread crashes the app.
        loader = CoverLoader(misses, self._cover_provider,
                             cover_size=(CELL_WIDTH - 8, COVER_HEIGHT))
        loader.cover_ready.connect(self._apply_cover)
        loader.finished.connect(lambda ldr=loader: self._cover_loaders.discard(ldr))
        self._cover_loaders.add(loader)
        self._cover_loader = loader
        loader.start()

    def _stop_cover_load(self) -> None:
        # Cooperative cancel: CoverLoader.run() checks isInterruptionRequested()
        # between roms and returns early, firing finished -> discard.
        if self._cover_loader is not None:
            self._cover_loader.requestInterruption()
            self._cover_loader = None

    def _apply_cover(self, rom_id: int, image: QImage) -> None:
        # A loader from a previous platform may emit for a tile that's gone.
        label = self._cover_labels.get(rom_id)
        if label is None:
            return
        pm = QPixmap.fromImage(image)
        if pm.isNull():
            return
        self._pixmap_cache[rom_id] = pm
        label.setPixmap(pm)

    def _on_toggle(self, rom_id: int, checked: bool) -> None:
        # Update the global set, then report the new cross-platform selection.
        if checked:
            self._selected_ids.add(rom_id)
        else:
            self._selected_ids.discard(rom_id)
        self._emit_selection()

    def _relayout(self, force: bool = False) -> None:
        # Re-grid the existing cells when the column count changes (live resize).
        cols = columns_for_width(self._scroll.viewport().width())
        if cols == self._cols and not force:
            return
        # Clear stale row/column stretches from the previous layout before
        # re-placing (stretch factors persist across takeAt()).
        for r in range(self._grid.rowCount()):
            self._grid.setRowStretch(r, 0)
        for c in range(self._grid.columnCount()):
            self._grid.setColumnStretch(c, 0)
        self._cols = cols
        # Detach items without destroying the cell widgets, then re-place them.
        while self._grid.count():
            self._grid.takeAt(0)
        for i, cell in enumerate(self._cells):
            self._grid.addWidget(cell, i // cols, i % cols, Qt.AlignTop | Qt.AlignLeft)
        # Park leftover space in a trailing row/column so fixed-size tiles stay
        # packed top-left instead of being spread apart on sparse platforms.
        rows = (len(self._cells) + cols - 1) // cols if self._cells else 0
        self._grid.setRowStretch(rows, 1)
        self._grid.setColumnStretch(cols, 1)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout()

    def clear_selection(self) -> None:
        self._selected_ids.clear()
        for check, _rom in self._checks.values():
            check.blockSignals(True)
            check.setChecked(False)
            check.blockSignals(False)
        self._emit_selection()

    def selected_roms(self) -> list[Rom]:
        # Global selection across all filter states, not just the visible tiles.
        return [rom for rom in self._roms if rom.id in self._selected_ids]

    def _rom_by_id(self, rom_id: int):
        return next((r for r in self._roms if r.id == rom_id), None)

    def _activate_rom(self, rom_id: int) -> None:
        rom = self._rom_by_id(rom_id)
        if rom is not None:
            self.tile_activated.emit(rom)

    def _emit_action(self, name: str, rom_id: int) -> None:
        rom = self._rom_by_id(rom_id)
        if rom is not None:
            self.action_requested.emit(name, rom)

    def _show_menu(self, cell, rom_id: int) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        downloaded = rom_id in self._downloaded_ids
        items = [
            ("Re-download" if downloaded else "Download", "download", True),
            ("Pull savegames", "pull", True),
            ("Open in RomM", "open_romm", True),
            ("Open containing folder", "open_folder", downloaded),
        ]
        for label, action_name, enabled in items:
            act = menu.addAction(label)
            act.setEnabled(enabled)
            act.triggered.connect(
                lambda _=False, n=action_name: self._emit_action(n, rom_id)
            )
        menu.exec(cell.mapToGlobal(cell.rect().center()))

    def _emit_selection(self) -> None:
        self.selection_changed.emit(self.selected_roms())
