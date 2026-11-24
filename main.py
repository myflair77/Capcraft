import sys
import os
import time
import base64
import ctypes
import json
from storage import atomic_write, write_json, HistoryWriter
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QUrl, Qt, QByteArray, QTimer
from PyQt6.QtGui import QImage, QPainter, QPixmap, QIcon
from print_window import PrintWindow
from app_version import APP_VERSION, APP_DISPLAY_VERSION
from update_service import UpdateService
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

DATA_DIR = os.environ.get("CAPCRAFT_DATA_DIR", os.path.expanduser("~"))
HISTORY_FILE = os.path.join(DATA_DIR, ".capcraft_history.json")
SETTINGS_FILE = os.path.join(DATA_DIR, ".capcraft_settings.json")


from capture_engine import CaptureEngine
from mini_launcher import MiniLauncherWindow
from single_instance import SingleInstanceBridge


def read_settings_dict(path=None):
    target = path or SETTINGS_FILE
    if not os.path.exists(target):
        return {}
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def compute_optimal_editor_zoom(viewport_w, viewport_h, toolbar_right, sidebar_w, current_zoom=1.0):
    """Compute a WebEngine zoom factor so the toolbar + sidebar fit cleanly across any DPI/monitor."""
    if not viewport_w or not viewport_h or not toolbar_right:
        return current_zoom
    required_w = float(toolbar_right) + float(sidebar_w or 170) + 28.0
    if required_w <= 0:
        return current_zoom
    width_zoom = float(current_zoom) * (float(viewport_w) / required_w)
    # Keep at least ~580 CSS px vertically so the canvas and recent list stay comfortable.
    max_height_zoom = float(current_zoom) * (float(viewport_h) / 580.0)
    target = min(width_zoom, max_height_zoom)
    return round(max(0.65, min(2.2, target)), 3)


def fit_editor_zoom_to_window(view, on_done=None, attempt=0, verify_pass=True):
    """Measure live toolbar/sidebar CSS width and adjust QWebEngineView zoom factor once visible."""
    if view is None:
        return
    js = """(() => {
        const tb = document.getElementById('toolbar');
        const sb = document.getElementById('sidebar');
        if (!tb) return null;
        const groups = tb.querySelectorAll('.tool-group');
        const last = groups.length ? groups[groups.length - 1] : null;
        const tbRight = last ? (last.offsetLeft + last.offsetWidth) : tb.scrollWidth;
        const sbW = sb ? sb.offsetWidth : 170;
        return { vw: window.innerWidth, vh: window.innerHeight, dpr: window.devicePixelRatio, tbRight, sbW };
    })()"""

    def _apply(metrics):
        if not isinstance(metrics, dict):
            if attempt < 20:
                QTimer.singleShot(100, lambda: fit_editor_zoom_to_window(view, on_done=on_done, attempt=attempt + 1, verify_pass=verify_pass))
            return
        vw = metrics.get("vw", 0)
        vh = metrics.get("vh", 0)
        tb_right = metrics.get("tbRight", 0)
        sb_w = metrics.get("sbW", 170)
        if vw < 300 or vh < 200 or tb_right < 100:
            if attempt < 20:
                QTimer.singleShot(100, lambda: fit_editor_zoom_to_window(view, on_done=on_done, attempt=attempt + 1, verify_pass=verify_pass))
            return
        cur = view.zoomFactor()
        target = compute_optimal_editor_zoom(vw, vh, tb_right, sb_w, current_zoom=cur)
        if abs(target - cur) >= 0.02:
            view.setZoomFactor(target)
        QTimer.singleShot(
            140,
            lambda: view.page().runJavaScript(
                "requestAnimationFrame(() => {"
                " if (typeof updateWorkspaceInset === 'function') updateWorkspaceInset();"
                " if (typeof applyFitWidth === 'function') applyFitWidth();"
                " else if (typeof applyFitZoom === 'function') applyFitZoom();"
                "});"
            ),
        )
        if verify_pass:
            # Re-check once after Chromium finishes any post-show DPI/surface update.
            QTimer.singleShot(
                450,
                lambda: fit_editor_zoom_to_window(view, on_done=on_done, attempt=0, verify_pass=False),
            )
        elif callable(on_done):
            on_done()

    view.page().runJavaScript(js, 0, _apply)


