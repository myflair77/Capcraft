import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from capture_engine import bgra_array_to_qimage
from main import AppController, Backend, EditorMainWindow, compute_optimal_editor_zoom
from mini_launcher import MiniLauncherWindow
from single_instance import SingleInstanceBridge


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class FakePage:
    def __init__(self):
        self.scripts = []

    def runJavaScript(self, script, *args):
        self.scripts.append(script)
        cb = args[-1] if args and callable(args[-1]) else None
        if cb is not None:
            cb(None)


class FakeView:
    def __init__(self, window):
        self._window = window
        self._page = FakePage()

    def window(self):
        return self._window

    def page(self):
        return self._page


class FakeCaptureEngine:
    def __init__(self, image_arr=None, encode_ext=".webp"):
        self.image_arr = image_arr
        self.encode_ext = encode_ext
        self.last_captured_qimage = None
        self.calls = []

    def run_capture(self, mode, quality_mode="normal"):
        self.calls.append((mode, quality_mode))
        self.last_captured_qimage = None
        if self.image_arr is None:
            return None
        self.last_captured_qimage = bgra_array_to_qimage(self.image_arr)
        ok, buf = cv2.imencode(self.encode_ext, self.image_arr)
        assert ok
        return base64.b64encode(buf).decode("ascii")


