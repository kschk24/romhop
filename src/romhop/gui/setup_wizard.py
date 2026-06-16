from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from romhop.gui.workers import CallableWorker


class ConnectionPage(QWizardPage):
    """RomM URL + token, with a Test-connection gate. Next stays disabled until
    a test passes; editing either field re-locks it."""

    def __init__(self, validate_fn, parent=None):
        super().__init__(parent)
        self.setTitle("Connect to RomM")
        self._validate_fn = validate_fn
        self._validated = False
        self._worker = None

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("http://romm.local")
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("rmm_...")
        self.url_edit.textChanged.connect(self._invalidate)
        self.token_edit.textChanged.connect(self._invalidate)

        self.test_btn = QPushButton("Test connection")
        self.test_btn.clicked.connect(self.test_connection)
        self.status_label = QLabel("")

        form = QFormLayout()
        form.addRow("RomM URL", self.url_edit)
        form.addRow("API token", self.token_edit)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        row = QHBoxLayout()
        row.addWidget(self.test_btn)
        row.addWidget(self.status_label, 1)
        layout.addLayout(row)

    def _invalidate(self, *_):
        if self._validated:
            self._validated = False
            self.completeChanged.emit()

    def isComplete(self) -> bool:  # noqa: N802 (Qt override)
        return self._validated

    def test_connection(self) -> None:
        url = self.url_edit.text().strip()
        token = self.token_edit.text().strip()
        self.status_label.setText("Testing…")
        self.test_btn.setEnabled(False)
        worker = CallableWorker(lambda: self._validate_fn(url, token))
        worker.done.connect(self._on_ok)
        worker.error.connect(self._on_err)
        worker.finished.connect(self._cleanup_worker)
        self._worker = worker
        worker.start()

    def _on_ok(self, _result) -> None:
        self._validated = True
        self.status_label.setText("Connection OK")
        self.completeChanged.emit()

    def _on_err(self, message: str) -> None:
        self._validated = False
        self.status_label.setText(message)
        self.completeChanged.emit()

    def _cleanup_worker(self) -> None:
        self.test_btn.setEnabled(True)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None


class PathsPage(QWizardPage):
    """ROMs root + RetroArch saves/states, with auto-detect. Only the ROMs root
    is required (saves/states fall back to defaults, matching the CLI)."""

    def __init__(self, detect_retroarch_fn, parent=None):
        super().__init__(parent)
        self.setTitle("Local folders")
        self._detect_retroarch_fn = detect_retroarch_fn
        self.sort_saves = False
        self.sort_states = False

        self.roms_edit = QLineEdit()
        self.saves_edit = QLineEdit()
        self.states_edit = QLineEdit()
        self.roms_edit.textChanged.connect(lambda *_: self.completeChanged.emit())

        form = QFormLayout()
        form.addRow("ROMs folder", self._with_browse(self.roms_edit))
        form.addRow("RetroArch saves", self._with_browse(self.saves_edit))
        form.addRow("RetroArch states", self._with_browse(self.states_edit))

        self.detect_btn = QPushButton("Detect from RetroArch")
        self.detect_btn.clicked.connect(self.detect_retroarch)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.detect_btn)

    def _with_browse(self, edit: QLineEdit):
        wrap = QHBoxLayout()
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(edit, 1)
        btn = QPushButton("Browse…")
        btn.clicked.connect(lambda: self._browse_into(edit))
        wrap.addWidget(btn)
        from PySide6.QtWidgets import QWidget
        holder = QWidget()
        holder.setLayout(wrap)
        return holder

    def _browse_into(self, edit: QLineEdit) -> None:
        picked = QFileDialog.getExistingDirectory(self, "Choose folder", edit.text())
        if picked:
            edit.setText(picked)

    def detect_retroarch(self) -> None:
        saves, states, sort_saves, sort_states = self._detect_retroarch_fn()
        if saves is not None:
            self.saves_edit.setText(str(saves))
        if states is not None:
            self.states_edit.setText(str(states))
        self.sort_saves = sort_saves
        self.sort_states = sort_states

    def isComplete(self) -> bool:  # noqa: N802 (Qt override)
        return bool(self.roms_edit.text().strip())


class SetupWizard(QWizard):
    """First-run wizard: Connection -> Paths -> Scan. Emits completed(settings,
    do_scan) on Finish. Backend access is injected (validate_fn,
    detect_retroarch_fn, persist) so the widget stays testable with fakes."""

    completed = Signal(object, bool)

    def __init__(self, *, validate_fn, detect_retroarch_fn, persist=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("romhop setup")
        self._detect_retroarch_fn = detect_retroarch_fn
        import romhop.config as config
        self._persist = persist or config.save_settings

        self.connection_page = ConnectionPage(validate_fn)
        self.addPage(self.connection_page)

        self.paths_page = PathsPage(detect_retroarch_fn)
        self.addPage(self.paths_page)