def position_window_on_active_screen(window, ratio=0.7):
    """Size and center the editor window on the monitor where the cursor currently is."""
    app = QApplication.instance()
    if app is None or window is None:
        return
    screen = None
    if sys.platform == "win32":
        try:
            import win32api
            px, py = win32api.GetCursorPos()
            for s in app.screens():
                if s.geometry().contains(px, py):
                    screen = s
                    break
        except Exception:
            pass
    if screen is None:
        screen = app.primaryScreen()
    if screen is not None:
        sg = screen.availableGeometry()
        width = max(960, int(sg.width() * ratio))
        height = max(640, int(sg.height() * ratio))
        width = min(width, sg.width())
        height = min(height, sg.height())
        window.resize(width, height)
        x = int((sg.width() - width) / 2) + sg.x()
        y = int((sg.height() - height) / 2) + sg.y()
        window.move(x, y)
    else:
        window.resize(1200, 800)


class EditorMainWindow(QMainWindow):
    """Main editor window that collapses back to the mini launcher on close."""

    def __init__(self, on_close_to_launcher=None):
        super().__init__()
        self._on_close_to_launcher = on_close_to_launcher
        self._force_close = False

    def closeEvent(self, event):
        if not self._force_close and self._on_close_to_launcher is not None:
            event.ignore()
            self.hide()
            self._on_close_to_launcher()
            return
        event.accept()


class AppController(QObject):
    """Coordinates transitions between mini launcher, capture overlay, and editor window."""

    def __init__(self, main_window, view, launcher, single_instance=None, settings_path=None):
        super().__init__()
        self.main_window = main_window
        self.view = view
        self.launcher = launcher
        self.single_instance = single_instance
        self.settings_path = settings_path or SETTINGS_FILE
        self.backend = None
        self.is_capturing = False
        self.frontend_ready = False
        self._editor_positioned = False
        self._zoom_optimized = False
        self._pending_capture = None
        self._pending_modal = None

        if self.launcher is not None:
            self.launcher.capture_requested.connect(self.start_capture_from_launcher)
            self.launcher.editor_requested.connect(self.show_editor)
            self.launcher.settings_requested.connect(lambda: self.show_editor(open_modal="settings"))
            self.launcher.guide_requested.connect(lambda: self.show_editor(open_modal="guide"))
            self.launcher.update_check_requested.connect(self._check_updates)
            self.launcher.quit_requested.connect(self.quit_app)

        if self.single_instance is not None:
            self.single_instance.activated.connect(self.on_second_instance_activated)

    def attach_backend(self, backend):
        self.backend = backend

    def _check_updates(self):
        if self.backend is not None:
            self.backend.check_updates()

    def show_launcher(self):
        if self.main_window is not None and self.main_window.isVisible():
            self.main_window.hide()
        if self.launcher is not None:
            self.launcher.show_positioned()

    def _schedule_zoom_optimization(self):
        if self._zoom_optimized or self.view is None:
            return
        if getattr(self, "_zoom_pending", False):
            return
        self._zoom_pending = True

        def _mark_done():
            self._zoom_optimized = True
            self._zoom_pending = False

        QTimer.singleShot(120, lambda: fit_editor_zoom_to_window(self.view, on_done=_mark_done))

    def show_editor(self, open_modal=None):
        if self.launcher is not None and self.launcher.isVisible():
            self.launcher.hide()
        if self.main_window is not None:
            if not self._editor_positioned:
                position_window_on_active_screen(self.main_window, ratio=0.7)
                self._editor_positioned = True
            self.main_window.showNormal()
            self.main_window.raise_()
            self.main_window.activateWindow()
        if self.frontend_ready and not self._zoom_optimized:
            self._schedule_zoom_optimization()
        if open_modal:
            if self.frontend_ready:
                self._open_frontend_modal(open_modal)
            else:
                self._pending_modal = open_modal

    def _open_frontend_modal(self, modal_name):
        if self.view is None:
            return
        if modal_name == "settings":
            self.view.page().runJavaScript("if(typeof openModal === 'function') openModal('modal_settings');")
        elif modal_name == "guide":
            self.view.page().runJavaScript("if(typeof openGuide === 'function') openGuide();")

    def on_frontend_ready(self):
        self.frontend_ready = True
        if self.main_window is not None and self.main_window.isVisible() and not self._zoom_optimized:
            self._schedule_zoom_optimization()
        if self._pending_capture is not None:
            image_base64, auto_copied = self._pending_capture
            self._pending_capture = None
            self.deliver_captured_image(image_base64, auto_copied)
        if self._pending_modal is not None:
            modal_name = self._pending_modal
            self._pending_modal = None
            self._open_frontend_modal(modal_name)

    def deliver_captured_image(self, image_base64, auto_copied=False):
        if not image_base64:
            return
        if not self.frontend_ready:
            self._pending_capture = (image_base64, auto_copied)
            return
        if self.view is None:
            return
        self.view.page().runJavaScript(f"window.receiveCapturedImage({json.dumps(image_base64)})")
        if auto_copied:
            self.view.page().runJavaScript(
                "if(typeof showToast === 'function') showToast('캡처 이미지가 클립보드에 복사되었습니다.');"
            )

    def start_capture_from_launcher(self, mode):
        if self.is_capturing or self.backend is None:
            return
        settings = read_settings_dict(self.settings_path)
        quality = settings.get("set_cap_quality") or "normal"
        resolved_mode = mode
        if mode == "size":
            try:
                w = max(50, int(settings.get("set_cap_w") or 800))
                h = max(50, int(settings.get("set_cap_h") or 600))
            except (TypeError, ValueError):
                w, h = 800, 600
            resolved_mode = f"size_{w}_{h}"
        self.backend.start_capture(resolved_mode, quality)

    def sync_launcher_mode(self, mode):
        if self.launcher is None or not mode:
            return
        base_mode = "size" if str(mode).startswith("size_") else str(mode)
        self.launcher.set_selected_mode(base_mode)

    def on_settings_saved(self, settings_dict):
        if self.launcher is not None and isinstance(settings_dict, dict):
            self.launcher.apply_theme(settings_dict.get("set_theme", "system"))

    def on_second_instance_activated(self, _message=""):
        if self.is_capturing:
            return
        self.show_launcher()

    def quit_app(self):
        if self.main_window is not None:
            self.main_window._force_close = True
            self.main_window.close()
        if self.launcher is not None:
            self.launcher._allow_close = True
            self.launcher.close()
        if self.single_instance is not None:
            self.single_instance.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()

