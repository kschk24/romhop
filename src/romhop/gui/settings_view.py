from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from romhop import config
from romhop.config import Settings

# Order matters: this is the on-screen field order.
EDITABLE_FIELDS = [
    "romm_url",
    "roms_root",
    "saves_dir",
    "states_dir",
    "sync_delay_seconds",
]


def settings_to_rows(s: Settings) -> dict[str, str]:
    return {
        "romm_url": s.romm_url,
        "roms_root": str(s.roms_root),
        "saves_dir": str(s.saves_dir),
        "states_dir": str(s.states_dir),
        "sync_delay_seconds": str(s.sync_delay_seconds),
    }


def apply_rows(s: Settings, rows: dict[str, str]) -> Settings:
    return replace(
        s,
        romm_url=rows["romm_url"],
        roms_root=Path(rows["roms_root"]),
        saves_dir=Path(rows["saves_dir"]),
        states_dir=Path(rows["states_dir"]),
        sync_delay_seconds=float(rows["sync_delay_seconds"]),
    )


class SettingsView(QWidget):
    """Form over the editable config keys. Saves via config.save_settings."""

    saved = Signal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._edits: dict[str, QLineEdit] = {}

        form = QFormLayout()
        rows = settings_to_rows(settings)
        for field in EDITABLE_FIELDS:
            edit = QLineEdit(rows[field])
            self._edits[field] = edit
            form.addRow(field, edit)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(save_btn)

    def _on_save(self) -> None:
        # TODO(validation): float()/Path() in apply_rows can raise on bad input;
        # wrap in try/except and surface errors in the UI when validation lands.
        rows = {field: edit.text() for field, edit in self._edits.items()}
        self._settings = apply_rows(self._settings, rows)
        config.save_settings(self._settings)
        self.saved.emit()
