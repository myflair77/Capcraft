"""Non-blocking version notices; never downloads or executes an installer."""
import json
import re
import time
from pathlib import Path
from urllib.parse import urlsplit
from PyQt6.QtCore import QObject, QUrl, Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import QMessageBox
from storage import atomic_write
from app_version import APP_VERSION, UPDATE_MANIFEST_URL


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,6}\.\d{1,6}(?:\.\d{1,6})?", value):
        raise ValueError('Invalid stable version')
    parts = tuple(map(int, value.split('.')))
    return parts + (0,) * (3 - len(parts))


def https_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError('Invalid URL')
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in value):
        raise ValueError('HTTPS required')
    return value


def parse_manifest(raw):
    if len(raw) > 65536: raise ValueError('Manifest too large')
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('Unsupported manifest')
    version_tuple(data.get('version'))
    https_url(data.get('download_page'))
    notes = data.get('notes', '')
    if not isinstance(notes, str) or len(notes) > 4000: raise ValueError('Invalid notes')
    return dict(version=data['version'], download_page=data['download_page'], notes=notes)


class UpdateService(QObject):
    def __init__(self, parent, data_dir, endpoint=UPDATE_MANIFEST_URL):
        super().__init__(parent)
        self.path = Path(data_dir) / '.capcraft_updates.json'
        self.endpoint = endpoint
        self.manager = QNetworkAccessManager(self)
        self.reply = None
        self.dialog = None
        self.state = {}
        try:
            value = json.loads(self.path.read_text(encoding='utf8'))
            if isinstance(value, dict): self.state = value
        except (OSError, ValueError): pass

    def save(self):
        try: atomic_write(self.path, json.dumps(self.state).encode('utf8'))
        except OSError: pass

    def set_enabled(self, enabled):
        self.state['enabled'] = bool(enabled)
        self.save()

    def message(self, text):
        if self.dialog: return
        box = QMessageBox(self.parent())
        box.setWindowTitle('Capcraft 업데이트')
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(text)
        self.dialog = box
        box.finished.connect(lambda _: setattr(self, 'dialog', None))
        box.open()

    def check(self, manual=False):
        if self.reply or self.dialog: return
        if not manual:
            if not self.state.get('enabled', True): return
            try:
                elapsed = time.time() - float(self.state.get('checked_at', 0))
                if 0 <= elapsed < 86400: return
            except (ValueError, TypeError): pass
        if not self.endpoint:
            if manual: self.message('아직 업데이트 배포 주소가 설정되지 않았습니다.')
            return
        try: https_url(self.endpoint)
        except ValueError:
            if manual: self.message('업데이트 배포 주소가 올바르지 않습니다.')
            return
        request = QNetworkRequest(QUrl(self.endpoint))
        request.setTransferTimeout(8000)
        request.setRawHeader(b'Cache-Control', b'no-cache')
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.SameOriginRedirectPolicy)
        self.reply = self.manager.get(request)
        reply = self.reply
        reply.downloadProgress.connect(lambda received, total: reply.abort() if max(received, total) > 65536 else None)
        reply.readyRead.connect(lambda: reply.abort() if reply.bytesAvailable() > 65536 else None)
        reply.finished.connect(lambda: self.finished(reply, manual))

    def finished(self, reply, manual):
        self.reply = None
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError: raise ValueError('Network failure')
            data = parse_manifest(bytes(reply.readAll()))
            self.state['checked_at'] = time.time()
            self.save()
            if version_tuple(data['version']) <= version_tuple(APP_VERSION):
                if manual: self.message(f'현재 최신 버전입니다. (v{APP_VERSION})')
                return
            if not manual and (not self.state.get('enabled', True) or self.state.get('skipped') == data['version']): return
            box = QMessageBox(self.parent())
            box.setWindowTitle('Capcraft 새 버전 안내')
            box.setTextFormat(Qt.TextFormat.PlainText)
            host = urlsplit(data['download_page']).hostname
            box.setText(f"Capcraft {data['version']} 업데이트가 있습니다.\n현재 버전: {APP_VERSION}\n\n{data['notes']}\n\n다운로드 사이트: {host}")
            download = box.addButton('다운로드 페이지 열기', QMessageBox.ButtonRole.AcceptRole)
            later = box.addButton('나중에', QMessageBox.ButtonRole.RejectRole)
            skip = box.addButton('이 버전 건너뛰기', QMessageBox.ButtonRole.ActionRole)
            box.setDefaultButton(later)
            self.dialog = box
            def selected(_):
                self.dialog = None
                if box.clickedButton() is skip:
                    self.state['skipped'] = data['version']; self.save()
                elif box.clickedButton() is download:
                    if not QDesktopServices.openUrl(QUrl(data['download_page'])):
                        self.message('브라우저를 열지 못했습니다. 다시 시도해 주세요.')
            box.finished.connect(selected)
            box.open()
        except (ValueError, TypeError, UnicodeError):
            if manual: self.message('업데이트를 확인하지 못했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.')
        finally: reply.deleteLater()
