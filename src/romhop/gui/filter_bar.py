from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QWidget


class FilterBar(QWidget):
    """Stateless gallery filter controls: Platform, Downloaded, Sort.

    Owns no library data — it only reports the user's intent via signals. The
    platform list is injected with set_platforms().
    """

    platform_changed = Signal(object)   # slug str, or None for "All platforms"
    downloaded_changed = Signal(str)    # "all" | "downloaded" | "missing"
    sort_changed = Signal(str)          # "asc" | "desc"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.platform_combo = QComboBox()
        self.platform_combo.addItem("All platforms", None)
        self.platform_combo.currentIndexChanged.connect(self._emit_platform)

        self.downloaded_combo = QComboBox()
        for label, mode in (("Downloaded: All", "all"),
                            ("Downloaded", "downloaded"),
                            ("Not downloaded", "missing")):
            self.downloaded_combo.addItem(label, mode)
        self.downloaded_combo.currentIndexChanged.connect(
            lambda i: self.downloaded_changed.emit(self.downloaded_combo.itemData(i)))

        self.sort_combo = QComboBox()
        for label, order in (("Name A-Z", "asc"), ("Name Z-A", "desc")):
            self.sort_combo.addItem(label, order)
        self.sort_combo.currentIndexChanged.connect(
            lambda i: self.sort_changed.emit(self.sort_combo.itemData(i)))

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.platform_combo)
        row.addWidget(self.downloaded_combo)
        row.addWidget(self.sort_combo)
        row.addStretch(1)

    def set_platforms(self, pairs: list[tuple[str, str]]) -> None:
        """Replace the platform list. `pairs` = [(slug, display_name), ...].
        Keeps "All platforms" at index 0."""
        self.platform_combo.blockSignals(True)
        self.platform_combo.clear()
        self.platform_combo.addItem("All platforms", None)
        for slug, name in pairs:
            self.platform_combo.addItem(name, slug)
        self.platform_combo.setCurrentIndex(0)
        self.platform_combo.blockSignals(False)

    def _emit_platform(self, index: int) -> None:
        self.platform_changed.emit(self.platform_combo.itemData(index))