class Backend(QObject):
    ocr_finished = pyqtSignal(str, str)
    ocr_retry = pyqtSignal(str, str)
    ocr_formatted = pyqtSignal(str, str)
    def __init__(self, engine, view, controller=None):
        super().__init__()
        self.engine = engine
        self.view = view
        self.controller = controller
        self._capturing = False
        self.history_writer = HistoryWriter(HISTORY_FILE)
        from ocr_bridge import OCRService
        self.ocr_service = OCRService(self)
        self.ocr_service.finished.connect(self.ocr_finished.emit)
        self.ocr_windows = {}
        self.updates = UpdateService(
            view.window(),
            DATA_DIR,
            on_quit_for_update=controller.quit_app if controller is not None else None,
        )

    @pyqtSlot()
    def check_updates(self):
        self.updates.check(manual=True)

    @pyqtSlot(bool)
    def set_update_checks(self, enabled):
        self.updates.set_enabled(enabled)

    @pyqtSlot(result=bool)
    def update_checks_enabled(self):
        return bool(self.updates.state.get('enabled', True))

    @pyqtSlot(str, str, result=bool)
    def open_ocr_result(self, key, payload):
        from ocr_window import OCRWindow
        result=json.loads(payload)
        window=self.ocr_windows.get(key)
        if window is None:
            window=OCRWindow(self.ocr_service,self.view.window())
            self.ocr_windows[key]=window
            window.retry.connect(lambda language:self.ocr_retry.emit(key,language))
            window.formatted.connect(lambda data:self.ocr_formatted.emit(key,data))
            window.destroyed.connect(lambda:self.ocr_windows.pop(key,None))
        window.update_result(result)
        window.show();window.raise_();window.activateWindow()
        return True

    @pyqtSlot(str)
    def close_ocr_result(self,key):
        window=self.ocr_windows.pop(key,None)
        if window is not None:window.close()

    @pyqtSlot(str, str)
    def recognize_text(self, token, data):
        self.ocr_service.submit(token, data)

    @pyqtSlot(str, str, str)
    def recognize_text_language(self, token, data, language):
        self.ocr_service.submit(token, data, language=language)

    @pyqtSlot(str, str)
    def format_ocr_text(self, token, data):
        self.ocr_service.submit(token, data, format_only=True)

    @pyqtSlot()
    def frontend_ready(self):
        if self.controller is not None:
            self.controller.on_frontend_ready()

    @pyqtSlot(str, result=bool)
    def copy_text(self, text):
        QApplication.clipboard().setText(text)
        return True

    def _copy_captured_image_to_clipboard(self, base64_data):
        qimg = getattr(self.engine, "last_captured_qimage", None)
        if qimg is not None and not qimg.isNull():
            QApplication.clipboard().setImage(qimg)
            return True
        if base64_data:
            return self.copy_to_clipboard(base64_data)
        return False

    @pyqtSlot(str, str)
    def start_capture(self, mode, quality_mode):
        if self._capturing:
            return
        self._capturing = True
        if self.controller is not None:
            self.controller.is_capturing = True
            self.controller.sync_launcher_mode(mode)

        try:
            # ★ 창을 완전히 숨긴 뒤 이벤트 큐 소진 후 스크린샷 촬영
            main_win = self.view.window() if self.view is not None else None
            launcher_win = self.controller.launcher if self.controller is not None else None
            had_visible_window = False
            if main_win is not None and main_win.isVisible():
                main_win.hide()
                had_visible_window = True
            if launcher_win is not None and launcher_win.isVisible():
                launcher_win.hide()
                had_visible_window = True

            if had_visible_window:
                QApplication.processEvents()   # 숨김 이벤트 즉시 처리
                time.sleep(0.35)               # 창 애니메이션·컴포지터 반영 대기
                QApplication.processEvents()   # 한 번 더 플러시

            try:
                image_base64 = self.engine.run_capture(mode, quality_mode)
            except Exception as e:
                print(f"Capture failed: {e}")
                image_base64 = None

            if image_base64:
                settings = read_settings_dict(
                    self.controller.settings_path if self.controller is not None else SETTINGS_FILE
                )
                auto_copy_enabled = settings.get("set_auto_copy", True)
                auto_copied = False
                if auto_copy_enabled:
                    auto_copied = self._copy_captured_image_to_clipboard(image_base64)

                if self.controller is not None:
                    self.controller.show_editor()
                    self.controller.deliver_captured_image(image_base64, auto_copied=auto_copied)
                elif main_win is not None:
                    main_win.show()
                    main_win.raise_()
                    main_win.activateWindow()
                    self.view.page().runJavaScript(f"window.receiveCapturedImage({json.dumps(image_base64)})")
                    if auto_copied:
                        self.view.page().runJavaScript(
                            "if(typeof showToast === 'function') showToast('캡처 이미지가 클립보드에 복사되었습니다.');"
                        )
            else:
                if self.controller is not None:
                    # 알캡처 동일 로직: 편집창/실행창 어디서 시작했든 ESC 취소 시 미니 실행창으로 전환
                    self.controller.show_launcher()
                elif main_win is not None:
                    main_win.show()
                    main_win.raise_()
                    main_win.activateWindow()
        finally:
            self._capturing = False
            if self.controller is not None:
                self.controller.is_capturing = False

    @pyqtSlot(str)
    def copy_to_clipboard(self, base64_data):
        try:
            # "data:image/png;base64," 접두어 제거
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            img_data = base64.b64decode(base64_data)
            image = QImage.fromData(img_data)
            if image.isNull():
                return False
            QApplication.clipboard().setImage(image)
            return True
        except Exception as e:
            print("Copy error:", e)
            return False

    @pyqtSlot(str)
    def print_image(self, base64_data):
        try:
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            img_data = base64.b64decode(base64_data)
            image = QImage.fromData(img_data)
            dialog = PrintWindow(image, self.view.window())
            dialog.exec()
        except Exception as e:
            print("Print error:", e)

    @pyqtSlot(result=str)
    def get_guide_html(self):
        try:
            if getattr(sys, 'frozen', False):
                from _guide_resource import get_html
                return get_html()
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
            
            save_path = os.path.normpath(save_path)
            if not save_path.lower().endswith(f".{ext}"):
                save_path += f".{ext}"

            dir_name = os.path.dirname(save_path)
            if dir_name and not os.path.exists(dir_name):
                try:
                    os.makedirs(dir_name, exist_ok=True)
                except Exception as e:
                    print(f"Directory creation error: {e}")

            self.view.page().runJavaScript(
                f"window.execute_save_to_path({json.dumps(save_path)}, {json.dumps(ext)})")

    @pyqtSlot(str, str)
    def write_file_data(self, path, base64_data):
        try:
            path = os.path.normpath(path)
            dir_name = os.path.dirname(path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)

            if "," in base64_data:
                base64_data = base64_data.split(",", 1)[1]
            data = base64.b64decode(base64_data)
            atomic_write(path, data)

            self.view.page().runJavaScript("if(typeof showToast === 'function') showToast('성공적으로 저장되었습니다.');")
            return True
        except Exception as e:
            print(f"Save error for path {path}: {e}")
            err_msg = str(e).replace('\\', '/').replace("'", "\\'").replace('"', '\\"').replace('\n', ' ')
            self.view.page().runJavaScript(f"if(typeof customAlert === 'function') customAlert('저장 중 오류가 발생했습니다: {err_msg}');")
            return False

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
                    self.view.page().runJavaScript(f"window.execute_open_file({json.dumps(filename)}, {json.dumps(b64)})")
            except Exception as e:
                print(f"Load error: {e}")
                self.view.page().runJavaScript(f"if(typeof customAlert === 'function') customAlert({json.dumps('불러오기 중 오류가 발생했습니다: ' + str(e))});")



    @pyqtSlot(str)
    def save_settings(self, json_str):
        path = SETTINGS_FILE
        try:
            write_json(path, json_str, dict)
            if self.controller is not None:
                try:
                    self.controller.on_settings_saved(json.loads(json_str))
                except Exception:
                    pass
        except Exception as e:
            print("Failed to save settings:", e)

    @pyqtSlot(result=str)
    def load_settings(self):
        path = SETTINGS_FILE
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
                            write_json(path, content, dict)
                    except Exception:
                        pass

                return content
            except Exception as e:
                print("Failed to load settings:", e)
        return ""

    @pyqtSlot(str, result=bool)
    def save_history(self, json_str):
        if '--isolate-history' in sys.argv:
            return False  # Diagnostic sessions must not overwrite real history.
        try:
            write_json(HISTORY_FILE, json_str, list)
            return True
        except Exception as e:
            print("Failed to save history:", e)
            return False

    @pyqtSlot(str, bool, bool, result=bool)
    def save_history_chunk(self, chunk, is_first, is_last):
        if '--isolate-history' in sys.argv:
            return False
        try:
            self.history_writer.append(chunk, is_first, is_last)
            return True
        except Exception as e:
            print("Failed to save history chunk:", e)
            return False

    @pyqtSlot(result=str)
    def load_history(self):
        # Recent captures are persistent; never delete them based on reboot time.
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

