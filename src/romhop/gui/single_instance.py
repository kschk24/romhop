from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

_KEY = "romhop-gui"
_MSG = b"show"


class SingleInstance(QObject):
    """Named-socket single-instance gate.

    First launch: ``is_running()`` returns False, then ``listen()`` claims the
    key and incoming connections emit ``activated``. A later launch:
    ``is_running()`` connects to the primary, sends a "show" message (which the
    primary turns into ``activated`` -> raise its window), and returns True so the
    caller can exit.
    """

    activated = Signal()

    def __init__(self, key: str = _KEY, parent=None):
        super().__init__(parent)
        self._key = key
        self._server: QLocalServer | None = None

    def is_running(self) -> bool:
        sock = QLocalSocket()
        sock.connectToServer(self._key)
        if not sock.waitForConnected(200):
            return False
        sock.write(_MSG)
        sock.flush()
        sock.waitForBytesWritten(200)
        sock.disconnectFromServer()
        return True

    def listen(self) -> None:
        # Clear any socket left by a crashed instance, else listen() fails on
        # "address in use".
        QLocalServer.removeServer(self._key)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)
        self._server.listen(self._key)

    def _on_connection(self) -> None:
        conn = self._server.nextPendingConnection()
        if conn is None:
            return
        conn.readyRead.connect(lambda: self._read(conn))

    def _read(self, conn) -> None:
        if _MSG in bytes(conn.readAll()):
            self.activated.emit()
        conn.disconnectFromServer()

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None