class TestLauncherAndAutoCopy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _ensure_app()

    def test_bgra_array_to_qimage_preserves_size_and_alpha(self):
        arr = np.zeros((16, 24, 4), dtype=np.uint8)
        arr[:, :] = (255, 128, 32, 200)  # B, G, R, A
        qimg = bgra_array_to_qimage(arr)
        self.assertIsNotNone(qimg)
        self.assertFalse(qimg.isNull())
        self.assertEqual((qimg.width(), qimg.height()), (24, 16))
        pixel = QColor.fromRgba(qimg.pixel(5, 5))
        self.assertEqual((pixel.red(), pixel.green(), pixel.blue(), pixel.alpha()), (32, 128, 255, 200))

    def test_single_instance_ipc_notifies_primary(self):
        with tempfile.TemporaryDirectory() as tmp:
            primary = SingleInstanceBridge(tmp)
            self.assertTrue(primary.start_listening())
            received = []
            primary.activated.connect(received.append)

            secondary = SingleInstanceBridge(tmp)
            self.assertTrue(secondary.try_notify_existing("ACTIVATE_LAUNCHER"))
            for _ in range(20):
                self.app.processEvents()
                if received:
                    break

            primary.close()
            self.assertEqual(received, ["ACTIVATE_LAUNCHER"])

    def test_mini_launcher_buttons_and_mode_selection(self):
        launcher = MiniLauncherWindow(theme_mode="light")
        captured_modes = []
        editor_clicks = []
        launcher.capture_requested.connect(captured_modes.append)
        launcher.editor_requested.connect(lambda: editor_clicks.append(True))

        self.assertEqual(launcher.selected_mode, "manual")
        launcher._mode_buttons["scroll"].click()
        self.assertEqual(launcher.selected_mode, "scroll")
        launcher.btn_new.click()
        launcher.btn_list.click()
        launcher.apply_theme("dark")
        launcher._allow_close = True
        launcher.close()

        self.assertEqual(captured_modes, ["scroll", "scroll"])
        self.assertEqual(len(editor_clicks), 1)

    def test_capture_success_auto_copies_and_queues_until_frontend_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = os.path.join(tmp, ".capcraft_settings.json")
            Path(settings_path).write_text(
                json.dumps({"set_cap_quality": "normal", "set_auto_copy": True}),
                encoding="utf-8",
            )
            arr = np.zeros((20, 30, 4), dtype=np.uint8)
            arr[:, :] = (10, 200, 50, 255)  # B, G, R, A

            launcher = MiniLauncherWindow(theme_mode="light")
            editor = EditorMainWindow()
            view = FakeView(editor)
            controller = AppController(editor, view, launcher, settings_path=settings_path)
            editor._on_close_to_launcher = controller.show_launcher
            engine = FakeCaptureEngine(image_arr=arr, encode_ext=".webp")
            backend = Backend(engine, view, controller=controller)
            controller.attach_backend(backend)

            launcher.show()
            backend.start_capture("manual", "normal")

            # Raw QImage was copied to clipboard even though normal mode encodes WebP.
            clip_img = QApplication.clipboard().image()
            self.assertFalse(clip_img.isNull())
            self.assertEqual((clip_img.width(), clip_img.height()), (30, 20))
            self.assertTrue(editor.isVisible())
            self.assertFalse(launcher.isVisible())
            # Frontend not ready yet -> image queued, not yet injected.
            self.assertEqual(view.page().scripts, [])

            backend.frontend_ready()
            self.assertTrue(any("window.receiveCapturedImage(" in s for s in view.page().scripts))
            self.assertTrue(any("클립보드에 복사되었습니다" in s for s in view.page().scripts))

            # Closing editor window collapses back to mini launcher.
            editor.close()
            self.assertFalse(editor.isVisible())
            self.assertTrue(launcher.isVisible())

            editor._force_close = True
            editor.close()
            launcher._allow_close = True
            launcher.close()

    def test_capture_cancel_from_editor_returns_to_mini_launcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = os.path.join(tmp, ".capcraft_settings.json")
            launcher = MiniLauncherWindow(theme_mode="light")
            editor = EditorMainWindow()
            view = FakeView(editor)
            controller = AppController(editor, view, launcher, settings_path=settings_path)
            engine = FakeCaptureEngine(image_arr=None)
            backend = Backend(engine, view, controller=controller)
            controller.attach_backend(backend)

            editor.show()
            launcher.hide()
            backend.start_capture("manual", "normal")

            self.assertFalse(editor.isVisible())
            self.assertTrue(launcher.isVisible())

            editor._force_close = True
            editor.close()
            launcher._allow_close = True
            launcher.close()

    def test_compute_optimal_editor_zoom_across_monitor_sizes(self):
        # Wide QHD monitor at 100% DPI: zooms up so toolbar + sidebar fill cleanly.
        z_wide = compute_optimal_editor_zoom(1792, 1060, 1020, 170, current_zoom=1.0)
        self.assertGreater(z_wide, 1.3)
        self.assertLessEqual(z_wide, 1.75)

        # Already matched monitor (~1220 CSS px): stays near 1.0.
        z_ideal = compute_optimal_editor_zoom(1218, 860, 1020, 170, current_zoom=1.0)
        self.assertAlmostEqual(z_ideal, 1.0, places=2)

        # Compact laptop screen: zooms down slightly so toolbar never clips.
        z_small = compute_optimal_editor_zoom(960, 640, 1020, 170, current_zoom=1.0)
        self.assertLess(z_small, 0.85)
        self.assertGreaterEqual(z_small, 0.65)

    def test_auto_copy_disabled_does_not_overwrite_clipboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = os.path.join(tmp, ".capcraft_settings.json")
            Path(settings_path).write_text(
                json.dumps({"set_auto_copy": False}),
                encoding="utf-8",
            )
            QApplication.clipboard().setText("KEEP_EXISTING_TEXT")

            arr = np.zeros((12, 12, 4), dtype=np.uint8)
            arr[:, :] = (0, 0, 255, 255)
            launcher = MiniLauncherWindow(theme_mode="light")
            editor = EditorMainWindow()
            view = FakeView(editor)
            controller = AppController(editor, view, launcher, settings_path=settings_path)
            controller.frontend_ready = True
            engine = FakeCaptureEngine(image_arr=arr, encode_ext=".webp")
            backend = Backend(engine, view, controller=controller)
            controller.attach_backend(backend)

            backend.start_capture("manual", "normal")
            self.assertEqual(QApplication.clipboard().text(), "KEEP_EXISTING_TEXT")
            self.assertFalse(any("클립보드에 복사되었습니다" in s for s in view.page().scripts))

            editor._force_close = True
            editor.close()
            launcher._allow_close = True
            launcher.close()


if __name__ == "__main__":
    unittest.main()
