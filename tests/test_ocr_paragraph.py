import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ocr_text import validate_spacing_models


class ParagraphTests(unittest.TestCase):
    def test_missing_models_rejected_before_native_constructor(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'cong.mdl'):
                validate_spacing_models(directory)

    def test_native_window_worker_and_shutdown_in_subprocess(self):
        # Capture fatal native failures as a failed test, not a dead test runner.
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
        result = subprocess.run(
            [sys.executable, '-X', 'faulthandler', str(Path(__file__)), '--worker'],
            cwd=ROOT, env=env, capture_output=True, timeout=90)
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr).decode('utf-8', 'replace'))
        self.assertIn(b'PARAGRAPH_PASS', result.stdout)


def worker():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer
    from ocr_bridge import OCRService
    from ocr_window import OCRWindow
    from ocr_text import compact
    app = QApplication([])
    service = OCRService()
    window = OCRWindow(service)
    raw = "엔씨가 선보인'아스트라에 오라티오'부스도 관람객들이 몰렸다.개장 직후 시연\n대기시간이 길었다.\n\n역할수행게임(R\nPG)이다. 도쿄와 비\n슷한 풍경에서 사\n건을 해결한다."
    assert window.mode.currentIndex() == 1, 'Paragraph mode must be the default'
    completed = []

    def finish(payload):
        data = json.loads(payload)
        text = data['formattedText']
        assert compact(raw) == compact(text)
        assert '(RPG)' in text and '비슷한' in text and '사건을' in text
        assert "선보인 '아스트라에 오라티오' 부스" in text
        assert '몰렸다. 개장' in text
        completed.append(True)
        QTimer.singleShot(0, verify_cached)

    def verify_cached():
        assert window.text.toPlainText() == window.result['formattedText']
        window.mode.setCurrentIndex(0)
        assert window.text.toPlainText() == raw
        window.mode.setCurrentIndex(1)
        window.copy_text()
        assert app.clipboard().text() == window.result['formattedText']
        cached = OCRWindow(service)
        cached.update_result(dict(window.result))
        assert cached.mode.currentIndex() == 1 and cached.token is None
        assert cached.text.toPlainText() == window.result['formattedText']
        cached.close()
        # A failed formatting job falls back to readable raw text.
        window.result = {'text': raw}
        window.token = 'test-failure'
        window.format_finished('test-failure', json.dumps({'error': 'test error'}))
        assert window.mode.currentIndex() == 0 and window.text.toPlainText() == raw
        assert window.status.text() == 'test error'
        window.close()
        app.quit()

    window.formatted.connect(finish)
    QTimer.singleShot(0, lambda: window.update_result({'text': raw}))
    QTimer.singleShot(60000, app.quit)
    app.exec()
    service.pool.waitForDone()
    assert completed, 'Paragraph worker did not finish'
    print('PARAGRAPH_PASS', flush=True)


if __name__ == '__main__':
    if '--worker' in sys.argv:
        worker()
    else:
        unittest.main()