def configure_rendering():
    # No forced rendering workaround: partial raster disabling did not resolve
    # the observed blanking. Leave explicit diagnostic environment flags intact.
    pass


def configure_display_scaling():
    # Preserve the original startup sizing requested by the user. Matching Qt
    # and Chromium DPR did not eliminate the bottom-of-window blanking issue.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '0'
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '0'
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def main():
    # Give Windows a stable application identity for taskbar/shortcut grouping.
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('JBH.Capcraft')
    except (AttributeError, OSError):
        pass
    if sum(flag in sys.argv for flag in ('--isolate-history', '--isolate-selection-ui', '--isolate-guides')) > 1:
        raise SystemExit('Use only one isolation option at a time.')
    configure_rendering()
    configure_display_scaling()
    # Keep supported acceleration and the user's original UI sizing.
    app = QApplication(sys.argv)

    direct_editor = any(
        flag in sys.argv
        for flag in (
            '--editor',
            '--diagnose-display',
            '--isolate-history',
            '--isolate-selection-ui',
            '--isolate-guides',
        )
    )
    camera_icon = create_camera_icon()
    single_instance = None
    launcher = None

    if not direct_editor:
        app.setQuitOnLastWindowClosed(False)
        single_instance = SingleInstanceBridge(DATA_DIR)
        if single_instance.try_notify_existing("ACTIVATE_LAUNCHER"):
            sys.exit(0)
        single_instance.start_listening()
        initial_settings = read_settings_dict(SETTINGS_FILE)
        launcher = MiniLauncherWindow(
            icon=camera_icon,
            theme_mode=initial_settings.get("set_theme", "system"),
        )

    main_window = EditorMainWindow()
    main_window.setWindowTitle(f"Capcraft v{APP_DISPLAY_VERSION}")
    main_window.setWindowIcon(camera_icon)
    
    # 모니터 화면 크기의 70%로 창 크기 설정 및 중앙 배치
    screen = app.primaryScreen()
    if screen:
        screen_geometry = screen.availableGeometry()
        width = int(screen_geometry.width() * 0.7)
        height = int(screen_geometry.height() * 0.7)
        main_window.resize(width, height)
        
        # 창을 화면 정중앙에 배치
        x = int((screen_geometry.width() - width) / 2) + screen_geometry.x()
        y = int((screen_geometry.height() - height) / 2) + screen_geometry.y()
        main_window.move(x, y)
        
        # 해상도 비례 줌 로직 제거 (고해상도 데스크톱에서 버튼이 너무 커지는 현상 방지)
        zoom_factor = 1.0
    else:
        main_window.resize(1200, 800)
        zoom_factor = 1.0
    
    view = QWebEngineView()
    view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
    view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
    
    channel = QWebChannel()
    engine = CaptureEngine()
    controller = None
    if not direct_editor:
        controller = AppController(
            main_window,
            view,
            launcher,
            single_instance=single_instance,
            settings_path=SETTINGS_FILE,
        )
        main_window._on_close_to_launcher = controller.show_launcher
        app.aboutToQuit.connect(single_instance.close)

    backend = Backend(engine, view, controller=controller)
    if controller is not None:
        controller.attach_backend(backend)
    
    channel.registerObject("pyBackend", backend)
    view.page().setWebChannel(channel)
    
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    html_path = os.path.join(base_dir, "index.html")
    if '--diagnose-display' in sys.argv:
        from display_diagnostics import install_display_diagnostics
        main_window.display_diagnostics = install_display_diagnostics(view)
    page_url = QUrl.fromLocalFile(html_path)
    if '--isolate-history' in sys.argv:
        page_url.setQuery('isolate-history=1')
        main_window.setWindowTitle('Capcraft — 진단 3: 썸네일·이력 갱신 제외 (자동 저장 안 됨)')
    elif '--isolate-selection-ui' in sys.argv:
        page_url.setQuery('isolate-selection-ui=1')
        main_window.setWindowTitle('Capcraft — 진단 2: 선택 속성 UI 동기화 제외')
    elif '--isolate-guides' in sys.argv:
        page_url.setQuery('isolate-guides=1')
        main_window.setWindowTitle('Capcraft — 진단 1: 스마트 정렬 가이드 제외')
    view.setUrl(page_url)
    
    main_window.setCentralWidget(view)
    view.page().windowCloseRequested.connect(main_window.close)
    view.setZoomFactor(zoom_factor)
    if direct_editor:
        position_window_on_active_screen(main_window, ratio=0.7)
        main_window.show()
        view.loadFinished.connect(lambda _ok: QTimer.singleShot(80, lambda: fit_editor_zoom_to_window(view)))
    elif launcher is not None:
        launcher.show_positioned()
    QTimer.singleShot(5000, backend.updates.check)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
