import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect, QPoint, Qt
import numpy as np
import cv2
import main
from capture_engine import CaptureOverlay, CaptureEngine, visible_window_bounds
from storage import atomic_write, write_json, HistoryWriter

APP = QApplication.instance() or QApplication([])


class RenderingConfigurationTests(unittest.TestCase):
    def test_no_ineffective_rendering_override(self):
        with patch.dict(os.environ, {}, clear=True), patch('main.sys.platform', 'win32'):
            main.configure_rendering()
            self.assertNotIn('QTWEBENGINE_CHROMIUM_FLAGS', os.environ)

    def test_explicit_flags_are_preserved(self):
        for flags in ('', '--enable-logging'):
            with patch.dict(os.environ, {'QTWEBENGINE_CHROMIUM_FLAGS': flags}), patch('main.sys.platform', 'win32'):
                main.configure_rendering()
                self.assertEqual(os.environ['QTWEBENGINE_CHROMIUM_FLAGS'], flags)


class WindowBoundsTests(unittest.TestCase):
    def test_visible_bounds_exclude_resize_margin_and_keep_physical_coordinates(self):
        def dwm(hwnd, attribute, pointer, size):
            self.assertEqual((hwnd, attribute), (456, 9))
            rect = pointer._obj
            rect.left, rect.top, rect.right, rect.bottom = -1800, 40, -400, 1040
            return 0
        with patch('capture_engine.win32gui.GetAncestor', return_value=456), \
             patch('capture_engine.ctypes.windll.dwmapi.DwmGetWindowAttribute', side_effect=dwm), \
             patch('capture_engine.win32gui.GetWindowRect') as fallback:
            self.assertEqual(visible_window_bounds(123), (-1800, 40, -400, 1040))
            fallback.assert_not_called()

    def test_failed_or_empty_dwm_bounds_fall_back(self):
        for result in (-1, 0):
            with patch('capture_engine.win32gui.GetAncestor', return_value=456), \
                 patch('capture_engine.ctypes.windll.dwmapi.DwmGetWindowAttribute', return_value=result), \
                 patch('capture_engine.win32gui.GetWindowRect', return_value=(1, 2, 101, 202)):
                self.assertEqual(visible_window_bounds(123), (1, 2, 101, 202))


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "한글 폴더" / "기록's.json"
        write_json(self.path, '[{"old": true}]', list)

    def test_interrupted_and_invalid_history_preserves_existing(self):
        writer = HistoryWriter(self.path)
        writer.append('[{"new":', True, False)
        self.assertEqual(json.loads(self.path.read_text()), [{"old": True}])
        with self.assertRaises(ValueError):
            writer.append('invalid]', False, True)
        self.assertEqual(json.loads(self.path.read_text()), [{"old": True}])

    def test_complete_unicode_chunk_transfer(self):
        writer = HistoryWriter(self.path)
        writer.append('["한글', True, False)
        writer.append(' 😀"]', False, True)
        self.assertEqual(json.loads(self.path.read_text(encoding='utf8')), ['한글 😀'])
        self.assertFalse(list(self.path.parent.glob('*.tmp')))

    def test_failed_replace_preserves_file(self):
        with patch('storage.os.replace', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                atomic_write(self.path, b'new')
        self.assertEqual(json.loads(self.path.read_text()), [{"old": True}])
        self.assertFalse(list(self.path.parent.glob('*.tmp')))

    def test_backend_unicode_save_dialog_and_atomic_file_write(self):
        view = MagicMock()
        backend = main.Backend(MagicMock(), view)
        target = str(self.path.with_suffix('.png'))
        with patch('main.QFileDialog.getSaveFileName', return_value=(target, 'PNG Files (*.png)')):
            backend._do_request_save('png', 'capture')
        script = view.page().runJavaScript.call_args.args[0]
        self.assertIn(json.dumps(target), script)
        self.assertNotIn('atob', script)
        self.assertTrue(backend.write_file_data(target, base64.b64encode(b'fixture').decode()))
        self.assertEqual(Path(target).read_bytes(), b'fixture')

    def test_history_survives_restart(self):
        with patch('main.HISTORY_FILE', str(self.path)):
            backend = main.Backend(MagicMock(), MagicMock())
            self.assertEqual(json.loads(backend.load_history()), [{"old": True}])


class CaptureTests(unittest.TestCase):
    def test_capture_modes_encode_expected_pixels(self):
        screen = MagicMock()
        screen.geometry.return_value = QRect(0, 0, 800, 600)
        screen.devicePixelRatio.return_value = 1
        screen.name.return_value = 'fixture'
        frame = np.full((600, 800, 4), (30, 60, 90, 255), dtype=np.uint8)
        with patch('capture_engine.QApplication') as app, \
                patch('capture_engine.mss.mss') as grabber, \
                patch('capture_engine.win32api.EnumDisplayMonitors', return_value=[]):
            app.instance.return_value.screens.return_value = [screen]
            grabber.return_value.__enter__.return_value.grab.return_value = frame
            for mode in ['manual', 'full', 'size_80_60', 'window', 'unit']:
                with self.subTest(mode=mode):
                    overlay = CaptureOverlay(mode, 'high')
                    overlay.current_pos = QPoint(200, 200)
                    event = MagicMock()
                    event.button.return_value = Qt.MouseButton.LeftButton
                    event.pos.return_value = QPoint(200, 200)
                    if mode in ('full', 'size_80_60'):
                        overlay.mousePressEvent(event)
                    elif mode == 'manual':
                        overlay.start_pos = QPoint(100, 100)
                        overlay.is_dragging = True
                        overlay.mouseReleaseEvent(event)
                    else:
                        overlay.target_rect_physical = (100, 100, 80, 60)
                        with patch('capture_engine.win32api.GetCursorPos', return_value=(200, 200)), \
                                patch('capture_engine.win32api.GetAsyncKeyState', side_effect=lambda key: -1 if key == 1 else 0):
                            overlay.poll_mouse()
                    image = cv2.imdecode(np.frombuffer(base64.b64decode(overlay.result_img), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                    expected = (600, 800) if mode == 'full' else (100, 100) if mode == 'manual' else (60, 80)
                    self.assertEqual(image.shape[:2], expected)
                    self.assertEqual(tuple(image[10, 10]), (30, 60, 90, 255))
                    if hasattr(overlay, 'timer'): overlay.timer.stop()
                    overlay.deleteLater()

    def test_scroll_stitching_with_initial_unchanged_frame(self):
        # A slow first scroll must not leave full_image uninitialized.
        rng = np.random.default_rng(4)
        content = rng.integers(0, 256, (700, 500, 4), dtype=np.uint8)
        content[:, :, 3] = 255
        state = {'step': 0}
        def scroll(*args): state['step'] += 1
        def frame(*args):
            offset = min(max(0, state['step'] - 1) * 80, 320)
            return content[offset:offset+300].copy()
        with patch('capture_engine.win32gui.WindowFromPoint', return_value=1), \
                patch('capture_engine.win32gui.GetWindowRect', return_value=(0, 0, 500, 300)), \
                patch('capture_engine.win32api.SetCursorPos'), \
                patch('capture_engine.win32api.GetCursorPos', return_value=(10, 10)), \
                patch('capture_engine.win32api.GetAsyncKeyState', return_value=0), \
                patch('capture_engine.win32api.mouse_event', side_effect=scroll), \
                patch('capture_engine.ScrollCaptureOverlay'), \
                patch('capture_engine.ScrollButtonOverlay') as button, \
                patch('capture_engine.time.sleep'), \
                patch('capture_engine.mss.mss') as grabber:
            button.return_value.geometry.return_value = QRect(100, 400, 280, 100)
            grabber.return_value.__enter__.return_value.grab.side_effect = frame
            encoded = CaptureEngine().run_scroll_capture(QPoint(10, 10), 'high')
            image = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
            self.assertEqual(image.shape, (620, 500, 4))
            np.testing.assert_array_equal(image, content[:620])

    def overlay(self):
        obj = CaptureOverlay.__new__(CaptureOverlay)
        # Test composition/coordinates from synthetic monitors, without reading the desktop.
        obj.v_left = -100
        obj.v_top = 0
        obj.screen_data = [
            {'logical_rect': QRect(-100, 0, 100, 100), 'dpr': 1,
             'physical_rect': dict(left=-100, top=0, width=100, height=100),
             'img_arr': np.full((100, 100, 4), (10, 20, 30, 255), dtype=np.uint8)},
            {'logical_rect': QRect(0, 0, 100, 100), 'dpr': 2,
             'physical_rect': dict(left=0, top=0, width=200, height=200),
             'img_arr': np.full((200, 200, 4), (40, 50, 60, 255), dtype=np.uint8)}]
        return obj

    def test_mixed_dpi_negative_monitor_coordinates(self):
        obj = self.overlay()
        self.assertEqual(obj.logical_to_physical(50, 40), (-50, 40))
        self.assertEqual(obj.logical_to_physical(150, 40), (100, 80))
        self.assertEqual(obj.physical_to_logical(100, 80), (150, 40))

    def test_cross_monitor_crop_and_transparent_gap(self):
        image = self.overlay().get_physical_crop(-50, 0, 300, 100)
        self.assertEqual(tuple(image[0, 0]), (10, 20, 30, 255))
        self.assertEqual(tuple(image[0, 70]), (40, 50, 60, 255))
        self.assertEqual(tuple(image[0, 290]), (0, 0, 0, 0))

    def test_fractional_175_percent_capture_coordinates(self):
        obj = self.overlay()
        obj.screen_data[1]['dpr'] = 1.75
        obj.screen_data[1]['physical_rect'].update(width=175, height=175)
        self.assertEqual(obj.logical_to_physical(140, 40), (70, 70))
        self.assertEqual(obj.physical_to_logical(70, 70), (140, 40))

    def test_failed_monitor_does_not_crash_coordinate_conversion(self):
        obj = self.overlay()
        obj.screen_data[0]['physical_rect'] = None
        self.assertEqual(obj.logical_to_physical(20, 30), (-80, 30))

    def test_70_capture_overlays_are_disposed(self):
        with patch('capture_engine.CaptureOverlay') as constructor:
            overlay = constructor.return_value
            overlay.isVisible.return_value = False
            overlay.result_img = 'fixture'
            engine = CaptureEngine()
            for _ in range(70):
                self.assertEqual(engine.run_capture('manual'), 'fixture')
            self.assertEqual(overlay.deleteLater.call_count, 70)
            self.assertEqual(overlay.timer.stop.call_count, 70)


if __name__ == '__main__':
    unittest.main()
