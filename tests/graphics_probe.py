"""Read graphics diagnostics in an isolated smoke-test window (no user history)."""
import os
import runpy
import sys
from pathlib import Path

os.environ['QT_LOGGING_RULES'] = 'qt.webenginecontext=true;qt.webengine.compositor=true;qt.scenegraph.general=true'
os.environ['CAPCRAFT_GRAPHICS_PROBE'] = '1'
if '--legacy-dpi' in sys.argv:
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '0'
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '0'
from PyQt6.QtCore import qInstallMessageHandler, qVersion
from PyQt6.QtWebEngineCore import qWebEngineVersion, qWebEngineChromiumVersion

def log(kind, context, message):
    print(f'QT [{context.category}] {message}', flush=True)

qInstallMessageHandler(log)
print('RUNTIME', sys.executable, qVersion(), qWebEngineVersion(), qWebEngineChromiumVersion(), flush=True)
for name in ['QTWEBENGINE_CHROMIUM_FLAGS', 'QT_QUICK_BACKEND', 'QSG_RHI_BACKEND', 'QT_SCALE_FACTOR', 'QT_OPENGL']:
    print(name, repr(os.environ.get(name)), flush=True)
sys.argv = [str(Path(__file__).with_name('qt_smoke.py')), '--benchmark']
runpy.run_path(sys.argv[0], run_name='__main__')
