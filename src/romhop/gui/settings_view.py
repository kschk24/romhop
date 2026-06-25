from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from romhop import config
from romhop.config import SCHEMA, CATEGORY_ORDER, CATEGORY_LABELS, Settings

SYNC_LABEL = "Enable save sync"  # the label of the sync_enabled FieldSpec
TOKEN_LABEL = "API token"  # keyring-stored, not a SCHEMA field
TOKEN_CATEGORY = "connection"  # group the token row lives under
DESKTOP_NOTIF_LABEL = "Desktop notifications"  # the label of the desktop_notifications FieldSpec


class SettingsView(QWidget):
    """Schema-driven settings form. One QGroupBox per category, built from
    config.SCHEMA. Saves via config.save_settings."""

    saved = Signal()
    cancelled = Signal()
    scan_requested = Signal()
    upload_requested = Signal()
    setup_requested = Signal()
    token_changed = Signal(str)  # emitted with the new token on a non-blank save
    update_check_requested = Signal()

    def __init__(self, settings: Settings, parent=None, *,
                 open_log_dir_fn=None, export_logs_fn=None):
        super().__init__(parent)
        self._settings = settings
        self._open_log_dir_fn = open_log_dir_fn
        self._export_logs_fn = export_logs_fn
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
            if category == TOKEN_CATEGORY:
                self._add_token_row(form)
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
        self.upload_btn = QPushButton("Upload local games to RomM")
        self.upload_btn.setObjectName("UploadButton")
        self.upload_btn.clicked.connect(lambda: self.upload_requested.emit())
        self.setup_btn = QPushButton("Run setup wizard")
        self.setup_btn.setObjectName("SetupButton")
        self.setup_btn.clicked.connect(lambda: self.setup_requested.emit())
        self.update_check_btn = QPushButton("Check for updates")
        self.update_check_btn.setObjectName("UpdateCheckButton")
        self.update_check_btn.clicked.connect(lambda: self.update_check_requested.emit())
        scan_row = QHBoxLayout()
        scan_row.addWidget(self.scan_btn)
        scan_row.addWidget(self.upload_btn)
        scan_row.addWidget(self.setup_btn)
        scan_row.addWidget(self.update_check_btn)
        scan_row.addStretch(1)
        layout.addLayout(scan_row)

        self.open_log_btn = QPushButton("Open log folder")
        self.open_log_btn.setObjectName("OpenLogFolderButton")
        self.open_log_btn.clicked.connect(self._on_open_log_folder)
        self.export_logs_btn = QPushButton("Export logs…")
        self.export_logs_btn.setObjectName("ExportLogsButton")
        self.export_logs_btn.clicked.connect(self._on_export_logs)
        log_row = QHBoxLayout()
        log_row.addWidget(self.open_log_btn)
        log_row.addWidget(self.export_logs_btn)
        log_row.addStretch(1)
        layout.addLayout(log_row)

        self._populate()
        self._refresh_scan_enabled()
        self._refresh_upload_enabled()

    # --- build helpers ---
    def _make_widget(self, spec) -> QWidget:
        # No text on the checkbox: the QFormLayout row already shows spec.label,
        # so a checkbox with its own text would double the label.
        if spec.type == "bool":
            return QCheckBox()
        if spec.type == "choice":
            combo = QComboBox()
            for opt in spec.options:
                combo.addItem(opt)
            return combo
        return QLineEdit()

    def _add_token_row(self, form: QFormLayout) -> None:
        """API token is stored in the OS keyring, not the ini, so it isn't a
        SCHEMA field. Add a masked row by hand and register it in _edits/
        _row_form so search filtering covers it — _populate and _on_save skip
        labels with no FieldSpec, so it stays out of the schema save path."""
        edit = QLineEdit()
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setToolTip("RomM API token. Stored in the OS keyring, never on disk.")
        self.token_edit = edit
        # Registered in _row_form (so search filtering reaches it) but NOT in
        # _edits, which stays a pure map of SCHEMA labels.
        self._row_form[TOKEN_LABEL] = form
        form.addRow(TOKEN_LABEL, edit)

    def _populate(self) -> None:
        """Load every widget from the saved settings."""
        for label, widget in self._edits.items():
            spec = self._spec_by_label[label]
            value = getattr(self._settings, spec.key)
            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(str(value))
            else:
                widget.setText(str(value))
        self._populate_token()

    def _populate_token(self) -> None:
        """Leave the field blank; a blank save keeps the current token (so we
        never echo the secret back into a widget). Placeholder signals whether
        one is already set."""
        self.token_edit.clear()
        if config.get_token():
            self.token_edit.setPlaceholderText("•••••••• (leave blank to keep)")
        else:
            self.token_edit.setPlaceholderText("Not set")

    # --- sync shims (bottom-bar indicator) ---
    def sync_enabled(self) -> bool:
        return self._settings.sync_enabled

    def set_sync_enabled(self, enabled: bool) -> None:
        self._settings = replace(self._settings, sync_enabled=enabled)
        self.sync_check.setChecked(enabled)

    def focus_sync(self) -> None:
        self.sync_check.setFocus()

    def set_desktop_notifications_available(self, available: bool, hint: str = "") -> None:
        """Disable the desktop notifications toggle with a hint when no tray is available."""
        widget = self._edits.get(DESKTOP_NOTIF_LABEL)
        if widget is None:
            return
        widget.setEnabled(available)
        if not available and hint:
            widget.setToolTip(hint)

    # --- host integration ---
    def current_settings(self) -> Settings:
        return self._settings

    # --- log actions ---
    def _on_open_log_folder(self) -> None:
        if self._open_log_dir_fn is not None:
            self._open_log_dir_fn()

    def _on_export_logs(self) -> None:
        if self._export_logs_fn is None:
            return
        from pathlib import Path
        import os
        desktop = Path(os.path.expanduser("~/Desktop"))
        default_dir = str(desktop) if desktop.is_dir() else os.path.expanduser("~")
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export logs", f"{default_dir}/romhop-logs.zip", "Zip files (*.zip)"
        )
        if dest:
            self._export_logs_fn(Path(dest))

    # --- scan / upload actions ---
    def _refresh_scan_enabled(self) -> None:
        self.scan_btn.setEnabled(config.roms_root_configured(self._settings))

    def set_scanning(self, scanning: bool) -> None:
        if scanning:
            self.scan_btn.setEnabled(False)
            self.scan_btn.setText("Scanning…")
        else:
            self.scan_btn.setText("Scan local library")
            self._refresh_scan_enabled()

    def _refresh_upload_enabled(self) -> None:
        self.upload_btn.setEnabled(config.roms_root_configured(self._settings))

    def set_uploading(self, uploading: bool) -> None:
        if uploading:
            self.upload_btn.setEnabled(False)
            self.upload_btn.setText("Discovering…")
        else:
            self.upload_btn.setText("Upload local games to RomM")
            self._refresh_upload_enabled()

    # --- search/filter ---
    def _widget_for(self, label: str) -> QWidget:
        # Token isn't in _edits (kept pure to SCHEMA), so resolve it here.
        return self.token_edit if label == TOKEN_LABEL else self._edits[label]

    def filter(self, query: str) -> None:
        q = query.strip().lower()
        for label, form in self._row_form.items():
            widget = self._widget_for(label)
            visible = q in label.lower() if q else True
            form.setRowVisible(widget, visible)
        # Hide a group whose rows are all filtered out.
        for group in self._groups:
            form = group.layout()
            any_visible = any(
                form.isRowVisible(self._widget_for(label))
                for label, f in self._row_form.items()
                if f is form
            )
            group.setVisible(any_visible)

    def is_field_visible(self, label: str) -> bool:
        return self._row_form[label].isRowVisible(self._widget_for(label))

    # --- save / cancel ---
    def reset(self) -> None:
        self._populate()
        self._refresh_scan_enabled()
        self._refresh_upload_enabled()

    def load(self, settings: Settings) -> None:
        """Replace the backing settings and refresh every widget. Used after the
        setup wizard writes new values so the form reflects them."""
        self._settings = settings
        self.reset()

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
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return config.coerce_value(spec.type, widget.text())

    def _on_save(self) -> None:
        # TODO(validation): coerce_value can raise on bad int/float input; wrap
        # and surface errors in the UI when validation lands.
        updates = {
            self._spec_by_label[label].key: self._read_widget(label)
            for label in self._edits
            if label in self._spec_by_label
        }
        self._settings = replace(self._settings, **updates)
        self._refresh_scan_enabled()
        # Warn (don't block) if the ROMs folder isn't usable, so downloads fail
        # later with a clear reason set here rather than a raw worker traceback.
        if config.roms_root_configured(self._settings):
            problem = config.roms_root_problem(self._settings.roms_root)
            if problem is not None:
                QMessageBox.warning(self, "ROMs folder unusable", problem)
        config.save_settings(self._settings)
        # Token lives in the keyring, not the ini. Blank == keep current, so a
        # bad save can never wipe a working token.
        token = self.token_edit.text().strip()
        if token:
            config.set_token(token)
            self.token_changed.emit(token)  # let the host update the live client
        self._populate_token()  # reset placeholder to reflect the new state
        self.saved.emit()
