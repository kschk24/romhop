from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)


class PullConflictDialog(QDialog):
    """Ask user whether to take the remote copy or keep the local one."""

    def __init__(self, file_name: str, remote_updated: str | None,
                 local_mtime: datetime, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save conflict")
        self.setModal(True)

        local_str = local_mtime.strftime("%Y-%m-%d %H:%M:%S")
        remote_str = remote_updated or "unknown"

        msg = QLabel(
            f"<b>{file_name}</b> differs from the RomM copy.<br><br>"
            f"<b>Local:</b> {local_str}<br>"
            f"<b>Remote:</b> {remote_str}<br><br>"
            "Which version do you want to keep?"
        )
        msg.setWordWrap(True)

        buttons = QDialogButtonBox()
        self._keep_btn = buttons.addButton("Keep local", QDialogButtonBox.RejectRole)
        self._take_btn = buttons.addButton("Take remote", QDialogButtonBox.AcceptRole)
        self._keep_btn.clicked.connect(self.reject)
        self._take_btn.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(msg)
        layout.addWidget(buttons)

    @classmethod
    def ask(cls, file_name: str, remote_updated: str | None,
            local_mtime: datetime, parent=None) -> bool:
        """Return True to take remote, False to keep local."""
        dlg = cls(file_name, remote_updated, local_mtime, parent)
        return dlg.exec() == QDialog.Accepted
