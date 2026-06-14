from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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

from romhop.romm_client import Rom


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._roms: list[Rom] = []
        self._checks: dict[int, tuple[QCheckBox, Rom]] = {}

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.currentTextChanged.connect(self._on_platform)

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._grid_host)

        row = QHBoxLayout(self)
        row.addWidget(self.sidebar, 0)
        row.addWidget(scroll, 1)

    def set_roms(self, roms: list[Rom]) -> None:
        self._roms = roms
        self.sidebar.clear()
        self.sidebar.addItems(platforms_from_roms(roms))
        if self.sidebar.count():
            self.sidebar.setCurrentRow(0)

    def current_platform(self) -> str:
        item = self.sidebar.currentItem()
        return item.text() if item else ""

    def _on_platform(self, platform: str) -> None:
        self._populate(platform, "")

    def filter(self, query: str) -> None:
        self._populate(self.current_platform(), query)

    def _populate(self, platform: str, query: str) -> None:
        while self._grid.count():
            w = self._grid.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        self._checks.clear()
        games = filter_games(self._roms, platform, query)
        cols = 4
        for i, rom in enumerate(games):
            cell = QWidget()
            box = QVBoxLayout(cell)
            cover = QLabel(rom.name)
            cover.setAlignment(Qt.AlignCenter)
            check = QCheckBox(rom.name)
            check.toggled.connect(self._emit_selection)
            box.addWidget(cover)
            box.addWidget(check)
            self._grid.addWidget(cell, i // cols, i % cols)
            self._checks[rom.id] = (check, rom)
        self._emit_selection()

    def selected_roms(self) -> list[Rom]:
        return [rom for check, rom in self._checks.values() if check.isChecked()]

    def _emit_selection(self) -> None:
        self.selection_changed.emit(self.selected_roms())
