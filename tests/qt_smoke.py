"""Run the same editor scenarios in the real Qt WebEngine with a QWebChannel bridge."""
import os
import sys
import json
from pathlib import Path
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
data = tempfile.TemporaryDirectory(prefix='capcraft-test-')
if '--observe-history' in sys.argv:
    source_dir = Path(os.environ.get('CAPCRAFT_DATA_DIR', str(Path.home())))
    history_source = source_dir / '.capcraft_history.json'
    if history_source.exists():
        shutil.copy2(history_source, Path(data.name) / '.capcraft_history.json')
os.environ['CAPCRAFT_DATA_DIR'] = data.name
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from main import Backend

app = QApplication(sys.argv)
errors = []
class Page(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source):
        if message.startswith('SELECTION_'): print(message, flush=True)
        if message.startswith('SELECTION_') and '--observe-history' in sys.argv:
            (ROOT / 'test-results').mkdir(exist_ok=True)
            with (ROOT / 'test-results/selection-live.log').open('a', encoding='utf8') as trace:
                trace.write(message + '\n')
        if level == self.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            errors.append(message)
            print('JS ERROR:', message, flush=True)

view = QWebEngineView()
profile = QWebEngineProfile(view)  # off the record, never use personal browser state
page = Page(profile, view)
view.setPage(page)
view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
channel = QWebChannel(page)
backend = Backend(None, view)
channel.registerObject('pyBackend', backend)
page.setWebChannel(channel)
host = QMainWindow()
host.setCentralWidget(view)
host.resize(1400, 1000)
host.setWindowTitle('Capcraft v1.2 - automated verification')
if '--software-compositing' in sys.argv:
    host.setWindowTitle('Capcraft v1.2 - compositor verification')
if '--presentation-pulse' in sys.argv:
    host.setWindowTitle('Capcraft v1.2 - bounded presentation verification')
finished = False

def finish(result):
    global finished
    if not result:
        return
    if finished:
        return
    finished = True
    timer.stop()
    results = json.loads(result)
    results.append(dict(name='Qt JavaScript errors', ok=not errors, errors=errors))
    (ROOT / 'test-results').mkdir(exist_ok=True)
    (ROOT / 'test-results/qt-editor.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf8')
    view.grab().save(str(ROOT / 'test-results/qt-editor.png'))
    for row in results:
        print(('PASS ' if row['ok'] else 'FAIL ') + row['name'] + ': ' + row.get('error', ''), flush=True)
    exit_code = 1 if any(not r['ok'] for r in results) else 0
    QTimer.singleShot(0, lambda: app.exit(exit_code))

def poll():
    page.runJavaScript('window.qtTestResults || null', finish)

def loaded(ok):
    if not ok:
        app.exit(2)
        return
    if '--presentation-pulse' in sys.argv:
        page.runJavaScript((ROOT / 'presentation-refresh.js').read_text(encoding='utf8') + '\ninstallPresentationRefresh();')
    if '--benchmark' in sys.argv:
        source = (ROOT / 'tests/rendering-scene.js').read_text(encoding='utf8')
        source += (ROOT / 'tests/qt-performance.js').read_text(encoding='utf8')
        page.runJavaScript(source + '\nrunQtPerformance().then(r => {console.log(JSON.stringify(r)); window.qtTestResults = JSON.stringify(r);});')
        timer.start(500)
        return
    if '--ocr' in sys.argv:
        source = (ROOT / 'tests/qt-ocr.js').read_text(encoding='utf8')
        page.runJavaScript(source)
        timer.start(500)
        return
    if '--observe-history' in sys.argv:
        source = (ROOT / 'tests/selection-trace.js').read_text(encoding='utf8')
        page.runJavaScript(source + '\ninstallSelectionTrace();')
        return
    if '--interactive' in sys.argv:
        scenario = 'selection' if '--selection' in sys.argv else ('recent' if '--recent' in sys.argv else 'rendering')
        source = (ROOT / f'tests/{scenario}-scene.js').read_text(encoding='utf8')
        page.runJavaScript(source + '\nprepare' + scenario.capitalize() + 'Scene();')
        return
    source = (ROOT / 'tests/editor-scenarios.js').read_text(encoding='utf8')
    page.runJavaScript(source + '\nrunEditorTests().then(r => window.qtTestResults = JSON.stringify(r)).catch(e => window.qtTestResults = JSON.stringify([{name:"suite",ok:false,error:String(e)}]));')
    timer.start(500)

timer = QTimer()
timer.timeout.connect(poll)
page.loadFinished.connect(loaded)
page.load(QUrl.fromLocalFile(str(ROOT / 'index.html')))
if '--interactive' in sys.argv or '--observe-history' in sys.argv:
    host.showMaximized()
else:
    host.show()
QTimer.singleShot(600000 if '--interactive' in sys.argv or '--observe-history' in sys.argv else 120000, lambda: app.exit(3))
code = app.exec()
view.close()
data.cleanup()
sys.exit(code)
