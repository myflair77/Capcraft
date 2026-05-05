import sys
import os
import time
import base64
import ctypes
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QObject, pyqtSlot, QUrl, Qt, QByteArray
from PyQt6.QtGui import QImage, QPainter, QPixmap, QIcon
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
try:
    from PyQt6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False


def create_camera_icon():
    """사이드바 카메라 SVG와 동일한 아이콘 생성"""
    svg_bytes = QByteArray(
        b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        b' stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        b'<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>'
        b'<circle cx="12" cy="13" r="4"/>'
        b'</svg>'
    )
    if _HAS_SVG:
        renderer = QSvgRenderer(svg_bytes)
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)
    return QIcon()

from capture_engine import CaptureEngine

class Backend(QObject):
    def __init__(self, engine, view):
        super().__init__()
        self.engine = engine
        self.view = view

    @pyqtSlot(str)
    def start_capture(self, mode):
        # ★ 창을 완전히 숨긴 뒤 이벤트 큐 소진 후 스크린샷 촬영
        self.view.window().hide()
        QApplication.processEvents()   # 숨김 이벤트 즉시 처리
        time.sleep(0.45)               # 창 애니메이션·컴포지터 반영 대기
        QApplication.processEvents()   # 한 번 더 플러시

        try:
            image_base64 = self.engine.run_capture(mode)
        except Exception as e:
            print(f"Capture failed: {e}")
            image_base64 = None

        # 캡처 후 메인 윈도우 복원
        self.view.window().show()
        self.view.window().raise_()
        self.view.window().activateWindow()

        if image_base64:
            self.view.page().runJavaScript(f"window.receiveCapturedImage('{image_base64}')")

    @pyqtSlot(str)
    def copy_to_clipboard(self, base64_data):
        try:
            # "data:image/png;base64," 접두어 제거
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            img_data = base64.b64decode(base64_data)
            image = QImage.fromData(img_data)
            QApplication.clipboard().setImage(image)
        except Exception as e:
            print("Copy error:", e)

    @pyqtSlot(str)
    def print_image(self, base64_data):
        try:
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            img_data = base64.b64decode(base64_data)
            self.print_img_obj = QImage.fromData(img_data)
            
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            date_str = time.strftime("%Y%m%d_%H%M%S")
            printer.setOutputFileName(f"BH-Capture_{date_str}.pdf")
            
            dialog = QPrintPreviewDialog(printer, self.view.window())
            dialog.paintRequested.connect(self._handle_print_preview)
            dialog.exec()
        except Exception as e:
            print("Print error:", e)

    def _handle_print_preview(self, printer):
        painter = QPainter(printer)
        rect = painter.viewport()
        pixmap = QPixmap.fromImage(self.print_img_obj)
        size = pixmap.size()
        size.scale(rect.size(), Qt.AspectRatioMode.KeepAspectRatio)
        painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
        painter.setWindow(pixmap.rect())
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

    @pyqtSlot(result=str)
    def get_guide_html(self):
        try:
            if getattr(sys, 'frozen', False):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, "guide.html")
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"<p>안내 파일을 불러오는 중 오류가 발생했습니다: {e}</p>"

def main():
    # ★ per-monitor DPI 인식 설정 (캡처 오버레이 확대 현상 방지)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        pass

    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '0'
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '0'
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)

    main_window = QMainWindow()
    main_window.setWindowTitle("BH-Capture v1.0")
    main_window.setWindowIcon(create_camera_icon())
    main_window.resize(1800, 1100)
    
    view = QWebEngineView()
    view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
    view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
    
    channel = QWebChannel()
    engine = CaptureEngine()
    backend = Backend(engine, view)
    
    channel.registerObject("pyBackend", backend)
    view.page().setWebChannel(channel)
    
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    html_path = os.path.join(base_dir, "index.html")
    view.setUrl(QUrl.fromLocalFile(html_path))
    
    main_window.setCentralWidget(view)
    view.page().windowCloseRequested.connect(main_window.close)
    main_window.resize(1800, 1100)
    view.setZoomFactor(1.35)
    main_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
