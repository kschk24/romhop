from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
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
