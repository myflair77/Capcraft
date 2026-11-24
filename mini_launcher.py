import sys
from PyQt6.QtCore import QByteArray, QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QSizePolicy,
    QToolButton,
    QWidget,
)

try:
    from PyQt6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False


CAPTURE_MODES = (
    ("manual", "직접지정"),
    ("window", "창"),
    ("unit", "단위영역"),
    ("full", "전체화면"),
    ("scroll", "스크롤"),
    ("size", "크기지정"),
)

_ICON_SVGS = {
    "new": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M6 2v14a2 2 0 0 0 2 2h14"/>'
        '<path d="M18 22V8a2 2 0 0 0-2-2H2"/>'
        '<line x1="12" y1="9" x2="12" y2="15"/>'
        '<line x1="9" y1="12" x2="15" y2="12"/>'
        '</svg>'
    ),
    "manual": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 17V5a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v7"/>'
        '<path d="M4 17a1 1 0 0 0 1 1h7"/>'
        '<line x1="18" y1="14" x2="18" y2="21"/>'
        '<line x1="14.5" y1="17.5" x2="21.5" y2="17.5"/>'
        '</svg>'
    ),
    "window": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="4" width="18" height="16" rx="2"/>'
        '<line x1="3" y1="9" x2="21" y2="9"/>'
        '<circle cx="6.5" cy="6.5" r="0.8" fill="{color}"/>'
        '<circle cx="9.5" cy="6.5" r="0.8" fill="{color}"/>'
        '</svg>'
    ),
    "unit": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="4" width="7" height="16" rx="1"/>'
        '<rect x="14" y="4" width="7" height="7" rx="1"/>'
        '<rect x="14" y="14" width="7" height="6" rx="1"/>'
        '</svg>'
    ),
    "full": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="4" width="18" height="16" rx="2"/>'
        '<path d="M8 9H7v1"/>'
        '<path d="M16 9h1v1"/>'
        '<path d="M8 15H7v-1"/>'
        '<path d="M16 15h1v-1"/>'
        '</svg>'
    ),
    "scroll": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="4" y="3" width="16" height="18" rx="2"/>'
        '<path d="M12 7l-2.5 3h5z" fill="{color}"/>'
        '<path d="M12 17l-2.5-3h5z" fill="{color}"/>'
        '</svg>'
    ),
    "size": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M4 8V5a1 1 0 0 1 1-1h3"/>'
        '<path d="M16 4h3a1 1 0 0 1 1 1v3"/>'
        '<path d="M20 16v3a1 1 0 0 1-1 1h-3"/>'
        '<path d="M8 20H5a1 1 0 0 1-1-1v-3"/>'
        '<line x1="10" y1="4" x2="14" y2="4"/>'
        '<line x1="10" y1="20" x2="14" y2="20"/>'
        '<line x1="4" y1="10" x2="4" y2="14"/>'
        '<line x1="20" y1="10" x2="20" y2="14"/>'
        '</svg>'
    ),
    "list": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="4" y="3" width="16" height="18" rx="2"/>'
        '<line x1="8" y1="3" x2="8" y2="21"/>'
        '<line x1="16" y1="3" x2="16" y2="21"/>'
        '<line x1="4" y1="9" x2="20" y2="9"/>'
        '<line x1="4" y1="15" x2="20" y2="15"/>'
        '</svg>'
    ),
    "menu": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="4" y1="6" x2="20" y2="6"/>'
        '<line x1="4" y1="12" x2="20" y2="12"/>'
        '<line x1="4" y1="18" x2="20" y2="18"/>'
        '</svg>'
    ),
}


def _is_system_dark_mode() -> bool:
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return value == 0
        except OSError:
            pass
    try:
        hints = QApplication.styleHints()
        if hasattr(hints, "colorScheme") and hints.colorScheme() == Qt.ColorScheme.Dark:
            return True
    except Exception:
        pass
    return False


def _render_svg_icon(svg_key: str, color: str, size: int = 24) -> QIcon:
    svg_template = _ICON_SVGS.get(svg_key)
    if not svg_template or not _HAS_SVG:
        return QIcon()
    svg_bytes = QByteArray(svg_template.format(color=color).encode("utf-8"))
    renderer = QSvgRenderer(svg_bytes)
    px_size = size * 2
    pixmap = QPixmap(px_size, px_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2.0)
    return QIcon(pixmap)


