from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
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


def filter_games(roms: list[Rom], platform: str, query: str) -> list[Rom]:
    q = query.strip().lower()
    out = [r for r in roms if r.platform_slug == platform]
    if q:
        out = [r for r in out if q in r.name.lower()]
    return sorted(out, key=lambda r: r.name.lower())


class LibraryView(QWidget):
    """Platform sidebar + game grid with checkbox multi-select."""

    selection_changed = Signal(list)  # emits list[Rom] currently checked

    def __init__(self, parent=None, *, cover_provider=None):
        super().__init__(parent)
        # cover_provider(rom) -> Path | None (cached cover image); fetched off
        # the UI thread by a CoverLoader and rendered into each tile.
        self._cover_provider = cover_provider
        self._cover_labels: dict[int, QLabel] = {}
        self._cover_loader = None
        self._roms: list[Rom] = []
        self._checks: dict[int, tuple[QCheckBox, Rom]] = {}
        # Global selection: rom ids checked across ALL platforms. The per-tab
        # _checks dict is rebuilt on every platform switch, so selection state
        # must live here to survive switching tabs and to drive a download set
        # that spans platforms.
        self._selected_ids: set[int] = set()
        self._cells: list[QWidget] = []
        self._cols = 0
        self._query = ""

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.currentTextChanged.connect(self._on_platform)

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._grid_host)

        row = QHBoxLayout(self)
        row.addWidget(self.sidebar, 0)
        row.addWidget(self._scroll, 1)

    def set_roms(self, roms: list[Rom]) -> None:
        self._roms = roms
        # Fresh library: drop any selection that referred to the old rom set.
        self._selected_ids.clear()
        self.sidebar.clear()
        self.sidebar.addItems(platforms_from_roms(roms))
        if self.sidebar.count():
            self.sidebar.setCurrentRow(0)

    def current_platform(self) -> str:
        item = self.sidebar.currentItem()
        return item.text() if item else ""

    def _on_platform(self, platform: str) -> None:
        # Keep the active search query when switching platforms.
        self._populate(platform, self._query)

    def filter(self, query: str) -> None:
        self._query = query
        self._populate(self.current_platform(), query)

    def _populate(self, platform: str, query: str) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
            del item
        self._checks.clear()
        self._cover_labels = {}
        self._cells = []
        games = filter_games(self._roms, platform, query)
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
            check = QCheckBox(rom.name)
            # Reflect the global selection, set before connecting so this
            # programmatic state doesn't fire a spurious toggle.
            check.setChecked(rom.id in self._selected_ids)
            check.toggled.connect(
                lambda checked, rid=rom.id: self._on_toggle(rid, checked)
            )
            box.addWidget(cover)
            box.addWidget(check)
            self._cells.append(cell)
            self._checks[rom.id] = (check, rom)
            self._cover_labels[rom.id] = cover
        self._relayout(force=True)
        self._start_cover_load(games)
        self._emit_selection()

    def _start_cover_load(self, roms: list[Rom]) -> None:
        if self._cover_provider is None or not roms:
            return
        loader = CoverLoader(roms, self._cover_provider)
        loader.cover_ready.connect(self._apply_cover)
        # Hold a reference so the thread isn't garbage-collected mid-run.
        self._cover_loader = loader
        loader.start()

    def _apply_cover(self, rom_id: int, path: str) -> None:
        # A loader from a previous platform may emit for a tile that's gone.
        label = self._cover_labels.get(rom_id)
        if label is None or not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            return
        label.setPixmap(pixmap.scaled(
            label.width(), label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        ))

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

    def selected_roms(self) -> list[Rom]:
        # Global selection across all platforms, not just the visible tab.
        return [rom for rom in self._roms if rom.id in self._selected_ids]

    def _emit_selection(self) -> None:
        self.selection_changed.emit(self.selected_roms())
