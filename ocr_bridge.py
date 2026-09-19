"""Single background OCR worker; Qt queued signal returns results to the UI thread."""
import json
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal
from ocr_engine import LocalOCR
from ocr_text import ParagraphFormatter


class OCRService(QObject):
    finished = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.engine = LocalOCR()
        self.formatter = ParagraphFormatter()
        self.pending = set()
        self.finished.connect(self._completed)

    def submit(self, token, data, format_only=False, language='auto'):
        if token in self.pending:
            return
        if len(self.pending) >= 3:
            self.finished.emit(token, json.dumps({'error':'OCR 처리 중입니다. 잠시 후 다시 눌러 주세요.'}, ensure_ascii=False))
            return
        self.pending.add(token)
        self.pool.start(OCRTask(self, token, data, format_only, language))

    def _completed(self, token, payload):
        self.pending.discard(token)


class OCRTask(QRunnable):
    def __init__(self, service, token, data, format_only=False, language='auto'):
        super().__init__()
        self.service, self.token, self.data = service, token, data
        self.format_only = format_only
        self.language=language

    def run(self):
        try:
            result = (self.service.formatter.format(json.loads(self.data)) if self.format_only
                      else self.service.engine.recognize(self.data,self.language))
        except Exception as error:
            result = {'error':str(error)[:350]}
        self.data = None
        self.service.finished.emit(self.token, json.dumps(result, ensure_ascii=False))
