"""Non-blocking version notices with verified one-click installer updates."""
import ctypes
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit
from PyQt6.QtCore import QObject, QUrl, Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog
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


def sha256_hex(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError('Invalid SHA-256')
    return value.lower()


def parse_manifest(raw):
    if len(raw) > 65536:
        raise ValueError('Manifest too large')
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('Unsupported manifest')
    version_tuple(data.get('version'))
    https_url(data.get('download_page'))
    notes = data.get('notes', '')
    if not isinstance(notes, str) or len(notes) > 4000:
        raise ValueError('Invalid notes')
    result = dict(version=data['version'], download_page=data['download_page'], notes=notes)
    if 'installer_url' in data and data['installer_url']:
        result['installer_url'] = https_url(data['installer_url'])
    if 'sha256' in data and data['sha256']:
        result['sha256'] = sha256_hex(data['sha256'])
    if 'size' in data and data['size']:
        size = data['size']
        if not isinstance(size, str) or len(size) > 64:
            raise ValueError('Invalid size')
        result['size'] = size
    return result


def launch_installer(installer_path):
    """Launch the downloaded Inno Setup installer in silent upgrade mode."""
    path_str = str(installer_path)
    params = "/SILENT /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS"
    if sys.platform == "win32":
        try:
            rc = ctypes.windll.shell32.ShellExecuteW(
                None, "open", path_str, params, str(Path(path_str).parent), 1
            )
            return int(rc) > 32
        except Exception:
            return False
    return False


class UpdateService(QObject):
    def __init__(self, parent, data_dir, endpoint=UPDATE_MANIFEST_URL, on_quit_for_update=None):
        super().__init__(parent)
        self.path = Path(data_dir) / '.capcraft_updates.json'
        self.endpoint = endpoint
        self.on_quit_for_update = on_quit_for_update
        self.manager = QNetworkAccessManager(self)
        self.reply = None
        self.dialog = None
        self.download_reply = None
        self.progress_dialog = None
        self._download_file = None
        self._download_part_path = None
        self._download_final_path = None
        self._download_hasher = None
        self._download_expected_sha256 = None
        self._download_cancelled = False
        self.state = {}
        try:
            value = json.loads(self.path.read_text(encoding='utf8'))
            if isinstance(value, dict):
                self.state = value
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            atomic_write(self.path, json.dumps(self.state).encode('utf8'))
        except OSError:
            pass

    def set_enabled(self, enabled):
        self.state['enabled'] = bool(enabled)
        self.save()

    def message(self, text):
        if self.dialog:
            return
        box = QMessageBox(self.parent())
        box.setWindowTitle('Capcraft 업데이트')
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(text)
        self.dialog = box
        box.finished.connect(lambda _: setattr(self, 'dialog', None))
        box.open()

    def check(self, manual=False):
        if self.reply or self.dialog or self.download_reply:
            return
        if not manual:
            if not self.state.get('enabled', True):
                return
            try:
                elapsed = time.time() - float(self.state.get('checked_at', 0))
                if 0 <= elapsed < 86400:
                    return
            except (ValueError, TypeError):
                pass
        if not self.endpoint:
            if manual:
                self.message('아직 업데이트 배포 주소가 설정되지 않았습니다.')
            return
        try:
            https_url(self.endpoint)
        except ValueError:
            if manual:
                self.message('업데이트 배포 주소가 올바르지 않습니다.')
            return
        request = QNetworkRequest(QUrl(self.endpoint))
        request.setTransferTimeout(8000)
        request.setRawHeader(b'Cache-Control', b'no-cache')
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.SameOriginRedirectPolicy,
        )
        self.reply = self.manager.get(request)
        reply = self.reply
        reply.downloadProgress.connect(
            lambda received, total: reply.abort() if max(received, total) > 65536 else None
        )
        reply.readyRead.connect(
            lambda: reply.abort() if reply.bytesAvailable() > 65536 else None
        )
        reply.finished.connect(lambda: self.finished(reply, manual))

    def finished(self, reply, manual):
        self.reply = None
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                raise ValueError('Network failure')
            data = parse_manifest(bytes(reply.readAll()))
            self.state['checked_at'] = time.time()
            self.save()
            if version_tuple(data['version']) <= version_tuple(APP_VERSION):
                if manual:
                    self.message(f'현재 최신 버전입니다. (v{APP_VERSION})')
                return
            if not manual and (not self.state.get('enabled', True) or self.state.get('skipped') == data['version']):
                return
            can_direct = bool(data.get('installer_url') and data.get('sha256'))
            if manual and can_direct:
                # User explicitly clicked '지금 업데이트': start direct download & install immediately.
                self.start_direct_update(data)
                return
            box = QMessageBox(self.parent())
            box.setWindowTitle('Capcraft 새 버전 안내')
            box.setTextFormat(Qt.TextFormat.PlainText)
            host = urlsplit(data['download_page']).hostname
            size_line = f"\n설치파일 크기: {data['size']}" if data.get('size') else ""
            box.setText(
                f"Capcraft {data['version']} 업데이트가 있습니다.\n"
                f"현재 버전: {APP_VERSION}{size_line}\n\n"
                f"{data['notes']}\n\n"
                f"다운로드 사이트: {host}"
            )
            update_now = None
            if can_direct:
                update_now = box.addButton('지금 업데이트', QMessageBox.ButtonRole.AcceptRole)
            download = box.addButton('다운로드 페이지 열기', QMessageBox.ButtonRole.ActionRole)
            later = box.addButton('나중에', QMessageBox.ButtonRole.RejectRole)
            skip = box.addButton('이 버전 건너뛰기', QMessageBox.ButtonRole.ActionRole)
            box.setDefaultButton(update_now if update_now is not None else later)
            self.dialog = box

            def selected(_):
                self.dialog = None
                clicked = box.clickedButton()
                if clicked is skip:
                    self.state['skipped'] = data['version']
                    self.save()
                elif update_now is not None and clicked is update_now:
                    self.start_direct_update(data)
                elif clicked is download:
                    if not QDesktopServices.openUrl(QUrl(data['download_page'])):
                        self.message('브라우저를 열지 못했습니다. 다시 시도해 주세요.')

            box.finished.connect(selected)
            box.open()
        except (ValueError, TypeError, UnicodeError):
            if manual:
                self.message('업데이트를 확인하지 못했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.')
        finally:
            reply.deleteLater()

    def _cleanup_download_handles(self, remove_part=False):
        if self._download_file is not None:
            try:
                self._download_file.close()
            except OSError:
                pass
            self._download_file = None
        if remove_part and self._download_part_path is not None:
            try:
                if self._download_part_path.exists():
                    self._download_part_path.unlink()
            except OSError:
                pass
        if self.progress_dialog is not None:
            try:
                self.progress_dialog.close()
                self.progress_dialog.deleteLater()
            except Exception:
                pass
            self.progress_dialog = None

    def start_direct_update(self, data):
        """Download installer with progress bar, verify SHA-256, and launch silent upgrade."""
        if self.download_reply is not None:
            return
        try:
            url = https_url(data.get('installer_url'))
            expected_sha = sha256_hex(data.get('sha256'))
            ver = data['version']
            version_tuple(ver)
        except (ValueError, KeyError):
            self.message('업데이트 정보가 올바르지 않아 자동 업데이트를 진행할 수 없습니다.')
            return

        update_dir = Path(tempfile.gettempdir()) / 'CapcraftUpdate'
        try:
            update_dir.mkdir(parents=True, exist_ok=True)
            final_path = update_dir / f'Capcraft_Setup_v{ver}.exe'
            part_path = update_dir / f'Capcraft_Setup_v{ver}.exe.part'
            self._download_file = open(part_path, 'wb')
        except OSError:
            self.message('임시 폴더에 업데이트 파일을 저장할 수 없습니다.')
            return

        self._download_part_path = part_path
        self._download_final_path = final_path
        self._download_hasher = hashlib.sha256()
        self._download_expected_sha256 = expected_sha
        self._download_cancelled = False

        progress = QProgressDialog(f'Capcraft {ver} 업데이트를 다운로드하고 있습니다...', '취소', 0, 100, self.parent())
        progress.setWindowTitle('Capcraft 업데이트')
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.canceled.connect(self.cancel_direct_update)
        progress.show()
        self.progress_dialog = progress

        request = QNetworkRequest(QUrl(url))
        request.setTransferTimeout(60000)
        request.setRawHeader(b'Cache-Control', b'no-cache')
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        reply = self.manager.get(request)
        self.download_reply = reply
        reply.readyRead.connect(lambda: self._on_download_ready_read(reply))
        reply.downloadProgress.connect(self._on_download_progress)
        reply.finished.connect(lambda: self._on_download_finished(reply, data))

    def cancel_direct_update(self):
        self._download_cancelled = True
        if self.download_reply is not None:
            self.download_reply.abort()

    def _on_download_ready_read(self, reply):
        if self._download_file is None or self._download_cancelled:
            return
        chunk = bytes(reply.readAll())
        if not chunk:
            return
        try:
            self._download_file.write(chunk)
            self._download_hasher.update(chunk)
        except OSError:
            self._download_cancelled = True
            reply.abort()

    def _on_download_progress(self, received, total):
        if self.progress_dialog is None or self._download_cancelled:
            return
        mb_recv = received / (1024 * 1024)
        if total > 0:
            pct = min(100, int(received * 100 / total))
            mb_total = total / (1024 * 1024)
            self.progress_dialog.setMaximum(100)
            self.progress_dialog.setValue(pct)
            self.progress_dialog.setLabelText(
                f'업데이트 다운로드 중... {mb_recv:.1f} / {mb_total:.1f} MB ({pct}%)'
            )
        else:
            self.progress_dialog.setMaximum(0)
            self.progress_dialog.setLabelText(f'업데이트 다운로드 중... {mb_recv:.1f} MB')

    def _on_download_finished(self, reply, data):
        self.download_reply = None
        try:
            if not self._download_cancelled and reply.error() == QNetworkReply.NetworkError.NoError:
                self._on_download_ready_read(reply)
                if self._download_file is not None:
                    self._download_file.flush()
                    self._download_file.close()
                    self._download_file = None

                actual_sha = self._download_hasher.hexdigest().lower() if self._download_hasher else ''
                if actual_sha != self._download_expected_sha256:
                    self._cleanup_download_handles(remove_part=True)
                    self.message('다운로드 파일의 무결성(SHA-256) 검증에 실패했습니다.\n다운로드 페이지에서 직접 받아 설치해 주세요.')
                    return

                if self._download_final_path.exists():
                    try:
                        self._download_final_path.unlink()
                    except OSError:
                        pass
                os.replace(self._download_part_path, self._download_final_path)
                self._cleanup_download_handles(remove_part=False)

                if launch_installer(self._download_final_path):
                    if callable(self.on_quit_for_update):
                        self.on_quit_for_update()
                    else:
                        app = QApplication.instance()
                        if app is not None:
                            app.quit()
                else:
                    self.message('업데이트 설치 프로그램 실행이 취소되었거나 실패했습니다.')
            elif self._download_cancelled:
                self._cleanup_download_handles(remove_part=True)
            else:
                self._cleanup_download_handles(remove_part=True)
                self.message('업데이트 다운로드 중 오류가 발생했습니다.\n잠시 후 다시 시도하거나 다운로드 페이지에서 직접 받아 주세요.')
        except OSError:
            self._cleanup_download_handles(remove_part=True)
            self.message('업데이트 파일을 준비하는 중 오류가 발생했습니다.')
        finally:
            reply.deleteLater()
