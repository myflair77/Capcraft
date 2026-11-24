import json
import tempfile
import unittest
from unittest.mock import patch
from PyQt6.QtCore import QByteArray
from PyQt6.QtNetwork import QNetworkReply
from PyQt6.QtWidgets import QApplication, QWidget
from update_service import UpdateService, parse_manifest, version_tuple


class Reply:
    def __init__(self, data, failed=False): self.data, self.failed = data, failed
    def error(self):
        return QNetworkReply.NetworkError.TimeoutError if self.failed else QNetworkReply.NetworkError.NoError
    def readAll(self): return QByteArray(json.dumps(self.data).encode())
    def deleteLater(self): pass


class UpdatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.window = QWidget()
        self.service = UpdateService(self.window, self.temp.name)
        self.manifest = dict(schema_version=1, version='1.3.0', download_page='https://example.com/download', notes='<b>plain text</b>')
    def tearDown(self):
        if self.service.dialog: self.service.dialog.close()
        self.window.close()
        self.temp.cleanup()
    def test_versions(self):
        self.assertGreater(version_tuple('1.10'), version_tuple('1.9.9'))
        self.assertEqual(version_tuple('1.2'), version_tuple('1.2.0'))
        for value in ['1.3-beta', 'v1.3', None, '1', '1.2.3.4']:
            with self.assertRaises(ValueError): version_tuple(value)
    def test_rejects_unsafe_or_oversized_manifest(self):
        for url in ['file:///a.exe', 'http://example.com', 'javascript:alert(1)', 'https://a:b@example.com']:
            with self.assertRaises(ValueError): parse_manifest(json.dumps(dict(self.manifest, download_page=url)))
        with self.assertRaises(ValueError): parse_manifest('x'*65537)
        with self.assertRaises(ValueError): parse_manifest('[]')
    def test_skip_persists_manual_check_overrides(self):
        self.service.finished(Reply(self.manifest), False)
        box = self.service.dialog
        next(b for b in box.buttons() if '건너뛰기' in b.text()).click()
        self.assertEqual(self.service.state['skipped'], '1.3.0')
        self.service.finished(Reply(self.manifest), False)
        self.assertIsNone(self.service.dialog)
        self.service.finished(Reply(self.manifest), True)
        self.assertIsNotNone(self.service.dialog)
        self.assertEqual(UpdateService(self.window, self.temp.name).state['skipped'], '1.3.0')
    def test_browser_only_after_explicit_download_click(self):
        with patch('update_service.QDesktopServices.openUrl', return_value=True) as opened:
            self.service.finished(Reply(self.manifest), True)
            opened.assert_not_called()
            next(b for b in self.service.dialog.buttons() if '페이지' in b.text()).click()
            self.assertEqual(opened.call_args.args[0].toString(), self.manifest['download_page'])
    def test_disabled_throttled_and_offline(self):
        with patch.object(self.service.manager, 'get') as get:
            self.service.set_enabled(False); self.service.check(); get.assert_not_called()
        self.service.finished(Reply({}, True), False)
        self.assertIsNone(self.service.dialog)
        self.assertNotIn('checked_at', self.service.state)
        self.service.finished(Reply(dict(self.manifest,version='1.2')), True)
        self.assertIn('최신', self.service.dialog.text())

    def test_manifest_supports_optional_direct_update_fields(self):
        good_sha = 'a' * 64
        full = dict(
            self.manifest,
            installer_url='https://github.com/myflair77/Capcraft/releases/download/v1.3.0/Capcraft_Setup_v1.3.0.exe',
            sha256=good_sha,
            size='610 MB',
        )
        parsed = parse_manifest(json.dumps(full))
        self.assertEqual(parsed['sha256'], good_sha)
        self.assertEqual(parsed['installer_url'], full['installer_url'])
        with self.assertRaises(ValueError):
            parse_manifest(json.dumps(dict(full, sha256='not-a-sha')))
        with self.assertRaises(ValueError):
            parse_manifest(json.dumps(dict(full, installer_url='http://insecure.example/a.exe')))

    def test_direct_update_verifies_sha256_and_launches_installer(self):
        import hashlib
        payload = b'fake-installer-binary-content'
        expected_sha = hashlib.sha256(payload).hexdigest()
        quit_called = []
        svc = UpdateService(self.window, self.temp.name, on_quit_for_update=lambda: quit_called.append(True))
        manifest = dict(
            self.manifest,
            installer_url='https://github.com/myflair77/Capcraft/releases/download/v1.3.0/Capcraft_Setup_v1.3.0.exe',
            sha256=expected_sha,
            size='1 MB',
        )

        class FakeSignal:
            def connect(self, fn): pass

        class FakeDownloadReply:
            def __init__(self, content):
                self._buf = content
                self.readyRead = FakeSignal()
                self.downloadProgress = FakeSignal()
                self.finished = FakeSignal()
            def error(self): return QNetworkReply.NetworkError.NoError
            def readAll(self):
                data, self._buf = self._buf, b''
                return QByteArray(data)
            def abort(self): pass
            def deleteLater(self): pass

        fake_reply = FakeDownloadReply(payload)
        with patch.object(svc.manager, 'get', return_value=fake_reply), \
             patch('update_service.launch_installer', return_value=True) as launched:
            # Auto check shows notice dialog with '지금 업데이트' button.
            svc.finished(Reply(manifest), False)
            update_btn = next(b for b in svc.dialog.buttons() if '지금 업데이트' in b.text())
            update_btn.click()
            svc._on_download_finished(fake_reply, manifest)
            launched.assert_called_once()
            self.assertEqual(quit_called, [True])

        # Manual '지금 업데이트' button starts direct update immediately without extra dialog.
        quit_called.clear()
        fake_reply2 = FakeDownloadReply(payload)
        with patch.object(svc.manager, 'get', return_value=fake_reply2), \
             patch('update_service.launch_installer', return_value=True) as launched2:
            svc.finished(Reply(manifest), True)
            self.assertIsNone(svc.dialog)
            self.assertIsNotNone(svc.download_reply)
            svc._on_download_finished(fake_reply2, manifest)
            launched2.assert_called_once()
            self.assertEqual(quit_called, [True])

    def test_direct_update_rejects_sha256_mismatch(self):
        payload = b'tampered-installer-binary'
        wrong_sha = '0' * 64
        svc = UpdateService(self.window, self.temp.name)
        manifest = dict(
            self.manifest,
            installer_url='https://github.com/myflair77/Capcraft/releases/download/v1.3.0/Capcraft_Setup_v1.3.0.exe',
            sha256=wrong_sha,
        )

        class FakeSignal:
            def connect(self, fn): pass

        class FakeDownloadReply:
            def __init__(self, content):
                self._buf = content
                self.readyRead = FakeSignal()
                self.downloadProgress = FakeSignal()
                self.finished = FakeSignal()
            def error(self): return QNetworkReply.NetworkError.NoError
            def readAll(self):
                data, self._buf = self._buf, b''
                return QByteArray(data)
            def abort(self): pass
            def deleteLater(self): pass

        fake_reply = FakeDownloadReply(payload)
        with patch.object(svc.manager, 'get', return_value=fake_reply), \
             patch('update_service.launch_installer', return_value=True) as launched:
            svc.start_direct_update(manifest)
            part_path = svc._download_part_path
            svc._on_download_finished(fake_reply, manifest)
            launched.assert_not_called()
            self.assertFalse(part_path.exists())
            self.assertIsNotNone(svc.dialog)
            self.assertIn('SHA-256', svc.dialog.text())
            svc.dialog.close()


if __name__ == '__main__': unittest.main()
