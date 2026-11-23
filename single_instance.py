import hashlib
import os
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


def server_name_for_data_dir(data_dir: str) -> str:
    normalized = os.path.abspath(data_dir or os.path.expanduser("~")).lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"Capcraft_SingleInstance_{digest}"


class SingleInstanceBridge(QObject):
    """Ensure only one Capcraft instance runs per data directory and forward activation."""

    activated = pyqtSignal(str)

    def __init__(self, data_dir: str, parent=None):
        super().__init__(parent)
        self.server_name = server_name_for_data_dir(data_dir)
        self.server = None

    def try_notify_existing(self, message: str = "ACTIVATE_LAUNCHER", timeout_ms: int = 400) -> bool:
        socket = QLocalSocket(self)
        socket.connectToServer(self.server_name)
        if not socket.waitForConnected(timeout_ms):
            socket.abort()
            return False
        payload = (message or "ACTIVATE_LAUNCHER").encode("utf-8")
        socket.write(payload)
        socket.flush()
        socket.waitForBytesWritten(timeout_ms)
        socket.disconnectFromServer()
        return True

    def start_listening(self) -> bool:
        if self.server is not None:
            return True
        QLocalServer.removeServer(self.server_name)
        server = QLocalServer(self)
        if not server.listen(self.server_name):
            return False
        server.newConnection.connect(self._handle_new_connection)
        self.server = server
        return True

    def _handle_new_connection(self):
        if self.server is None:
            return
        while self.server.hasPendingConnections():
            client = self.server.nextPendingConnection()
            if client is None:
                continue
            client.waitForReadyRead(200)
            raw = bytes(client.readAll()).decode("utf-8", errors="ignore").strip()
            client.disconnectFromServer()
            client.deleteLater()
            self.activated.emit(raw or "ACTIVATE_LAUNCHER")

    def close(self):
        if self.server is not None:
            self.server.close()
            QLocalServer.removeServer(self.server_name)
            self.server = None
