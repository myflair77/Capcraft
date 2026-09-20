"""Offline preview QA; writes a PDF, never sends a physical print job."""
import os
import sys
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QColor, QPainter, QFont, QPageLayout, QFontDatabase
from PyQt6.QtPrintSupport import QPrinter
from print_window import PrintWindow

app = QApplication([])
font_path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'malgun.ttf'
if font_path.exists():
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    families = QFontDatabase.applicationFontFamilies(font_id)
    if families:
        app.setFont(QFont(families[0], 10))
image = QImage(1000, 640, QImage.Format.Format_RGB32)
image.fill(QColor('#eff6ff'))
painter = QPainter(image)
painter.fillRect(45, 45, 910, 550, QColor('white'))
painter.setPen(QColor('#2563eb')); painter.setFont(QFont(app.font().family(), 32))
painter.drawText(90, 145, 'Capcraft')
painter.setPen(QColor('#334155')); painter.setFont(QFont(app.font().family(), 18))
painter.drawText(90, 205, 'Capture. Edit. Print.')
for i, color in enumerate(['#2563eb', '#93c5fd', '#dbeafe']):
    painter.fillRect(90 + i*270, 260, 240, 230, QColor(color))
painter.end()
output = Path('test-results'); output.mkdir(exist_ok=True)
window = PrintWindow(image)
window.show(); app.processEvents()
window.preview.fitInView(); app.processEvents()
window.grab().save(str(output / 'print-preview.png'))
window.orientation.setCurrentIndex(1)
assert window.printer.pageLayout().orientation() == QPageLayout.Orientation.Landscape
window.paper.setCurrentIndex(1)
app.processEvents()
assert window.preview.pageCount() == 1
window.printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
window.printer.setOutputFileName(str(output / 'print-preview.pdf'))
assert window.paint_page(window.printer)
assert (output / 'print-preview.pdf').stat().st_size > 1000
window.reject()
assert not window.isVisible()
print('PASS preview layout, orientation, paper size, single page, PDF output and close')