class MiniLauncherWindow(QMainWindow):
    """Compact ALCapture-style launcher bar for quick one-click capture."""

    capture_requested = pyqtSignal(str)
    editor_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    guide_requested = pyqtSignal()
    update_check_requested = pyqtSignal()
    cancel_capture_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, icon: QIcon | None = None, theme_mode: str = "system", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Capcraft 실행창")
        if icon is not None:
            self.setWindowIcon(icon)

        # Use standard QMainWindow chrome (guaranteed taskbar/Alt+Tab visibility on Windows)
        # with maximize disabled and always-on-top enabled like ALCapture.
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self._selected_mode = "manual"
        self._theme_mode = theme_mode or "system"
        self._is_dark = False
        self._positioned = False
        self._allow_close = False
        self._mode_buttons: dict[str, QToolButton] = {}
        self._icon_buttons: list[tuple[QToolButton, str]] = []
        self._separators: list[QFrame] = []

        self._build_ui()
        self.apply_theme(self._theme_mode)
        self.set_selected_mode(self._selected_mode)
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

    @property
    def selected_mode(self) -> str:
        return self._selected_mode

    def _create_action_button(self, svg_key: str, label: str, min_width: int = 60) -> QToolButton:
        btn = QToolButton(self)
        btn.setText(label)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        btn.setIconSize(QSize(24, 24))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumSize(min_width, 66)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        font = QFont("Malgun Gothic", 9)
        btn.setFont(font)
        self._icon_buttons.append((btn, svg_key))
        return btn

    def _create_separator(self) -> QFrame:
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setFixedWidth(1)
        line.setFixedHeight(44)
        self._separators.append(line)
        return line

    def _build_ui(self):
        container = QWidget(self)
        self.setCentralWidget(container)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        self.btn_new = self._create_action_button("new", "새캡처", min_width=60)
        self.btn_new.setToolTip("선택된 방식으로 바로 캡처")
        self.btn_new.clicked.connect(lambda: self.capture_requested.emit(self._selected_mode))
        layout.addWidget(self.btn_new)

        layout.addWidget(self._create_separator())

        for mode_key, label in CAPTURE_MODES:
            btn = self._create_action_button(mode_key, label, min_width=62)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked=False, m=mode_key: self._on_mode_clicked(m))
            self._mode_buttons[mode_key] = btn
            layout.addWidget(btn)

        layout.addWidget(self._create_separator())

        self.btn_list = self._create_action_button("list", "캡처목록", min_width=64)
        self.btn_list.setToolTip("Capcraft 편집창 및 최근 캡처 목록 열기")
        self.btn_list.clicked.connect(self.editor_requested.emit)
        layout.addWidget(self.btn_list)

        self.btn_menu = self._create_action_button("menu", "메뉴", min_width=56)
        self.btn_menu.setToolTip("설정 및 기타 메뉴")
        self.btn_menu.clicked.connect(self._show_popup_menu)
        layout.addWidget(self.btn_menu)

        self.popup_menu = QMenu(self)
        self.action_settings = self.popup_menu.addAction("환경설정")
        self.action_settings.triggered.connect(self.settings_requested.emit)
        self.action_guide = self.popup_menu.addAction("사용 안내")
        self.action_guide.triggered.connect(self.guide_requested.emit)
        self.action_update = self.popup_menu.addAction("지금 업데이트")
        self.action_update.triggered.connect(self.update_check_requested.emit)
        self.popup_menu.addSeparator()
        self.action_quit = self.popup_menu.addAction("종료")
        self.action_quit.triggered.connect(self.quit_requested.emit)

    def _on_mode_clicked(self, mode_key: str):
        self.set_selected_mode(mode_key)
        self.capture_requested.emit(mode_key)

    def set_selected_mode(self, mode_key: str):
        if mode_key not in self._mode_buttons:
            mode_key = "manual"
        self._selected_mode = mode_key
        for key, btn in self._mode_buttons.items():
            btn.setChecked(key == mode_key)

    def _show_popup_menu(self):
        pos = self.btn_menu.mapToGlobal(QPoint(0, self.btn_menu.height() + 4))
        self.popup_menu.exec(pos)

    def apply_theme(self, theme_mode: str = "system"):
        self._theme_mode = theme_mode or "system"
        if self._theme_mode == "dark":
            is_dark = True
        elif self._theme_mode == "light":
            is_dark = False
        else:
            is_dark = _is_system_dark_mode()
        self._is_dark = is_dark

        if is_dark:
            bg = "#1e293b"
            fg = "#e2e8f0"
            hover = "#334155"
            checked_bg = "#1e3a5f"
            checked_fg = "#93c5fd"
            sep_color = "#334155"
            icon_color = "#e2e8f0"
            menu_bg = "#1e293b"
            menu_border = "#334155"
        else:
            bg = "#ffffff"
            fg = "#334155"
            hover = "#f1f5f9"
            checked_bg = "#e0f2fe"
            checked_fg = "#1d4ed8"
            sep_color = "#e2e8f0"
            icon_color = "#1e293b"
            menu_bg = "#ffffff"
            menu_border = "#cbd5e1"

        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {bg};
                color: {fg};
            }}
            QToolButton {{
                background-color: transparent;
                color: {fg};
                border: none;
                border-radius: 6px;
                padding: 6px 4px 4px 4px;
            }}
            QToolButton:hover {{
                background-color: {hover};
            }}
            QToolButton:checked {{
                background-color: {checked_bg};
                color: {checked_fg};
                font-weight: bold;
            }}
            QMenu {{
                background-color: {menu_bg};
                color: {fg};
                border: 1px solid {menu_border};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 18px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {hover};
            }}
            """
        )
        for sep in self._separators:
            sep.setStyleSheet(f"background-color: {sep_color}; border: none;")
        for btn, svg_key in self._icon_buttons:
            btn.setIcon(_render_svg_icon(svg_key, icon_color, size=24))

    def _target_screen(self):
        # Prefer Win32 physical cursor coordinates so multi-monitor + disabled HiDPI picks the active screen.
        if sys.platform == "win32":
            try:
                import win32api
                px, py = win32api.GetCursorPos()
                for s in QApplication.screens():
                    if s.geometry().contains(px, py):
                        return s
            except Exception:
                pass
        return QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()

    def show_positioned(self):
        if not self._positioned:
            screen = self._target_screen()
            if screen is not None:
                avail = screen.availableGeometry()
                x = avail.x() + (avail.width() - self.width()) // 2
                y = avail.top() + 36
                self.move(max(avail.left(), x), max(avail.top(), y))
            self._positioned = True
        self.show()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_capture_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if not self._allow_close:
            self.quit_requested.emit()
        event.accept()
