from __future__ import annotations

from dataclasses import replace

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
from romhop.config import SCHEMA, CATEGORY_ORDER, CATEGORY_LABELS, Settings

SYNC_LABEL = "Enable save sync"  # the label of the sync_enabled FieldSpec


class SettingsView(QWidget):
    """Schema-driven settings form. One QGroupBox per category, built from
    config.SCHEMA. Saves via config.save_settings."""

    saved = Signal()
    cancelled = Signal()
    scan_requested = Signal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        # label -> editor widget (QLineEdit or QCheckBox)
        self._edits: dict[str, QWidget] = {}
        # label -> the QFormLayout holding its row (for show/hide)
        self._row_form: dict[str, QFormLayout] = {}
        # label -> FieldSpec (for save-time coercion)
        self._spec_by_label: dict[str, "config.FieldSpec"] = {
            f.label: f for f in SCHEMA
        }
        self._groups: list[QGroupBox] = []

        layout = QVBoxLayout(self)
        for category in CATEGORY_ORDER:
            group = QGroupBox(CATEGORY_LABELS[category])
            form = QFormLayout(group)
            for spec in SCHEMA:
                if spec.category != category:
                    continue
                widget = self._make_widget(spec)
                widget.setToolTip(spec.help)
                self._edits[spec.label] = widget
                self._row_form[spec.label] = form
                form.addRow(spec.label, widget)
            self._groups.append(group)
            layout.addWidget(group)

        # Shim: the bottom-bar sync indicator and old tests reach for sync_check.
        self.sync_check = self._edits[SYNC_LABEL]

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self._on_cancel)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)
        buttons = QHBoxLayout()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

        # Standalone maintenance action, separate from the form's Save/Cancel.
        self.scan_btn = QPushButton("Scan local library")
        self.scan_btn.setObjectName("ScanButton")
        self.scan_btn.clicked.connect(lambda: self.scan_requested.emit())
        scan_row = QHBoxLayout()
        scan_row.addWidget(self.scan_btn)
        scan_row.addStretch(1)
        layout.addLayout(scan_row)

        self._populate()
        self._refresh_scan_enabled()

    # --- build helpers ---
    def _make_widget(self, spec) -> QWidget:
        # No text on the checkbox: the QFormLayout row already shows spec.label,
        # so a checkbox with its own text would double the label.
        if spec.type == "bool":
            return QCheckBox()
        return QLineEdit()

    def _populate(self) -> None:
        """Load every widget from the saved settings."""
        for label, widget in self._edits.items():
            spec = self._spec_by_label[label]
            value = getattr(self._settings, spec.key)
            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            else:
                widget.setText(str(value))

    # --- sync shims (bottom-bar indicator) ---
    def sync_enabled(self) -> bool:
        return self._settings.sync_enabled

    def set_sync_enabled(self, enabled: bool) -> None:
        self._settings = replace(self._settings, sync_enabled=enabled)
        self.sync_check.setChecked(enabled)

    def focus_sync(self) -> None:
        self.sync_check.setFocus()

    # --- host integration ---
    def current_settings(self) -> Settings:
        return self._settings

    # --- scan action ---
    def _refresh_scan_enabled(self) -> None:
        self.scan_btn.setEnabled(config.roms_root_configured(self._settings))

    def set_scanning(self, scanning: bool) -> None:
        if scanning:
            self.scan_btn.setEnabled(False)
            self.scan_btn.setText("Scanning…")
        else:
            self.scan_btn.setText("Scan local library")
            self._refresh_scan_enabled()

    # --- search/filter ---
    def filter(self, query: str) -> None:
        q = query.strip().lower()
        for label, form in self._row_form.items():
            widget = self._edits[label]
            visible = q in label.lower() if q else True
            form.setRowVisible(widget, visible)
        # Hide a group whose rows are all filtered out.
        for group in self._groups:
            form = group.layout()
            any_visible = any(
                form.isRowVisible(self._edits[label])
                for label, f in self._row_form.items()
                if f is form
            )
            group.setVisible(any_visible)

    def is_field_visible(self, label: str) -> bool:
        return self._row_form[label].isRowVisible(self._edits[label])

    # --- save / cancel ---
    def reset(self) -> None:
        self._populate()
        self._refresh_scan_enabled()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._on_cancel()
            return
        super().keyPressEvent(event)

    def _on_cancel(self) -> None:
        self.reset()
        self.cancelled.emit()

    def _read_widget(self, label: str):
        widget = self._edits[label]
        spec = self._spec_by_label[label]
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        return config.coerce_value(spec.type, widget.text())

    def _on_save(self) -> None:
        # TODO(validation): coerce_value can raise on bad int/float input; wrap
        # and surface errors in the UI when validation lands.
        updates = {
            self._spec_by_label[label].key: self._read_widget(label)
            for label in self._edits
        }
        self._settings = replace(self._settings, **updates)
        self._refresh_scan_enabled()
        config.save_settings(self._settings)
        self.saved.emit()
