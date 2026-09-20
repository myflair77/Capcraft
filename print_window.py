"""Capcraft print preview; preview and physical output share one paint path."""
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPageLayout, QPageSize, QColor, QBrush
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QComboBox, QFrame, QMessageBox, QGraphicsView)
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewWidget, QPrintDialog


class PrintWindow(QDialog):
    def __init__(self, image, parent=None):
        super().__init__(parent)
        if image.isNull():
            raise ValueError('인쇄할 이미지가 없습니다.')
        self.image = image
        self.setWindowTitle('Capcraft · 인쇄 미리보기')
        self.resize(1060, 760)
        self.setMinimumSize(760, 560)
        self.printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        self.printer.setDocName('Capcraft')
        self.printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        self.setStyleSheet('''
            QDialog { background: #f6f8fc; }
            QLabel { color: #334155; font-family: "맑은 고딕"; font-size: 13px; }
            QLabel#heading { color: #1e293b; font-size: 24px; font-weight: 700; }
            QLabel#muted { color: #64748b; font-size: 12px; }
            QFrame#card { background: white; border: 1px solid #e2e8f0; border-radius: 12px; }
            QPushButton, QComboBox { background: white; color: #334155; border: 1px solid #cbd5e1;
                border-radius: 7px; padding: 9px 14px; font-size: 13px; }
            QPushButton:hover, QComboBox:hover { background: #eff6ff; border-color: #93b4ff; }
            QPushButton:focus, QComboBox:focus { border: 1px solid #2563eb; }
            QPushButton#primary { background: #2563eb; color: white; border-color: #2563eb; font-weight: 600; }
            QPushButton#primary:hover { background: #1d4ed8; }
            QComboBox QAbstractItemView { background: white; color: #334155; selection-background-color: #dbeafe; }
        ''')
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(18)
        heading = QLabel('인쇄 미리보기'); heading.setObjectName('heading')
        root.addWidget(heading)
        subtitle = QLabel('용지에 맞춘 결과를 확인하고 인쇄하세요.'); subtitle.setObjectName('muted')
        root.addWidget(subtitle)
        body = QHBoxLayout(); body.setSpacing(18); root.addLayout(body, 1)
        card = QFrame(); card.setObjectName('card'); card.setFixedWidth(230)
        settings = QVBoxLayout(card); settings.setContentsMargins(18, 20, 18, 20); settings.setSpacing(12)
        body.addWidget(card)
        settings.addWidget(QLabel('용지 크기'))
        self.paper = QComboBox()
        for name, page_id in [('A4', QPageSize.PageSizeId.A4), ('A3', QPageSize.PageSizeId.A3), ('Letter', QPageSize.PageSizeId.Letter)]:
            self.paper.addItem(name, page_id)
        settings.addWidget(self.paper)
        settings.addSpacing(8); settings.addWidget(QLabel('용지 방향'))
        self.orientation = QComboBox(); self.orientation.addItems(['세로', '가로'])
        settings.addWidget(self.orientation)
        settings.addSpacing(8); settings.addWidget(QLabel('이미지 배치'))
        note = QLabel('비율 유지 · 용지에 맞춤\n인쇄 가능 영역의 가운데 배치')
        note.setWordWrap(True); note.setObjectName('muted'); settings.addWidget(note)
        settings.addStretch()
        info = QLabel(f'원본 이미지\n{image.width():,} × {image.height():,} px')
        info.setObjectName('muted'); settings.addWidget(info)
        preview_column = QVBoxLayout(); body.addLayout(preview_column, 1)
        controls = QHBoxLayout(); preview_column.addLayout(controls)
        controls.addWidget(QLabel('미리보기')); controls.addStretch()
        for label, action in [('-', lambda: self.preview.zoomOut()), ('+', lambda: self.preview.zoomIn()), ('페이지 맞춤', lambda: self.preview.fitInView())]:
            button = QPushButton(label); button.clicked.connect(action); controls.addWidget(button)
            if label in ('-', '+'):
                button.setAccessibleName('축소' if label == '-' else '확대')
        self.preview = QPrintPreviewWidget(self.printer, self)
        for view in self.preview.findChildren(QGraphicsView):
            view.setBackgroundBrush(QBrush(QColor('#e8edf5')))
            view.setFrameShape(QFrame.Shape.NoFrame)
        self.preview.paintRequested.connect(self.paint_page)
        preview_column.addWidget(self.preview, 1)
        footer = QHBoxLayout(); root.addLayout(footer)
        help_text = QLabel('다음 단계에서 프린터와 인쇄 매수를 선택합니다.'); help_text.setObjectName('muted')
        footer.addWidget(help_text); footer.addStretch()
        close = QPushButton('닫기'); close.clicked.connect(self.reject); footer.addWidget(close)
        self.print_button = QPushButton('인쇄…'); self.print_button.setObjectName('primary')
        self.print_button.clicked.connect(self.print_document); footer.addWidget(self.print_button)
        self.paper.currentIndexChanged.connect(self.update_layout)
        self.orientation.currentIndexChanged.connect(self.update_layout)
        self.preview.updatePreview()

    def update_layout(self):
        self.printer.setPageSize(QPageSize(self.paper.currentData()))
        self.printer.setPageOrientation(QPageLayout.Orientation.Landscape if self.orientation.currentIndex() else QPageLayout.Orientation.Portrait)
        self.preview.updatePreview()
        self.preview.fitInView()

    def paint_page(self, printer):
        painter = QPainter()
        if not painter.begin(printer):
            return False
        try:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            rect = QRectF(painter.viewport())
            scale = min(rect.width() / self.image.width(), rect.height() / self.image.height())
            width, height = self.image.width() * scale, self.image.height() * scale
            target = QRectF(rect.x() + (rect.width()-width)/2, rect.y() + (rect.height()-height)/2, width, height)
            painter.drawImage(target, self.image)
        finally:
            painter.end()
        return True

    def print_document(self):
        dialog = QPrintDialog(self.printer, self)
        dialog.setWindowTitle('Capcraft · 프린터 선택')
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.paint_page(self.printer):
                self.accept()
            else:
                QMessageBox.warning(self, '인쇄 실패', '프린터를 시작할 수 없습니다. 연결과 설정을 확인해 주세요.')
