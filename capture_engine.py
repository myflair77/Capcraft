import sys
import time
import base64
import cv2
import numpy as np
import mss
import win32gui
import win32api
import win32con
import uiautomation as auto
from PyQt6.QtWidgets import QWidget, QApplication, QPushButton, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QImage, QPixmap, QFont
import ctypes


class CaptureOverlay(QWidget):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode
        self.result_img = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        if self.mode in ('window', 'unit', 'scroll'):
            self.setWindowFlag(Qt.WindowType.WindowTransparentForInput, True)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # ── 스크린 데이터 수집 ──────────────────────────────────────────────
        app = QApplication.instance()
        screens = app.screens()

        # 전체 가상 데스크톱 (논리 픽셀)
        v_left   = min(s.geometry().left()   for s in screens)
        v_top    = min(s.geometry().top()    for s in screens)
        v_right  = max(s.geometry().right()  for s in screens)
        v_bottom = max(s.geometry().bottom() for s in screens)

        self.v_left   = v_left
        self.v_top    = v_top
        self.v_width  = v_right  - v_left
        self.v_height = v_bottom - v_top

        self.setGeometry(v_left, v_top, self.v_width, self.v_height)

        self.screen_data = []

        with mss.mss() as sct:
            for i, screen in enumerate(screens):
                lr  = screen.geometry()   # 논리 픽셀 QRect
                dpr = screen.devicePixelRatio()

                if i + 1 < len(sct.monitors):
                    p_mon   = sct.monitors[i + 1]
                    sct_img = sct.grab(p_mon)
                    img_arr = np.array(sct_img)  # BGRA
                    
                    h, w, c = img_arr.shape
                    img_arr_copy = img_arr.copy()
                    qimg = QImage(img_arr_copy.data, w, h, w * c, QImage.Format.Format_ARGB32)
                    display_pixmap = QPixmap.fromImage(qimg)
                    display_pixmap.setDevicePixelRatio(dpr)
                else:
                    p_mon   = None
                    img_arr = None
                    display_pixmap = QPixmap(int(lr.width() * dpr), int(lr.height() * dpr))
                    display_pixmap.fill(Qt.GlobalColor.black)
                    display_pixmap.setDevicePixelRatio(dpr)

                self.screen_data.append({
                    'logical_rect':  lr,
                    'dpr':           dpr,
                    'physical_rect': p_mon,
                    'pixmap':        display_pixmap,
                    'img_arr':       img_arr,
                })

        self.start_pos            = None
        self.current_pos          = None
        self.drag_start_pos       = None
        self.is_dragging          = False
        self.poly_points          = []
        self.target_rect_physical = None
        self.target_rect_logical  = None
        self.setMouseTracking(True)

        # 크기지정 모드
        if self.mode.startswith('size_'):
            parts = self.mode.split('_')
            self.size_w = int(parts[1]) if len(parts) > 1 else 800
            self.size_h = int(parts[2]) if len(parts) > 2 else 600
            self.mode   = 'size'
        else:
            self.size_w, self.size_h = 800, 600

        # window / unit / scroll 폴링
        if self.mode in ('window', 'unit', 'scroll'):
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.poll_mouse)
            self.timer.start(20)
            self.lbutton_down = False

    # ─── 좌표 변환 ──────────────────────────────────────────────────────────
    def logical_to_physical(self, lx, ly):
        """위젯 로컬 논리 좌표 → 물리 픽셀 좌표"""
        glx = lx + self.v_left
        gly = ly + self.v_top
        for sd in self.screen_data:
            lr = sd['logical_rect']
            if lr.contains(int(glx), int(gly)):
                rel_lx = glx - lr.x()
                rel_ly = gly - lr.y()
                px = sd['physical_rect']['left'] + int(rel_lx * sd['dpr'])
                py = sd['physical_rect']['top']  + int(rel_ly * sd['dpr'])
                return px, py
        return int(glx), int(gly)

    def physical_to_logical(self, px, py):
        """물리 픽셀 좌표 → 위젯 로컬 논리 좌표"""
        for sd in self.screen_data:
            if sd['physical_rect'] is None:
                continue
            p = sd['physical_rect']
            if p['left'] <= px < p['left'] + p['width'] and \
               p['top']  <= py < p['top']  + p['height']:
                rel_px = px - p['left']
                rel_py = py - p['top']
                glx = sd['logical_rect'].x() + rel_px / sd['dpr']
                gly = sd['logical_rect'].y() + rel_py / sd['dpr']
                return glx - self.v_left, gly - self.v_top
        return px - self.v_left, py - self.v_top

    # ─── 폴링 ───────────────────────────────────────────────────────────────
    def poll_mouse(self):
        try:
            px, py = win32api.GetCursorPos()
        except:
            return

        lx, ly = self.physical_to_logical(px, py)
        self.current_pos = QPoint(int(lx), int(ly))

        lbutton = win32api.GetAsyncKeyState(win32con.VK_LBUTTON)
        if lbutton < 0:
            if not self.lbutton_down:
                self.lbutton_down = True
                if self.mode == 'scroll':
                    self.timer.stop()
                    self.result_img = QPoint(px, py)
                    self.close()
                elif self.target_rect_physical:
                    self.timer.stop()
                    self.perform_capture(self.target_rect_physical)
        else:
            self.lbutton_down = False

        if not self.lbutton_down:
            if self.mode in ('window', 'scroll'):
                hwnd = win32gui.WindowFromPoint((px, py))
                if hwnd:
                    try:
                        l, t, r, b = win32gui.GetWindowRect(hwnd)
                        self.target_rect_physical = (l, t, r - l, b - t)
                        llx, lly = self.physical_to_logical(l, t)
                        lrx, lry = self.physical_to_logical(r, b)
                        self.target_rect_logical = QRect(
                            int(llx), int(lly),
                            int(lrx - llx), int(lry - lly)
                        )
                    except:
                        pass
            elif self.mode == 'unit':
                try:
                    control = auto.ControlFromPoint(px, py)
                    if control:
                        rect = control.BoundingRectangle
                        self.target_rect_physical = (rect.left, rect.top, rect.width(), rect.height())
                        llx, lly = self.physical_to_logical(rect.left, rect.top)
                        lrx, lry = self.physical_to_logical(rect.right, rect.bottom)
                        self.target_rect_logical = QRect(
                            int(llx), int(lly),
                            int(lrx - llx), int(lry - lly)
                        )
                except:
                    pass
            self.update()

    # ─── 그리기 ─────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)

        # 1. 각 스크린 스냅샷 (논리 좌표에 맞게 배치)
        for sd in self.screen_data:
            lr    = sd['logical_rect']
            off_x = lr.x() - self.v_left
            off_y = lr.y() - self.v_top
            # display_pixmap의 DPR은 Qt가 자동으로 처리 → 논리 크기로 렌더
            painter.drawPixmap(off_x, off_y, sd['pixmap'])

        # 2. 반투명 어두운 오버레이
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        # 3. 모드별 선택 표시
        if self.mode == 'manual':
            if self.is_dragging and self.start_pos and self.current_pos:
                rect = QRect(self.start_pos, self.current_pos).normalized()
                self._draw_bright(painter, rect)
                painter.setPen(QPen(QColor(59, 130, 246), 2))
                painter.drawRect(rect)
                self._draw_label(painter, rect, f"{rect.width()} × {rect.height()} px")
            elif self.poly_points:
                from PyQt6.QtGui import QPainterPath
                path = QPainterPath()
                path.moveTo(float(self.poly_points[0].x()), float(self.poly_points[0].y()))
                for p in self.poly_points[1:]:
                    path.lineTo(float(p.x()), float(p.y()))
                if self.current_pos:
                    path.lineTo(float(self.current_pos.x()), float(self.current_pos.y()))
                
                painter.save()
                painter.setClipPath(path)
                self._draw_bright(painter, path.boundingRect().toRect())
                painter.restore()
                
                painter.setPen(QPen(QColor(59, 130, 246), 2))
                painter.drawPath(path)
                
                if self.current_pos and len(self.poly_points) >= 1:
                    if (self.current_pos - self.poly_points[0]).manhattanLength() < 20:
                        painter.setBrush(QColor(255, 80, 80))
                        painter.drawEllipse(self.poly_points[0], 6, 6)

        elif self.mode in ('window', 'unit', 'scroll') and self.target_rect_logical:
            rect = self.target_rect_logical
            self._draw_bright(painter, rect)
            painter.setPen(QPen(QColor(255, 80, 80), 3))
            painter.drawRect(rect)

        elif self.mode == 'size' and self.current_pos:
            w, h = self.size_w, self.size_h
            cx   = self.current_pos.x()
            cy   = self.current_pos.y()
            rect = QRect(cx - w // 2, cy - h // 2, w, h)
            self._draw_bright(painter, rect)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawRect(rect)
            self._draw_label(painter, rect, f"{w} × {h} px  (휠로 조절)")

        elif self.mode == 'full':
            for i, sd in enumerate(self.screen_data, 1):
                lr   = sd['logical_rect']
                rect = QRect(lr.x() - self.v_left, lr.y() - self.v_top, lr.width(), lr.height())
                hover = self.current_pos and rect.contains(self.current_pos)
                if hover:
                    painter.fillRect(rect, QColor(255, 255, 255, 40))
                    painter.setPen(QPen(QColor(59, 130, 246), 4))
                else:
                    painter.setPen(QPen(QColor(200, 200, 200), 2))
                painter.drawRect(rect)
                f = QFont(); f.setPointSize(24); f.setBold(True); painter.setFont(f)
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"화면 {i}")

            if len(self.screen_data) > 1:
                for sd in self.screen_data[1:]:
                    bx = sd['logical_rect'].x() - self.v_left
                    cy = sd['logical_rect'].y() - self.v_top + sd['logical_rect'].height() // 2
                    for btn in (QRect(bx-130, cy-25, 120, 50), QRect(bx+10, cy-25, 120, 50)):
                        hover = self.current_pos and btn.contains(self.current_pos)
                        painter.fillRect(btn, QColor(59,130,246,220) if hover else QColor(0,0,0,180))
                        painter.setPen(QPen(QColor(255,255,255), 2))
                        painter.drawRect(btn)
                        f2 = QFont(); f2.setPointSize(14); f2.setBold(True); painter.setFont(f2)
                        painter.drawText(btn, Qt.AlignmentFlag.AlignCenter, "모두")

        painter.end()

    def _draw_bright(self, painter, rect):
        """선택 영역을 원본 스냅샷으로 밝게 표시"""
        for sd in self.screen_data:
            lr = sd['logical_rect']
            screen_local = QRect(lr.x()-self.v_left, lr.y()-self.v_top, lr.width(), lr.height())
            inter = rect.intersected(screen_local)
            if not inter.isEmpty():
                painter.save()
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
                painter.setClipRect(inter)
                painter.drawPixmap(screen_local.topLeft(), sd['pixmap'])
                painter.restore()

    def _draw_label(self, painter, rect, text):
        f = QFont(); f.setPointSize(11); f.setBold(True); painter.setFont(f)
        lr = QRect(rect.x(), rect.bottom()+6, max(rect.width(), 200), 26)
        painter.fillRect(lr, QColor(0, 0, 0, 160))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(lr, Qt.AlignmentFlag.AlignCenter, text)

    # ─── 마우스 이벤트 ──────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.drag_start_pos = event.pos()
        cp = self.current_pos or event.pos()

        if self.mode == 'size':
            w, h = self.size_w, self.size_h
            rect = QRect(cp.x()-w//2, cp.y()-h//2, w, h)
            px1, py1 = self.logical_to_physical(rect.left(), rect.top())
            px2, py2 = self.logical_to_physical(rect.right(), rect.bottom())
            self.perform_capture((px1, py1, px2-px1, py2-py1))

        elif self.mode == 'full':
            if len(self.screen_data) > 1:
                for sd in self.screen_data[1:]:
                    bx = sd['logical_rect'].x() - self.v_left
                    cy = sd['logical_rect'].y()-self.v_top + sd['logical_rect'].height()//2
                    for btn in (QRect(bx-130,cy-25,120,50), QRect(bx+10,cy-25,120,50)):
                        if btn.contains(cp):
                            mn_x = min(s['physical_rect']['left'] for s in self.screen_data if s['physical_rect'])
                            mn_y = min(s['physical_rect']['top']  for s in self.screen_data if s['physical_rect'])
                            mx_x = max(s['physical_rect']['left']+s['physical_rect']['width']  for s in self.screen_data if s['physical_rect'])
                            mx_y = max(s['physical_rect']['top'] +s['physical_rect']['height'] for s in self.screen_data if s['physical_rect'])
                            self.perform_capture((mn_x, mn_y, mx_x-mn_x, mx_y-mn_y))
                            return
            for sd in self.screen_data:
                lr   = sd['logical_rect']
                rect = QRect(lr.x()-self.v_left, lr.y()-self.v_top, lr.width(), lr.height())
                if rect.contains(cp) and sd['physical_rect']:
                    p = sd['physical_rect']
                    self.perform_capture((p['left'], p['top'], p['width'], p['height']))
                    return

    def mouseMoveEvent(self, event):
        self.current_pos = event.pos()
        if self.mode == 'manual' and self.drag_start_pos and not self.is_dragging:
            if (event.pos() - self.drag_start_pos).manhattanLength() > 5:
                self.is_dragging = True
                self.start_pos = self.drag_start_pos
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    def wheelEvent(self, event):
        if self.mode == 'size':
            delta = event.angleDelta().y()
            step  = 20
            self.size_w = max(50, min(3840, self.size_w + (step if delta > 0 else -step)))
            self.size_h = max(50, min(2160, self.size_h + (step if delta > 0 else -step)))
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.mode == 'manual':
            if self.is_dragging and self.start_pos:
                rect = QRect(self.start_pos, event.pos()).normalized()
                if rect.width() > 5 and rect.height() > 5:
                    px1, py1 = self.logical_to_physical(rect.left(),  rect.top())
                    px2, py2 = self.logical_to_physical(rect.right(), rect.bottom())
                    self.perform_capture((px1, py1, px2-px1, py2-py1))
                else:
                    self.close()
            else:
                self.drag_start_pos = None
                self.is_dragging = False
                self.start_pos = None
                
                pos = event.pos()
                if not self.poly_points:
                    self.poly_points.append(pos)
                else:
                    if (pos - self.poly_points[0]).manhattanLength() < 20:
                        self.perform_poly_capture(self.poly_points)
                    else:
                        self.poly_points.append(pos)
                self.update()

    # ─── 캡처 실행 ──────────────────────────────────────────────────────────
    def perform_poly_capture(self, logical_points):
        phys_points = [self.logical_to_physical(p.x(), p.y()) for p in logical_points]
        pxs = [p[0] for p in phys_points]
        pys = [p[1] for p in phys_points]
        min_x, max_x = min(pxs), max(pxs)
        min_y, max_y = min(pys), max(pys)
        w, h = max_x - min_x, max_y - min_y
        
        if w <= 0 or h <= 0:
            self.close()
            return
            
        cropped = self.get_physical_crop(min_x, min_y, w, h)
        
        mask = np.zeros((h, w), dtype=np.uint8)
        poly_arr = np.array([[(x - min_x, y - min_y) for x, y in phys_points]], dtype=np.int32)
        cv2.fillPoly(mask, poly_arr, 255)
        
        cropped[:, :, 3] = np.where(mask == 255, cropped[:, :, 3], 0)
        
        _, buffer = cv2.imencode('.png', cropped)
        self.result_img = base64.b64encode(buffer).decode('utf-8')
        self.close()

    def get_physical_crop(self, x, y, w, h):
        result = np.zeros((h, w, 4), dtype=np.uint8)
        for sd in self.screen_data:
            if sd['img_arr'] is None or sd['physical_rect'] is None:
                continue
            p  = sd['physical_rect']
            ix = max(x, p['left']);         iy = max(y, p['top'])
            ir = min(x+w, p['left']+p['width'])
            ib = min(y+h, p['top'] +p['height'])
            if ix < ir and iy < ib:
                sx = ix-p['left']; sy = iy-p['top']
                dx = ix-x;         dy = iy-y
                cw = ir-ix;        ch = ib-iy
                result[dy:dy+ch, dx:dx+cw] = sd['img_arr'][sy:sy+ch, sx:sx+cw]
        return result

    def perform_capture(self, rect):
        x, y, w, h = int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3])
        if w <= 0 or h <= 0:
            self.close()
            return
        cropped = self.get_physical_crop(x, y, w, h)
        _, buffer = cv2.imencode('.png', cropped)
        self.result_img = base64.b64encode(buffer).decode('utf-8')
        self.close()


