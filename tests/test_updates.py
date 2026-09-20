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


if __name__ == '__main__': unittest.main()
