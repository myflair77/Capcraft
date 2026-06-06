import sys
import os
import time
import base64
import ctypes
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QObject, pyqtSlot, QUrl, Qt, QByteArray, QTimer
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

HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".capcraft_history.json")

def cleanup_history_if_rebooted():
    try:
        if not os.path.exists(HISTORY_FILE):
            return
        mtime = os.path.getmtime(HISTORY_FILE)
        uptime_sec = ctypes.windll.kernel32.GetTickCount64() / 1000.0
        boot_time = time.time() - uptime_sec
        # 파일이 시스템 부팅 시간 이전에 수정되었다면 재부팅된 것으로 간주하고 삭제
        if mtime < boot_time:
            os.remove(HISTORY_FILE)
    except Exception:
        pass

from capture_engine import CaptureEngine

class Backend(QObject):
    def __init__(self, engine, view):
        super().__init__()
        self.engine = engine
        self.view = view

    @pyqtSlot(str, str)
    def start_capture(self, mode, quality_mode):
        # ★ 창을 완전히 숨긴 뒤 이벤트 큐 소진 후 스크린샷 촬영
        self.view.window().hide()
        QApplication.processEvents()   # 숨김 이벤트 즉시 처리
        time.sleep(0.45)               # 창 애니메이션·컴포지터 반영 대기
        QApplication.processEvents()   # 한 번 더 플러시

        try:
            image_base64 = self.engine.run_capture(mode, quality_mode)
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
            printer.setOutputFileName(f"Capcraft_{date_str}.pdf")
            
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

    @pyqtSlot(str, str)
    def request_save(self, default_format, suggested_name):
        QTimer.singleShot(0, lambda: self._do_request_save(default_format, suggested_name))

    def _do_request_save(self, default_format, suggested_name):
        filter_str = "PNG Files (*.png);;JPG Files (*.jpg);;SVG Files (*.svg);;PDF Files (*.pdf);;JSON Files (*.json)"
        if default_format in ["jpg", "jpeg"]:
            initial_filter = "JPG Files (*.jpg)"
        elif default_format == "svg":
            initial_filter = "SVG Files (*.svg)"
        elif default_format == "pdf":
            initial_filter = "PDF Files (*.pdf)"
        elif default_format == "json":
            initial_filter = "JSON Files (*.json)"
        else:
            initial_filter = "PNG Files (*.png)"
            
        save_path, selected_filter = QFileDialog.getSaveFileName(
            self.view.window(), 
            "저장", 
            suggested_name, 
            filter_str, 
            initial_filter
        )
        
        if save_path:
            ext = "png"
            if "jpg" in selected_filter.lower(): ext = "jpg"
            elif "svg" in selected_filter.lower(): ext = "svg"
            elif "pdf" in selected_filter.lower(): ext = "pdf"
            elif "json" in selected_filter.lower(): ext = "json"
            
            path_b64 = base64.b64encode(save_path.encode('utf-8')).decode()
            self.view.page().runJavaScript(f"window.execute_save_to_path(atob('{path_b64}'), '{ext}')")

    @pyqtSlot(str, str)
    def write_file_data(self, path, base64_data):
        try:
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            data = base64.b64decode(base64_data)
            with open(path, "wb") as f:
                f.write(data)
            self.view.page().runJavaScript("if(typeof showToast === 'function') showToast('저장되었습니다.');")
        except Exception as e:
            print(f"Save error: {e}")
            self.view.page().runJavaScript(f"if(typeof customAlert === 'function') customAlert('저장 중 오류가 발생했습니다: {e}');")

    @pyqtSlot()
    def request_open_file(self):
        QTimer.singleShot(0, self._do_request_open_file)

    def _do_request_open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.view.window(), 
            "파일 열기", 
            "", 
            "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, "rb") as f:
                    data = f.read()
                    b64 = base64.b64encode(data).decode('utf-8')
                    filename = os.path.basename(file_path)
                    self.view.page().runJavaScript(f"window.execute_open_file('{filename}', '{b64}')")
            except Exception as e:
                print(f"Load error: {e}")
                self.view.page().runJavaScript(f"if(typeof customAlert === 'function') customAlert('불러오기 중 오류가 발생했습니다: {e}');")



    @pyqtSlot(str)
    def save_settings(self, json_str):
        path = os.path.join(os.path.expanduser("~"), ".capcraft_settings.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json_str)
        except Exception as e:
            print("Failed to save settings:", e)

    @pyqtSlot(result=str)
    def load_settings(self):
        path = os.path.join(os.path.expanduser("~"), ".capcraft_settings.json")
        if os.path.exists(path):
            try:
                mtime = os.path.getmtime(path)
                uptime_sec = ctypes.windll.kernel32.GetTickCount64() / 1000.0
                boot_time = time.time() - uptime_sec
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 시스템 부팅 이전에 저장된 설정이라면, 최근 이모티콘 기록을 삭제
                if mtime < boot_time:
                    try:
                        import json
                        data = json.loads(content)
                        if "recentEmojis" in data:
                            del data["recentEmojis"]
                            content = json.dumps(data)
                            with open(path, "w", encoding="utf-8") as f:
                                f.write(content)
                    except Exception:
                        pass

                return content
            except Exception as e:
                print("Failed to load settings:", e)
        return ""

    @pyqtSlot(str)
    def save_history(self, json_str):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                f.write(json_str)
        except Exception as e:
            print("Failed to save history:", e)

    @pyqtSlot(result=str)
    def load_history(self):
        cleanup_history_if_rebooted()
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print("Failed to load history:", e)
        return ""

    @pyqtSlot(result=str)
    def select_directory(self):
        folder = QFileDialog.getExistingDirectory(None, "사용자 정의 이모티콘 폴더 선택")
        return folder if folder else ""

    @pyqtSlot(str, result=str)
    def get_images_in_directory(self, dir_path):
        import json
        images = []
        if os.path.isdir(dir_path):
            valid_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
            try:
                for f in os.listdir(dir_path):
                    ext = os.path.splitext(f)[1].lower()
                    if ext in valid_exts:
                        full_path = os.path.join(dir_path, f)
                        url = "file:///" + full_path.replace("\\", "/")
                        name = os.path.splitext(f)[0]
                        category = os.path.basename(dir_path)
                        images.append({
                            "name": name,
                            "shortcodes": [name],
                            "url": url,
                            "category": category
                        })
            except Exception as e:
                print(f"Error reading directory {dir_path}: {e}")
        return json.dumps(images)

def main():
    # ★ per-monitor DPI 인식 설정 (캡처 오버레이 확대 현상 방지)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        pass

    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '0'
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '0'
    # ★ QWebEngine GPU 래스터화만 선택적 비활성화 — 캔버스 깜빡임 방지 + GPU 컴포지팅 성능 유지
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--disable-gpu-rasterization --disable-partial-raster'
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)

    main_window = QMainWindow()
    main_window.setWindowTitle("Capcraft v1.2")
    main_window.setWindowIcon(create_camera_icon())
    
    # 모니터 화면 크기의 70%로 창 크기 설정
    screen = app.primaryScreen()
    if screen:
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.7)
        height = int(screen_geometry.height() * 0.7)
        main_window.resize(width, height)
        # 화면 크기에 비례해 UI(상단바, 사이드바 등) 줌 비율 조절
        zoom_factor = max(0.8, (width / 1800.0) * 1.35)
    else:
        main_window.resize(1800, 1100)
        zoom_factor = 1.35
    
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
    view.setZoomFactor(zoom_factor)
    main_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