class ScrollCaptureOverlay(QWidget):
    def __init__(self, rect):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(rect[0], rect[1], rect[2], rect[3])
        
        try:
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), 0x00000011)
        except:
            pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 255, 255, 30))
        painter.setPen(QPen(QColor(59, 130, 246), 4))
        painter.drawRect(self.rect())
        painter.end()


class ScrollButtonOverlay(QWidget):
    def __init__(self, rect, stop_callback):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        btn_w, btn_h = 280, 100
        x = rect[0] + (rect[2] - btn_w) // 2
        y = rect[1] + rect[3] - btn_h - 40
        self.setGeometry(x, y, btn_w, btn_h)
        
        try:
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), 0x00000011)
        except:
            pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn = QPushButton("여기까지만 캡처")
        self.btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6; color: white; border: 2px solid white; 
                border-radius: 20px; font-weight: bold; font-size: 16px; padding: 12px 24px;
            }
            QPushButton:hover { background-color: #2563eb; }
        """)
        self.btn.clicked.connect(stop_callback)
        layout.addWidget(self.btn)
        
        lbl = QLabel("ESC 키를 누르거나 이 버튼을 누르세요.")
        lbl.setStyleSheet("color: white; font-size: 13px; font-weight: bold; background-color: rgba(0,0,0,0.5); padding: 5px 10px; border-radius: 10px; margin-top: 5px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)


# ─────────────────────────────────────────────────────────────────────────────
class CaptureEngine:
    def __init__(self):
        pass

    def run_capture(self, mode):
        overlay = CaptureOverlay(mode)
        overlay.show()
        overlay.raise_()
        overlay.activateWindow()

        while overlay.isVisible():
            QApplication.processEvents()
            time.sleep(0.01)

        if mode == 'scroll' and isinstance(overlay.result_img, QPoint):
            time.sleep(0.3) # 오버레이가 완전히 닫힐 때까지 대기
            return self.run_scroll_capture(overlay.result_img)

        return overlay.result_img

    def run_scroll_capture(self, pos):
        hwnd = win32gui.WindowFromPoint((pos.x(), pos.y()))
        if not hwnd:
            return None
        try:
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            monitor = {"top": t, "left": l, "width": r-l, "height": b-t}
        except:
            return None

        win32api.SetCursorPos((pos.x(), pos.y()))
        for _ in range(30):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, 1200, 0)
        time.sleep(0.8)

        stop_flag = [False]
        def do_stop():
            stop_flag[0] = True

        scroll_overlay = ScrollCaptureOverlay((monitor['left'], monitor['top'], monitor['width'], monitor['height']))
        scroll_btn_overlay = ScrollButtonOverlay((monitor['left'], monitor['top'], monitor['width'], monitor['height']), do_stop)
        scroll_overlay.show()
        scroll_btn_overlay.show()
        QApplication.processEvents()

        br = scroll_btn_overlay.geometry()
        btn_rx = max(0, br.x() - monitor['left'])
        btn_ry = max(0, br.y() - monitor['top'])
        btn_rw = br.width()
        btn_rh = br.height()

        def mask_button(img, ref):
            result = img.copy()
            y1 = btn_ry; y2 = min(btn_ry + btn_rh, img.shape[0])
            x1 = btn_rx; x2 = min(btn_rx + btn_rw, img.shape[1])
            if y2 > y1 and x2 > x1 and ref is not None:
                result[y1:y2, x1:x2] = ref[y1:y2, x1:x2]
            return result

        def robust_offset(prev, cur, img_h):
            w = prev.shape[1]
            lc = int(w * 0.05)
            rc = int(w * 0.80)
            strip_offsets = []
            for frac in (0.25, 0.45, 0.60):
                sy   = int(img_h * frac)
                sh   = int(img_h * 0.15)
                if sy + sh > img_h: continue
                t_strip = prev[sy:sy+sh, lc:lc+rc]
                gt = cv2.cvtColor(t_strip, cv2.COLOR_BGRA2GRAY)
                gn = cv2.cvtColor(cur[:, lc:lc+rc], cv2.COLOR_BGRA2GRAY)
                if gn.shape[0] < gt.shape[0]: continue
                res = cv2.matchTemplate(gn, gt, cv2.TM_CCOEFF_NORMED)
                _, mv, _, ml = cv2.minMaxLoc(res)
                if mv > 0.80:
                    off = sy - ml[1]
                    if 5 <= off <= int(img_h * 0.80): strip_offsets.append(off)
            if not strip_offsets: return None
            strip_offsets.sort()
            return strip_offsets[len(strip_offsets) // 2]

        images = []
        with mss.mss() as sct:
            def grab():
                try: return np.array(sct.grab(monitor))
                except: return np.array(sct.grab(sct.monitors[0]))

            def wait_stable(timeout=1.5):
                t0 = time.time()
                prev = grab()
                while time.time() - t0 < timeout:
                    if stop_flag[0]: break
                    QApplication.processEvents()
                    time.sleep(0.15)
                    cur = grab()
                    if np.abs(cur.astype(np.int16) - prev.astype(np.int16)).mean() < 1.5:
                        return cur
                    prev = cur
                return prev

            raw = wait_stable(0.8)
            first_img = raw.copy()
            cur_clean = mask_button(raw, first_img)
            images.append(cur_clean)
            last_clean = cur_clean
            img_h = raw.shape[0]
            max_scrolls, no_change_cnt = 40, 0

            for _ in range(max_scrolls):
                if stop_flag[0] or win32api.GetAsyncKeyState(win32con.VK_ESCAPE): break
                QApplication.processEvents()
                px, py = win32api.GetCursorPos()
                is_over_btn = scroll_btn_overlay.geometry().contains(px, py)
                if is_over_btn: win32api.SetCursorPos((monitor['left'] + 20, monitor['top'] + 20))
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -300, 0)
                if is_over_btn: win32api.SetCursorPos((px, py))
                raw_new = wait_stable(1.0)
                if stop_flag[0] or win32api.GetAsyncKeyState(win32con.VK_ESCAPE): break
                new_clean = mask_button(raw_new, last_clean)
                if np.array_equal(last_clean, new_clean):
                    no_change_cnt += 1
                    if no_change_cnt >= 2: break
                    continue
                no_change_cnt = 0

                # ── 로버스트 offset 계산 ──────────────────────────────
                offset = robust_offset(last_clean, new_clean, img_h)
                if offset is not None and offset > 0:
                    images.append(new_clean[-offset:, :])
                # offset 계산 실패 시 해당 프레임 건너뜀 (중복/반복 방지)

                last_clean = new_clean

        scroll_overlay.close()
        scroll_btn_overlay.close()

        if not images:
            return None
        final_img = np.vstack(images)
        _, buffer = cv2.imencode('.png', final_img)
        return base64.b64encode(buffer).decode('utf-8')
