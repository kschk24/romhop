from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from romhop import config
from romhop.config import Settings

DOWNLOAD_LIMIT_LABEL = "Download limit (KB/s, 0 = unlimited):"

# Order matters: this is the on-screen field order.
EDITABLE_FIELDS = [
    "RomM URL:",
    "Rom directory:",
    "Saves directory:",
    "States directory:",
    "Sync delay:",
    DOWNLOAD_LIMIT_LABEL,
]


def settings_to_rows(s: Settings) -> dict[str, str]:
    return {
        "RomM URL:": s.romm_url,
        "Rom directory:": str(s.roms_root),
        "Saves directory:": str(s.saves_dir),
        "States directory:": str(s.states_dir),
        "Sync delay:": str(s.sync_delay_seconds),
        DOWNLOAD_LIMIT_LABEL: str(s.download_rate_limit_kbps),
    }


def apply_rows(s: Settings, rows: dict[str, str]) -> Settings:
    return replace(
        s,
        romm_url=rows["RomM URL:"],
        roms_root=Path(rows["Rom directory:"]),
        saves_dir=Path(rows["Saves directory:"]),
        states_dir=Path(rows["States directory:"]),
        sync_delay_seconds=float(rows["Sync delay:"]),
        download_rate_limit_kbps=int(rows[DOWNLOAD_LIMIT_LABEL]),
    )


class SettingsView(QWidget):
    """Form over the editable config keys. Saves via config.save_settings."""

    saved = Signal()
    cancelled = Signal()
    scan_requested = Signal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._edits: dict[str, QLineEdit] = {}

        self._form = QFormLayout()
        form = self._form
        rows = settings_to_rows(settings)
        for field in EDITABLE_FIELDS:
            edit = QLineEdit(rows[field])
            self._edits[field] = edit
            form.addRow(field, edit)

        # Sync section: an enable toggle grouped under its own heading so the
        # bottom-bar indicator can navigate straight here. sync_delay_seconds
        # stays in the form above; this is the on/off control.
        self.sync_section = QGroupBox("Sync")
        self.sync_section.setObjectName("SyncSection")
        self.sync_check = QCheckBox("Enable save sync")
        self.sync_check.setChecked(settings.sync_enabled)
        sync_box = QVBoxLayout(self.sync_section)
        sync_box.addWidget(self.sync_check)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self._on_cancel)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)

        buttons = QHBoxLayout()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)

        # Standalone maintenance action, separate from the form's Save/Cancel.
        self.scan_btn = QPushButton("Scan local library")
        self.scan_btn.setObjectName("ScanButton")
        self.scan_btn.clicked.connect(lambda: self.scan_requested.emit())
        scan_row = QHBoxLayout()
        scan_row.addWidget(self.scan_btn)
        scan_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.sync_section)
        layout.addLayout(buttons)
        layout.addLayout(scan_row)
        self._refresh_scan_enabled()

    def sync_enabled(self) -> bool:
        return self._settings.sync_enabled

    def set_sync_enabled(self, enabled: bool) -> None:
        """Mirror an external sync-toggle change (e.g. the bottom-bar button)
        into the saved settings and the checkbox, so the menu never disagrees
        with the rest of the UI."""
        self._settings = replace(self._settings, sync_enabled=enabled)
        self.sync_check.setChecked(enabled)
        self._refresh_scan_enabled()

    def current_settings(self) -> Settings:
        """The last-saved Settings (drives the host's in-memory copy)."""
        return self._settings

    def _refresh_scan_enabled(self) -> None:
        """Scan needs a configured ROMs folder; grey out the button otherwise."""
        self.scan_btn.setEnabled(config.roms_root_configured(self._settings))

    def set_scanning(self, scanning: bool) -> None:
        """Busy state while a scan runs off the UI thread."""
        if scanning:
            self.scan_btn.setEnabled(False)
            self.scan_btn.setText("Scanning…")
        else:
            self.scan_btn.setText("Scan local library")
            self._refresh_scan_enabled()

    def focus_sync(self) -> None:
        """Surface the sync section (the clickable bottom-bar indicator lands
        here)."""
        self.sync_check.setFocus()

    def filter(self, query: str) -> None:
        """Show only rows whose field name matches the query (substring,
        case-insensitive). Empty query shows every row."""
        q = query.strip().lower()
        for field, edit in self._edits.items():
            visible = q in field.lower() if q else True
            self._form.setRowVisible(edit, visible)

    def is_field_visible(self, field: str) -> bool:
        return self._form.isRowVisible(self._edits[field])

    def reset(self) -> None:
        """Repopulate fields from the saved settings, discarding edits."""
        rows = settings_to_rows(self._settings)
        for field, edit in self._edits.items():
            edit.setText(rows[field])
        self.sync_check.setChecked(self._settings.sync_enabled)

    def keyPressEvent(self, event) -> None:
        # Esc backs out of settings without saving.
        if event.key() == Qt.Key.Key_Escape:
            self._on_cancel()
            return
        super().keyPressEvent(event)

    def _on_cancel(self) -> None:
        self.reset()
        self.cancelled.emit()

    def _on_save(self) -> None:
        # TODO(validation): float()/Path() in apply_rows can raise on bad input;
        # wrap in try/except and surface errors in the UI when validation lands.
        rows = {field: edit.text() for field, edit in self._edits.items()}
        self._settings = replace(
            apply_rows(self._settings, rows),
            sync_enabled=self.sync_check.isChecked(),
        )
        self._refresh_scan_enabled()
        config.save_settings(self._settings)
        self.saved.emit()
