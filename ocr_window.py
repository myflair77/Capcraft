"""Movable non-modal native OCR result window, independent of the web canvas."""
import json
import uuid
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPlainTextEdit, QPushButton, QApplication
from ocr_languages import LANGUAGES


class OCRWindow(QWidget):
    retry = pyqtSignal(str)
    formatted = pyqtSignal(str)

    def __init__(self, service, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle('Capcraft · OCR 텍스트')
        self.resize(780,620)
        self.service=service
        self.token=None
        self.result={}
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('PC 내부 처리 · 원본 캡처 기준'))
        row=QHBoxLayout();layout.addLayout(row)
        self.language=QComboBox()
        for code,label in LANGUAGES.items():self.language.addItem(label,code)
        row.addWidget(self.language)
        self.mode=QComboBox();self.mode.addItems(['원문 그대로','문단 정리']);row.addWidget(self.mode)
        self.mode.setCurrentIndex(1)
        self.mode.currentIndexChanged.connect(self.show_text)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        self.text=QPlainTextEdit();self.text.setReadOnly(True);layout.addWidget(self.text)
        actions=QHBoxLayout();layout.addLayout(actions)
        retry=QPushButton('다시 인식');retry.clicked.connect(lambda:self.retry.emit(self.language.currentData()));actions.addWidget(retry)
        actions.addStretch()
        copy=QPushButton('텍스트를 복사');copy.clicked.connect(self.copy_text);actions.addWidget(copy)
        close=QPushButton('닫기');close.clicked.connect(self.close);actions.addWidget(close)
        service.finished.connect(self.format_finished)

    def update_result(self,result):
        self.token=None
        self.result=result
        self.language.setCurrentIndex(max(0,self.language.findData(result.get('languageMode','auto'))))
        self.show_text()

    def copy_text(self):
        QApplication.clipboard().setText(self.text.toPlainText())
        self.status.setText('현재 표시된 텍스트를 복사했습니다.')

    def show_text(self):
        if self.mode.currentIndex()==0:
            self.text.setPlainText(self.result.get('text',''))
            labels=[LANGUAGES.get(code,'판별 불확실') for code in self.result.get('languages',[])]
            self.status.setText('인식 언어: '+(', '.join(labels) or '판별 불확실')+' · 중요한 문구는 원본과 비교해 주세요.')
        elif 'formattedText' in self.result:
            self.text.setPlainText(self.result['formattedText'])
            self.status.setText(self.result.get('formatNotes','문단 정리 완료'))
        else:
            self.text.setPlainText(self.result.get('text',''))
            self.status.setText('PC 내부에서 문단을 정리하고 있습니다… 완료 전까지 원문을 표시합니다.')
            if not self.token:
                self.token='format-'+uuid.uuid4().hex
                self.service.submit(self.token,json.dumps(self.result,ensure_ascii=False),format_only=True)
        review=self.result.get('reviewCount',0)
        low=self.result.get('lowConfidence',0)
        if review or low:
            self.status.setText(self.status.text()+f' · 원본 대조 필요: 부분 인식 {review}곳, 낮은 신뢰도 {low}줄')
            details=[]
            for line in self.result.get('lines',[]):
                for item in line.get('review',[]):
                    details.append(line.get('text','')+'\n'+item.get('reason','')+': '+item.get('candidate','')+
                                   (' / '+item['alternative'] if item.get('alternative') else ''))
            self.status.setToolTip('\n\n'.join(details))
        else:
            self.status.setToolTip('')

    def format_finished(self,token,payload):
        if token!=self.token:return
        self.token=None
        result=json.loads(payload)
        if result.get('error'):
            self.mode.setCurrentIndex(0)
            self.status.setText(result['error'])
            return
        self.result.update(result)
        self.formatted.emit(payload)
        self.show_text()
