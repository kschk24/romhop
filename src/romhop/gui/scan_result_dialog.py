from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
)


class ScanResultDialog(QDialog):
    """Reports a scan outcome: a counts headline plus the unmatched games and
    basename collisions. Empty sections are omitted from the detail body."""

    def __init__(self, result, parent=None):
        super().__init__(parent)
        self._result = result
        self.setWindowTitle("Scan results")

        summary = QLabel(self.summary_text())
        detail = QPlainTextEdit(self.detail_text())
        detail.setReadOnly(True)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(summary)
        if self.detail_text():
            layout.addWidget(detail)
        layout.addWidget(buttons)

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
